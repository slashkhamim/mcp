"""
Identity Provider (IdP) client for enterprise authentication.
Supports Okta, Azure AD, Google Workspace, and Keycloak.
"""

import os
import json
import time
import base64
import hashlib
import secrets
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, parse_qs, urlparse
import requests
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class IdPClient:
    """Universal Identity Provider client supporting multiple IdP types."""
    
    def __init__(self, config: Dict[str, Any]):
        self.idp_type = config.get('idp_type', '').lower()
        self.domain = config.get('domain')
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.redirect_uri = config.get('redirect_uri', 'http://localhost:8080/callback')
        self.scopes = config.get('scopes', ['openid', 'profile', 'email', 'groups'])
        
        # Cache for JWKS keys
        self._jwks_cache = {}
        self._jwks_cache_expiry = 0
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate IdP configuration."""
        if not self.idp_type:
            raise ValueError("IdP type is required")
        
        if self.idp_type not in ['okta', 'azure', 'google', 'keycloak']:
            raise ValueError(f"Unsupported IdP type: {self.idp_type}")
        
        if not all([self.domain, self.client_id, self.client_secret]):
            raise ValueError("Domain, client_id, and client_secret are required")
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate authorization URL for OAuth2 flow."""
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Generate PKCE parameters
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'scope': ' '.join(self.scopes),
            'redirect_uri': self.redirect_uri,
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256'
        }
        
        auth_url = f"{self._get_auth_endpoint()}?{urlencode(params)}"
        
        # Store code_verifier for token exchange
        self._code_verifier = code_verifier
        
        return auth_url
    
    def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and ID tokens."""
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': authorization_code,
            'redirect_uri': self.redirect_uri,
            'code_verifier': getattr(self, '_code_verifier', '')
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        response = requests.post(
            self._get_token_endpoint(),
            data=token_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Token exchange failed: {response.text}")
        
        tokens = response.json()
        
        # Validate and decode ID token
        if 'id_token' in tokens:
            user_info = self.validate_id_token(tokens['id_token'])
            tokens['user_info'] = user_info
        
        return tokens
    
    def validate_id_token(self, id_token: str) -> Dict[str, Any]:
        """Validate and decode ID token."""
        try:
            # Get JWKS for token validation
            jwks = self._get_jwks()
            
            # Decode header to get key ID
            header = jwt.get_unverified_header(id_token)
            kid = header.get('kid')
            
            if not kid:
                raise ValueError("No key ID found in token header")
            
            # Find matching key
            key = None
            for jwk in jwks.get('keys', []):
                if jwk.get('kid') == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
                    break
            
            if not key:
                raise ValueError(f"No matching key found for kid: {kid}")
            
            # Validate token
            payload = jwt.decode(
                id_token,
                key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=self._get_issuer()
            )
            
            return payload
            
        except Exception as e:
            raise Exception(f"ID token validation failed: {str(e)}")
    
    def get_user_groups(self, access_token: str) -> List[str]:
        """Get user groups from IdP."""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        
        groups_url = self._get_groups_endpoint()
        response = requests.get(groups_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch user groups: {response.text}")
        
        groups_data = response.json()
        return self._extract_groups(groups_data)
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        token_data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        response = requests.post(
            self._get_token_endpoint(),
            data=token_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"Token refresh failed: {response.text}")
        
        return response.json()
    
    def _get_auth_endpoint(self) -> str:
        """Get authorization endpoint for IdP."""
        endpoints = {
            'okta': f"https://{self.domain}/oauth2/default/v1/authorize",
            'azure': f"https://login.microsoftonline.com/{self.domain}/oauth2/v2.0/authorize",
            'google': "https://accounts.google.com/o/oauth2/v2/auth",
            'keycloak': f"https://{self.domain}/auth/realms/master/protocol/openid-connect/auth"
        }
        return endpoints[self.idp_type]
    
    def _get_token_endpoint(self) -> str:
        """Get token endpoint for IdP."""
        endpoints = {
            'okta': f"https://{self.domain}/oauth2/default/v1/token",
            'azure': f"https://login.microsoftonline.com/{self.domain}/oauth2/v2.0/token",
            'google': "https://oauth2.googleapis.com/token",
            'keycloak': f"https://{self.domain}/auth/realms/master/protocol/openid-connect/token"
        }
        return endpoints[self.idp_type]
    
    def _get_groups_endpoint(self) -> str:
        """Get groups endpoint for IdP."""
        endpoints = {
            'okta': f"https://{self.domain}/api/v1/users/me/groups",
            'azure': "https://graph.microsoft.com/v1.0/me/memberOf",
            'google': "https://www.googleapis.com/oauth2/v2/userinfo",
            'keycloak': f"https://{self.domain}/auth/realms/master/protocol/openid-connect/userinfo"
        }
        return endpoints[self.idp_type]
    
    def _get_issuer(self) -> str:
        """Get issuer for token validation."""
        issuers = {
            'okta': f"https://{self.domain}/oauth2/default",
            'azure': f"https://login.microsoftonline.com/{self.domain}/v2.0",
            'google': "https://accounts.google.com",
            'keycloak': f"https://{self.domain}/auth/realms/master"
        }
        return issuers[self.idp_type]
    
    def _get_jwks(self) -> Dict[str, Any]:
        """Get JWKS (JSON Web Key Set) for token validation."""
        # Check cache first
        if time.time() < self._jwks_cache_expiry and self._jwks_cache:
            return self._jwks_cache
        
        jwks_endpoints = {
            'okta': f"https://{self.domain}/oauth2/default/v1/keys",
            'azure': f"https://login.microsoftonline.com/{self.domain}/discovery/v2.0/keys",
            'google': "https://www.googleapis.com/oauth2/v3/certs",
            'keycloak': f"https://{self.domain}/auth/realms/master/protocol/openid-connect/certs"
        }
        
        jwks_url = jwks_endpoints[self.idp_type]
        response = requests.get(jwks_url, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch JWKS: {response.text}")
        
        jwks = response.json()
        
        # Cache for 1 hour
        self._jwks_cache = jwks
        self._jwks_cache_expiry = time.time() + 3600
        
        return jwks
    
    def _extract_groups(self, groups_data: Dict[str, Any]) -> List[str]:
        """Extract group names from IdP-specific response format."""
        groups = []
        
        if self.idp_type == 'okta':
            for group in groups_data:
                groups.append(group.get('profile', {}).get('name', ''))
        
        elif self.idp_type == 'azure':
            for item in groups_data.get('value', []):
                if item.get('@odata.type') == '#microsoft.graph.group':
                    groups.append(item.get('displayName', ''))
        
        elif self.idp_type == 'google':
            # Google doesn't provide groups in standard way
            # This would need Google Workspace Admin SDK
            groups = groups_data.get('groups', [])
        
        elif self.idp_type == 'keycloak':
            groups = groups_data.get('groups', [])
        
        return [g for g in groups if g]  # Filter out empty strings


class IdPAuthenticator:
    """High-level authenticator that handles the complete OAuth2 flow."""
    
    def __init__(self, config: Dict[str, Any]):
        self.client = IdPClient(config)
        self.current_tokens = None
        self.user_info = None
        self.user_groups = None
    
    def start_authentication(self) -> str:
        """Start the authentication process and return authorization URL."""
        return self.client.get_authorization_url()
    
    def complete_authentication(self, authorization_code: str) -> Dict[str, Any]:
        """Complete authentication with authorization code."""
        # Exchange code for tokens
        self.current_tokens = self.client.exchange_code_for_tokens(authorization_code)
        self.user_info = self.current_tokens.get('user_info', {})
        
        # Get user groups
        if 'access_token' in self.current_tokens:
            try:
                self.user_groups = self.client.get_user_groups(self.current_tokens['access_token'])
            except Exception as e:
                print(f"Warning: Failed to fetch user groups: {e}")
                self.user_groups = []
        
        return {
            'user_info': self.user_info,
            'groups': self.user_groups,
            'tokens': self.current_tokens
        }
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated."""
        if not self.current_tokens:
            return False
        
        # Check if access token is expired
        access_token = self.current_tokens.get('access_token')
        if not access_token:
            return False
        
        try:
            # Decode without verification to check expiry
            payload = jwt.decode(access_token, options={"verify_signature": False})
            exp = payload.get('exp', 0)
            return time.time() < exp
        except:
            return False
    
    def refresh_authentication(self) -> bool:
        """Refresh authentication tokens."""
        if not self.current_tokens or 'refresh_token' not in self.current_tokens:
            return False
        
        try:
            new_tokens = self.client.refresh_access_token(self.current_tokens['refresh_token'])
            self.current_tokens.update(new_tokens)
            return True
        except Exception as e:
            print(f"Token refresh failed: {e}")
            return False
    
    def get_access_token(self) -> Optional[str]:
        """Get current access token, refreshing if necessary."""
        if not self.is_authenticated():
            if not self.refresh_authentication():
                return None
        
        return self.current_tokens.get('access_token')
    
    def get_user_context(self) -> Dict[str, Any]:
        """Get complete user context for authorization decisions."""
        return {
            'user_id': self.user_info.get('sub'),
            'email': self.user_info.get('email'),
            'name': self.user_info.get('name'),
            'groups': self.user_groups or [],
            'authenticated_at': self.user_info.get('iat'),
            'expires_at': self.user_info.get('exp')
        }
