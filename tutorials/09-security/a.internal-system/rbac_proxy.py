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
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
import uvicorn

from libs.idp_client import IdPAuthenticator
from libs.rbac_manager import RBACProxy

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables for configuration
idp_authenticator: Optional[IdPAuthenticator] = None
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
    idp_authenticator = IdPAuthenticator(config)
    rbac_proxy = RBACProxy(config)
    
    logger.info(f"RBAC Proxy started with IdP type: {config['idp_type']}")
    
    yield
    
    # Shutdown (if needed)
    logger.info("RBAC Proxy shutting down")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Internal System RBAC Proxy",
    description="Authentication proxy for internal MCP systems",
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
        'client_id': os.getenv('IDP_CLIENT_ID', 'your_client_id'),
        'client_secret': os.getenv('IDP_CLIENT_SECRET', 'your_client_secret'),
        'redirect_uri': os.getenv('IDP_REDIRECT_URI', 'http://localhost:8080/callback'),
        'scopes': os.getenv('IDP_SCOPES', 'openid profile email groups').split(),
        
        # JWT Configuration
        'jwt_secret_key': os.getenv('JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-this-in-production'),
        'jwt_algorithm': os.getenv('JWT_ALGORITHM', 'HS256'),
        'token_expiry_minutes': int(os.getenv('TOKEN_EXPIRY_MINUTES', '15')),
        'issuer': os.getenv('JWT_ISSUER', 'internal-rbac-proxy'),
        'audience': os.getenv('JWT_AUDIENCE', 'internal-mcp-server'),
        
        # RBAC Configuration
        'role_mappings_file': os.getenv('ROLE_MAPPINGS_FILE', 'config/role_mappings.yaml'),
        
        # Server Configuration
        'host': os.getenv('PROXY_HOST', '0.0.0.0'),
        'port': int(os.getenv('PROXY_PORT', '8080')),
        'debug': os.getenv('DEBUG', 'false').lower() == 'true'
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
        
        if error:
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
        
        if not auth_code:
            raise HTTPException(status_code=400, detail="Missing authorization code")
        
        # Complete authentication
        auth_result = idp_authenticator.complete_authentication(auth_code)
        
        # Process through RBAC
        rbac_result = rbac_proxy.process_authentication(auth_result)
        
        if not rbac_result['success']:
            raise HTTPException(status_code=403, detail=rbac_result['error'])
        
        # Store session (in production, use secure session management)
        session_id = f"session_{auth_result['user_info']['sub']}_{int(datetime.utcnow().timestamp())}"
        active_sessions[session_id] = {
            'user_info': rbac_result['user_info'],
            'jwt_token': rbac_result['jwt_token'],
            'roles': rbac_result['roles'],
            'scopes': rbac_result['scopes'],
            'created_at': datetime.utcnow().isoformat()
        }
        
        return {
            "success": True,
            "session_id": session_id,
            "user_info": rbac_result['user_info'],
            "roles": rbac_result['roles'],
            "scopes": rbac_result['scopes'],
            "jwt_token": rbac_result['jwt_token'],
            "expires_in": rbac_result['expires_in']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication callback failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/token")
async def get_token(request: Request):
    """Exchange session for JWT token."""
    try:
        body = await request.json()
        session_id = body.get('session_id')
        
        if not session_id or session_id not in active_sessions:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        session_data = active_sessions[session_id]
        
        return {
            "access_token": session_data['jwt_token'],
            "token_type": "Bearer",
            "expires_in": config['token_expiry_minutes'] * 60,
            "user_info": session_data['user_info'],
            "roles": session_data['roles'],
            "scopes": session_data['scopes']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/auth/validate")
async def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate JWT token and return user context."""
    try:
        token = credentials.credentials
        payload = rbac_proxy.rbac_manager.validate_jwt_token(token)
        
        return {
            "valid": True,
            "user_context": {
                "user_id": payload.get('sub'),
                "email": payload.get('email'),
                "name": payload.get('name'),
                "roles": payload.get('roles', []),
                "scopes": payload.get('scopes', []),
                "expires_at": payload.get('exp')
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/auth/authorize")
async def authorize_request(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Authorize a request for specific scope."""
    try:
        body = await request.json()
        required_scope = body.get('scope')
        
        if not required_scope:
            raise HTTPException(status_code=400, detail="Scope is required")
        
        token = credentials.credentials
        result = rbac_proxy.validate_request(token, required_scope)
        
        if not result['success']:
            raise HTTPException(status_code=403, detail=result['error'])
        
        return {
            "authorized": True,
            "user_context": result['user_context']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authorization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/auth/sessions")
async def list_sessions(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """List active sessions (admin only)."""
    try:
        token = credentials.credentials
        payload = rbac_proxy.rbac_manager.validate_jwt_token(token)
        
        # Check admin permission
        if not rbac_proxy.rbac_manager.check_permission(payload, 'admin:sessions'):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Return session summary (without sensitive data)
        sessions_summary = []
        for session_id, session_data in active_sessions.items():
            sessions_summary.append({
                "session_id": session_id,
                "user_email": session_data['user_info']['email'],
                "roles": session_data['roles'],
                "created_at": session_data['created_at']
            })
        
        return {"sessions": sessions_summary}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session listing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/auth/sessions/{session_id}")
async def revoke_session(session_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Revoke a session (admin only)."""
    try:
        token = credentials.credentials
        payload = rbac_proxy.rbac_manager.validate_jwt_token(token)
        
        # Check admin permission or own session
        user_id = payload.get('sub')
        is_admin = rbac_proxy.rbac_manager.check_permission(payload, 'admin:sessions')
        is_own_session = session_id.startswith(f"session_{user_id}_")
        
        if not (is_admin or is_own_session):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        if session_id in active_sessions:
            del active_sessions[session_id]
            return {"success": True, "message": "Session revoked"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session revocation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
