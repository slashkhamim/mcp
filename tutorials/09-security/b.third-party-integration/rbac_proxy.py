"""
RBAC Proxy Server - Handles IdP authentication and JWT token minting.
Acts as the intermediary between clients and MCP servers.
"""

import os
import json
import asyncio
from typing import Dict, Any, Optional
from urllib.parse import parse_qs, urlparse
import logging
import time
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
import uvicorn

from libs.keycloak_client import KeycloakAuthenticator
from libs.rbac_manager import RBACProxy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for configuration
idp_authenticator: Optional[KeycloakAuthenticator] = None
rbac_proxy: Optional[RBACProxy] = None
config: Dict[str, Any] = {}

# In-memory session store (use Redis in production)
active_sessions: Dict[str, Dict[str, Any]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown."""
    global idp_authenticator, rbac_proxy, config
    
    # Startup
    config = load_config()
    
    # Validate required configuration
    required_vars = ['domain', 'client_id', 'client_secret', 'jwt_secret_key']
    missing_vars = [var for var in required_vars if not config.get(var)]
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {missing_vars}")
    
    # Initialize services
    idp_authenticator = KeycloakAuthenticator(config)
    rbac_proxy = RBACProxy(config)
    
    logger.info(f"RBAC Proxy started with IdP type: {config['idp_type']}")
    
    yield
    
    # Shutdown (if needed)
    logger.info("RBAC Proxy shutting down")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Third-Party Integration RBAC Proxy",
    description="Authentication proxy for third-party integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()


def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    # Load .env file if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        logger.warning("python-dotenv not available, using system environment only")
    
    return {
        # IdP Configuration
        'idp_type': os.getenv('IDP_TYPE', 'okta').lower(),
        'domain': os.getenv('IDP_DOMAIN', 'your-domain.okta.com'),
        'idp_protocol': os.getenv('IDP_PROTOCOL', 'http'),
        'realm': os.getenv('IDP_REALM', 'your-realm'),
        'client_id': os.getenv('IDP_CLIENT_ID', 'your_client_id'),
        'client_secret': os.getenv('IDP_CLIENT_SECRET', 'your_client_secret'),
        'redirect_uri': os.getenv('IDP_REDIRECT_URI', 'http://localhost:8081/auth/callback'),
        'scopes': os.getenv('IDP_SCOPES', 'openid profile email groups').split(),
        
        # JWT Configuration
        'jwt_secret_key': os.getenv('JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-this-in-production'),
        'jwt_algorithm': os.getenv('JWT_ALGORITHM', 'HS256'),
        'token_expiry_minutes': int(os.getenv('TOKEN_EXPIRY_MINUTES', '60')),
        'issuer': os.getenv('JWT_ISSUER', 'internal-rbac-proxy'),
        'audience': os.getenv('JWT_AUDIENCE', 'internal-mcp-server'),
                
        # Server Configuration
        'host': os.getenv('PROXY_HOST', '0.0.0.0'),
        'port': int(os.getenv('PROXY_PORT', '8080')),
        'debug': os.getenv('DEBUG', 'false').lower() == 'true',

        # Client Configuration
        'client_redirect_uri': os.getenv('CLIENT_REDIRECT_URI', 'http://localhost:8081/auth/callback'),

        # Google Configuration
        'google_client_id': os.getenv('GOOGLE_CLIENT_ID', 'your_google_client_id'),
        'google_client_secret': os.getenv('GOOGLE_CLIENT_SECRET', 'your_google_client_secret'),
        'google_oauth_token_uri': os.getenv('GOOGLE_OAUTH_TOKEN_URI', 'https://oauth2.googleapis.com/token'),
    }


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Internal System RBAC Proxy",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "idp_type": config.get('idp_type')
    }


@app.get("/auth/login")
async def login():
    """Initiate OAuth2 login flow."""
    try:
        auth_url = idp_authenticator.start_authentication()
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Login initiation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle OAuth2 callback."""
    try:
        # Extract authorization code from query parameters
        query_params = dict(request.query_params)
        auth_code = query_params.get('code')
        state = query_params.get('state')
        error = query_params.get('error')
        logger.info(f"Auth callback: {query_params}")
        if error:
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
        
        if not auth_code:
            raise HTTPException(status_code=400, detail="Missing authorization code")
        
        # Complete authentication
        auth_result = idp_authenticator.complete_authentication(auth_code)
        keycloak_access_token = auth_result['tokens']['access_token']
        google_tokens = idp_authenticator.get_google_token(keycloak_access_token)
        refresh_token_expiration = google_tokens['refresh_token_expires_in']

        # Store session (in production, use secure session management)
        session_id = f"session_{auth_result['user_info']['sub']}_{int(datetime.utcnow().timestamp())}"
        auth_result['user_info']['session_id'] = session_id

        # Process through RBAC
        rbac_result = rbac_proxy.process_authentication(auth_result)
        
        if not rbac_result['success']:
            raise HTTPException(status_code=403, detail=rbac_result['error'])
        
        active_sessions[session_id] = {
            'user_info': rbac_result['user_info'],
            'jwt_token': rbac_result['jwt_token'],
            'roles': rbac_result['roles'],
            'scopes': rbac_result['scopes'],
            'google_access_token': google_tokens['access_token'],
            'google_access_token_expiration': google_tokens['accessTokenExpiration'],
            'google_refresh_token': google_tokens['refresh_token'],
            'google_refresh_token_expiration': int(time.time() + refresh_token_expiration),
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Get the base redirect URL from config
        redirect_base = config.get('client_redirect_uri')
        
        # Prepare data for redirect
        redirect_params = {
            "session_id": session_id,
            "token": rbac_result['jwt_token'],
            "expires_in": rbac_result['expires_in'],
            "auth_success": "true"
        }
        
        # Build redirect URL with parameters
        query_string = "&".join([f"{key}={value}" for key, value in redirect_params.items()])
        redirect_url = f"{redirect_base}?{query_string}"
        
        # Return redirect response
        return RedirectResponse(url=redirect_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication callback failed: {e}")
        # Redirect to app with error
        error_redirect = f"{config.get('redirect_uri', 'http://localhost:8501')}?auth_error={str(e)}"
        return RedirectResponse(url=error_redirect)

@app.get("/auth/jwks")
async def get_jwks():
    """Get JSON Web Key Set for token validation."""
    try:
        if config['jwt_algorithm'].startswith('RS'):
            return rbac_proxy.get_jwks()
        else:
            # For HMAC algorithms, JWKS is not applicable
            raise HTTPException(status_code=404, detail="JWKS not available for HMAC algorithms")
    except Exception as e:
        logger.error(f"JWKS retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/token/google")
async def get_google_access_token(request: Request):
    """Validate and decode Google token."""
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header format. Expected 'Bearer <token>'")
    
    token = parts[1]
    try:
        user_info = rbac_proxy.validate_jwt_token(token)
        session_id = user_info.get('session_id')
        session_data = active_sessions.get(session_id)
        if session_data:
            current_epoch_time = int(time.time())
            google_access_token = session_data['google_access_token']
            google_access_token_expiration = session_data['google_access_token_expiration']
            google_refresh_token = session_data['google_refresh_token']
            google_refresh_token_expiration = session_data['google_refresh_token_expiration']
            if current_epoch_time < google_access_token_expiration:
                return {"access_token": google_access_token, "expiration_time": google_access_token_expiration}
            else:
                if current_epoch_time < google_refresh_token_expiration:
                    # Refresh access token
                    refresh_response = idp_authenticator.refresh_google_token(google_refresh_token)
                    new_access_token = refresh_response['access_token']
                    new_expiration_time = int(time.time() + refresh_response['expires_in'])
                    active_sessions[session_id]['google_access_token'] = new_access_token
                    active_sessions[session_id]['google_access_token_expiration'] = new_expiration_time
                    
                    return {"access_token": new_access_token, "expiration_time": new_expiration_time}
                else:
                    raise HTTPException(status_code=401, detail="Please re-login to acquire new access token")
        else:
            raise HTTPException(status_code=401, detail="Session not found")
    except Exception as e:
        logger.error(f"Google access token validation failed: {e}")
        raise HTTPException(status_code=401, detail=str(e))

@app.get("/health")
async def health_check():
    """Detailed health check."""
    try:
        # Test IdP connectivity (basic check)
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "idp_client": "healthy",
                "rbac_manager": "healthy",
                "session_store": "healthy"
            },
            "metrics": {
                "active_sessions": len(active_sessions),
                "idp_type": config.get('idp_type')
            }
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


if __name__ == "__main__":
    # Load configuration
    config = load_config()
    
    # Run server
    uvicorn.run(
        "rbac_proxy:app",
        host=config['host'],
        port=config['port'],
        reload=config['debug'],
        log_level="info"
    )
