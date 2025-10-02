"""
Role-Based Access Control (RBAC) manager for internal systems.
Handles role mapping, scope resolution, and JWT token minting.
"""

import os
import json
import time
import yaml
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import logging

logger = logging.getLogger(__name__)


class RBACManager:
    """Manages role-based access control and JWT token operations."""
    
    def __init__(self, config: Dict[str, Any]):
        self.jwt_secret = config.get('jwt_secret_key')
        self.jwt_algorithm = config.get('jwt_algorithm', 'RS256')
        self.token_expiry_minutes = config.get('token_expiry_minutes', 60)
        self.issuer = config.get('issuer', 'rbac-proxy')
        self.audience = config.get('audience', 'google-mcp-server')
        
        # Load role mappings
        self.role_mappings = self._load_role_mappings()
        
        # Generate RSA key pair for RS256 if needed
        if self.jwt_algorithm.startswith('RS'):
            self._generate_rsa_keys()
        
        if not self.jwt_secret:
            raise ValueError("JWT secret key is required")
    
    def _load_role_mappings(self) -> Dict[str, Any]:
        """Load role mappings from YAML file or use defaults."""
        return {
            'roles': {
                'basic': {
                    'scopes': ['api:google:read'],
                    'description': 'Basic access'
                },
                'editor': {
                    'scopes': ['api:google:*'],
                    'description': 'Editor access'
                },
            },
            'group_mappings': {
                # Map IdP groups to internal roles
                'Basic': 'basic',
                'Editor': 'editor',
            }
        }
    
    def _generate_rsa_keys(self):
        """Generate RSA key pair for RS256 JWT signing."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        
        self.private_key = private_key
        self.public_key = private_key.public_key()
        
        # Store keys for JWKS endpoint
        self.private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        self.public_key_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def map_groups_to_roles(self, groups: List[str]) -> List[str]:
        """Map IdP groups to internal roles."""
        roles = []
        group_mappings = self.role_mappings.get('group_mappings', {})
        
        for group in groups:
            if group in group_mappings:
                role = group_mappings[group]
                if role not in roles:
                    roles.append(role)
        
        # Default role if no mappings found
        if not roles:
            roles.append('readonly')
        
        logger.info(f"Mapped groups {groups} to roles {roles}")
        return roles
    
    def resolve_scopes(self, roles: List[str]) -> List[str]:
        """Resolve roles to scopes."""
        scopes = set()
        role_definitions = self.role_mappings.get('roles', {})
        
        for role in roles:
            if role in role_definitions:
                role_scopes = role_definitions[role].get('scopes', [])
                scopes.update(role_scopes)
        
        # Handle wildcard scopes
        resolved_scopes = []
        for scope in scopes:
            if scope == '*':
                # Grant all available scopes
                resolved_scopes.extend(self._get_all_scopes())
            else:
                resolved_scopes.append(scope)
        
        # Remove duplicates and sort
        resolved_scopes = sorted(list(set(resolved_scopes)))
        
        logger.info(f"Resolved roles {roles} to scopes {resolved_scopes}")
        return resolved_scopes
    
    def _get_all_scopes(self) -> List[str]:
        """Get all available scopes from role definitions."""
        all_scopes = set()
        role_definitions = self.role_mappings.get('roles', {})
        
        for role_data in role_definitions.values():
            scopes = role_data.get('scopes', [])
            for scope in scopes:
                if scope != '*':  # Avoid infinite recursion
                    all_scopes.add(scope)
        
        return list(all_scopes)
    
    def create_jwt_token(self, user_context: Dict[str, Any], roles: List[str], scopes: List[str]) -> str:
        """Create a JWT token with user context and permissions."""
        import time
        now_timestamp = int(time.time())
        exp_timestamp = now_timestamp + (self.token_expiry_minutes * 60)
        payload = {
            # Standard JWT claims
            'iss': self.issuer,
            'aud': self.audience,
            'sub': user_context.get('user_id', user_context.get('sub', '')),
            'iat': now_timestamp,
            'exp': exp_timestamp,
            'nbf': now_timestamp,
            'jti': f"{user_context.get('user_id', user_context.get('sub', ''))}_{now_timestamp}",
            
            # Custom claims
            'email': user_context.get('email'),
            'name': user_context.get('name'),
            'roles': roles,
            'scopes': scopes,
            'groups': user_context.get('groups', []),
            'session_id': user_context.get('session_id'),
            'auth_time': user_context.get('authenticated_at'),
            'token_type': 'access'
        }
        
        # Sign token
        if self.jwt_algorithm.startswith('RS'):
            token = jwt.encode(payload, self.private_key, algorithm=self.jwt_algorithm)
        else:
            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        logger.info(f"Created JWT token for user {user_context.get('email')} with roles {roles}")
        return token
    
    def get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set for token validation."""
        if not self.jwt_algorithm.startswith('RS'):
            raise Exception("JWKS only available for RSA algorithms")
        
        # Convert public key to JWK format
        public_numbers = self.public_key.public_numbers()
        
        # Convert to base64url encoding
        def int_to_base64url(val):
            import base64
            byte_length = (val.bit_length() + 7) // 8
            val_bytes = val.to_bytes(byte_length, 'big')
            return base64.urlsafe_b64encode(val_bytes).decode('ascii').rstrip('=')
        
        jwk = {
            'kty': 'RSA',
            'use': 'sig',
            'alg': self.jwt_algorithm,
            'kid': 'internal-rbac-key-1',
            'n': int_to_base64url(public_numbers.n),
            'e': int_to_base64url(public_numbers.e)
        }
        
        return {
            'keys': [jwk]
        }
    
    def audit_log(self, action: str, user_context: Dict[str, Any], details: Dict[str, Any] = None):
        """Log audit events for security monitoring."""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'user_id': user_context.get('user_id', user_context.get('sub', '')),
            'user_email': user_context.get('email'),
            'user_roles': user_context.get('roles', []),
            'details': details or {}
        }
        
        # In production, this would go to a secure audit log system
        logger.info(f"AUDIT: {json.dumps(audit_entry)}")

    def validate_jwt_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode JWT token."""
        try:
            if self.jwt_algorithm.startswith('RS'):
                payload = jwt.decode(
                    token,
                    self.public_key,
                    algorithms=[self.jwt_algorithm],
                    audience=self.audience,
                    issuer=self.issuer
                )
            else:
                payload = jwt.decode(
                    token,
                    self.jwt_secret,
                    algorithms=[self.jwt_algorithm],
                    audience=self.audience,
                    issuer=self.issuer
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise Exception("Token has expired")
        except jwt.InvalidTokenError as e:
            raise Exception(f"Invalid token: {str(e)}")

class RBACProxy:
    """RBAC Proxy service that handles authentication flow."""
    
    def __init__(self, config: Dict[str, Any]):
        self.rbac_manager = RBACManager(config)
        self.config = config
    
    def process_authentication(self, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Process user authentication and return JWT token."""
        try:
            # Map groups to roles
            user_info = user_context.get('user_info')
            user_groups = user_info.get('groups', [])
            user_groups = [group.replace('/', '') for group in user_groups]
            
            roles = self.rbac_manager.map_groups_to_roles(user_groups)
            
            # Resolve roles to scopes
            scopes = self.rbac_manager.resolve_scopes(roles)
            
            # Create JWT token
            jwt_token = self.rbac_manager.create_jwt_token(user_info, roles, scopes)
            
            # Audit log
            self.rbac_manager.audit_log(
                'authentication_success',
                user_context,
                {'roles': roles, 'scopes': scopes}
            )
            
            return {
                'success': True,
                'jwt_token': jwt_token,
                'expires_in': self.rbac_manager.token_expiry_minutes * 60,
                'roles': roles,
                'scopes': scopes,
                'user_info': {
                    'user_id': user_context.get('user_id', user_info.get('sub', '')),
                    'email': user_context.get('email'),
                    'name': user_context.get('name', user_info.get('given_name', ''))
                }
            }
            
        except Exception as e:
            # Audit log failure
            self.rbac_manager.audit_log(
                'authentication_failure',
                user_context,
                {'error': str(e)}
            )
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_jwt_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode JWT token."""
        return self.rbac_manager.validate_jwt_token(token)
    
    def get_jwks(self) -> Dict[str, Any]:
        """Get JWKS for token validation."""
        return self.rbac_manager.get_jwks()
