"""
Keycloak Identity Provider (IdP) client for enterprise authentication.
"""

import os
import json
import time
import base64
import hashlib
import logging
import secrets
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode, parse_qs, urlparse
import requests
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


class KeycloakClient:
    """Keycloak Identity Provider (IdP) client for enterprise authentication."""
    
    def __init__(self, config: Dict[str, Any]):
        self.domain = config.get('domain')
        self.idp_protocol = config.get('idp_protocol', 'http')
        self.client_id = config.get('client_id')
        self.realm = config.get('realm')
        self.client_secret = config.get('client_secret')
        self.redirect_uri = config.get('redirect_uri', 'http://localhost:8080/callback')
        self.scopes = config.get('scopes', ['openid', 'profile', 'email', 'groups'])
        
        # Cache for JWKS keys
        self._jwks_cache = {}
        self._jwks_cache_expiry = 0
        
        # Google oauth config
        self.google_client_id = config.get('google_client_id')
        self.google_client_secret = config.get('google_client_secret')
        self.google_oauth_token_uri = config.get('google_oauth_token_uri', 'https://oauth2.googleapis.com/token')

        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate IdP configuration."""
        
        if not all([self.domain, self.client_id, self.client_secret]):
            raise ValueError("Domain, client_id, and client_secret are required")
    
    """used"""
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
        
        return response.json()

    def _get_auth_endpoint(self) -> str:
        """Get authorization endpoint for IdP."""
        return f"{self.idp_protocol}://{self.domain}/realms/{self.realm}/protocol/openid-connect/auth"
    
    def _get_token_endpoint(self) -> str:
        """Get token endpoint for IdP."""
        return f"{self.idp_protocol}://{self.domain}/realms/{self.realm}/protocol/openid-connect/token"


class KeycloakAuthenticator:
    """High-level authenticator that handles the complete OAuth2 flow."""
    
    def __init__(self, config: Dict[str, Any]):
        self.client = KeycloakClient(config)
        self.current_tokens = None
        self.user_info = None
        self.logger = logging.getLogger(__name__)
    
    def start_authentication(self) -> str:
        """Start the authentication process and return authorization URL."""
        return self.client.get_authorization_url()
    
    def complete_authentication(self, authorization_code: str) -> Dict[str, Any]:
        """Complete authentication with authorization code."""
        # Exchange code for tokens
        self.current_tokens = self.client.exchange_code_for_tokens(authorization_code)
        self.user_info = jwt.decode(self.current_tokens['id_token'], options={"verify_signature": False})
        
        return {
            'user_info': self.user_info,
            'tokens': self.current_tokens
        }
        
        
