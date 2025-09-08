#!/usr/bin/env python3
"""
Working MCP Server with Authentication
Compatible with MCP client connections.
"""

import asyncio
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import aiosqlite
from dotenv import load_dotenv
from functools import wraps

from mcp.server.fastmcp import FastMCP
from mcp.types import Tool, TextContent, Resource

from libs.auth_manager import AuthManager, User, UserRole
from libs.audit_logger import AuditLogger, AuditEventType, AuditLevel
from libs.security_utils import SecurityAuditor, InputValidator

# Load environment variables
load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-this")
DATABASE_PATH = os.getenv("DATABASE_PATH", "./auth.db")

# Initialize components
auth_manager = AuthManager(DATABASE_PATH, SECRET_KEY)
audit_logger = AuditLogger(DATABASE_PATH)

# Create MCP server
server = FastMCP("authenticated-mcp-server")

# Global variable to store current authenticated user
current_auth_user = None

# Authentication middleware decorators
def require_auth(func):
    """Middleware decorator to require authentication"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        global current_auth_user
        if not current_auth_user:
            return [TextContent(type="text", text=json.dumps({"error": "Authentication required"}))]
        return await func(*args, **kwargs)
    return wrapper

def require_admin(func):
    """Middleware decorator to require admin role"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        global current_auth_user
        if not current_auth_user:
            return [TextContent(type="text", text=json.dumps({"error": "Authentication required"}))]
        if current_auth_user.role != UserRole.ADMIN:
            return [TextContent(type="text", text=json.dumps({"error": "Admin access required"}))]
        return await func(*args, **kwargs)
    return wrapper

# Individual tool handlers with decorators

@server.tool()
async def authenticate_user(username: str, password: str) -> list[TextContent]:
    """Authenticate user with username and password"""
    global current_auth_user
    
    try:
        # Validate input
        if not InputValidator.validate_username(username):
            result = {"success": False, "error": "Invalid username format"}
            return [TextContent(type="text", text=json.dumps(result))]
        
        # Authenticate user
        user = await auth_manager.authenticate_user(username, password)
        
        if user:
            current_auth_user = user
            
            # Create access token
            access_token_expires = timedelta(minutes=30)
            access_token = auth_manager.create_access_token(user, access_token_expires)
            
            await audit_logger.log_authentication(
                AuditEventType.LOGIN_SUCCESS,
                user.id, user.username, True, {"ip_address": "localhost"}
            )
            
            result = {
                "success": True,
                "access_token": access_token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role.value
                }
            }
        else:
            await audit_logger.log_authentication(
                AuditEventType.LOGIN_FAILURE,
                None, username, False, {"ip_address": "localhost"},
                {"reason": "Invalid credentials"}
            )
            
            result = {"success": False, "error": "Invalid username or password"}
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        await audit_logger.log_security_event(
            AuditEventType.SYSTEM_ERROR,
            AuditLevel.ERROR,
            {"error": str(e), "tool": "authenticate_user"}
        )
        return [TextContent(type="text", text=json.dumps({"error": f"Internal error: {str(e)}"}, indent=2))]

@server.tool()
async def authenticate_with_api_key(api_key: str) -> list[TextContent]:
    """Authenticate using API key"""
    global current_auth_user
    
    try:
        user = await auth_manager.authenticate_api_key(api_key)
        
        if user:
            current_auth_user = user
            
            await audit_logger.log_api_key_event(
                AuditEventType.API_KEY_USED,
                user.id, user.username, "api_key_access", {"ip_address": "localhost"}
            )
            
            result = {
                "success": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role.value
                }
            }
        else:
            result = {"success": False, "error": "Invalid API key"}
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        await audit_logger.log_security_event(
            AuditEventType.SYSTEM_ERROR,
            AuditLevel.ERROR,
            {"error": str(e), "tool": "authenticate_with_api_key"}
        )
        return [TextContent(type="text", text=json.dumps({"error": f"Internal error: {str(e)}"}, indent=2))]

@server.tool()
@require_auth
async def get_user_profile() -> list[TextContent]:
    """Get current user's profile information (requires authentication)"""
    global current_auth_user
    
    profile = {
        "id": current_auth_user.id,
        "username": current_auth_user.username,
        "email": current_auth_user.email,
        "role": current_auth_user.role.value,
        "created_at": current_auth_user.created_at.isoformat(),
        "last_login": current_auth_user.last_login.isoformat() if current_auth_user.last_login else None
    }
    return [TextContent(type="text", text=json.dumps(profile, indent=2))]

@server.tool()
@require_auth
async def create_secure_note(title: str, content: str) -> list[TextContent]:
    """Create a secure note (authenticated users only)"""
    global current_auth_user
    
    try:
        # Sanitize input
        title = InputValidator.sanitize_string(title, 100)
        content = InputValidator.sanitize_string(content, 1000)
        
        note = {
            "id": f"note_{datetime.utcnow().timestamp()}",
            "title": title,
            "content": content,
            "author": current_auth_user.username,
            "created_at": datetime.utcnow().isoformat()
        }
        
        return [TextContent(type="text", text=json.dumps(note, indent=2))]
    except Exception as e:
        await audit_logger.log_security_event(
            AuditEventType.SYSTEM_ERROR,
            AuditLevel.ERROR,
            {"error": str(e), "tool": "create_secure_note"}
        )
        return [TextContent(type="text", text=json.dumps({"error": f"Internal error: {str(e)}"}, indent=2))]

@server.tool()
@require_admin
async def list_audit_events(limit: int = 10) -> list[TextContent]:
    """List recent audit events (admin only)"""
    try:
        events = await audit_logger.get_audit_events(limit=limit)
        return [TextContent(type="text", text=json.dumps(events, indent=2))]
    except Exception as e:
        await audit_logger.log_security_event(
            AuditEventType.SYSTEM_ERROR,
            AuditLevel.ERROR,
            {"error": str(e), "tool": "list_audit_events"}
        )
        return [TextContent(type="text", text=json.dumps({"error": f"Internal error: {str(e)}"}, indent=2))]

@server.tool()
@require_admin
async def get_security_summary(hours: int = 24) -> list[TextContent]:
    """Get security summary for the last N hours (admin only)"""
    try:
        summary = await audit_logger.get_security_summary(hours)
        return [TextContent(type="text", text=json.dumps(summary, indent=2))]
    except Exception as e:
        await audit_logger.log_security_event(
            AuditEventType.SYSTEM_ERROR,
            AuditLevel.ERROR,
            {"error": str(e), "tool": "get_security_summary"}
        )
        return [TextContent(type="text", text=json.dumps({"error": f"Internal error: {str(e)}"}, indent=2))]

@server.tool()
@require_auth
async def create_api_key(name: str, permissions: list = None, expires_days: int = None) -> list[TextContent]:
    """Create a new API key (authenticated users only)"""
    global current_auth_user
    
    try:
        if permissions is None:
            permissions = ["read"]
        
        api_key = await auth_manager.create_api_key(
            current_auth_user.id,
            name,
            permissions,
            expires_days
        )
        
        if api_key:
            expires_at = None
            if expires_days:
                expires_at = (datetime.utcnow() + timedelta(days=expires_days)).isoformat()
            
            await audit_logger.log_api_key_event(
                AuditEventType.API_KEY_CREATED,
                current_auth_user.id, current_auth_user.username,
                name, {"ip_address": "localhost"},
                {"permissions": permissions, "expires_days": expires_days}
            )
            
            result = {
                "success": True,
                "api_key": api_key,
                "name": name,
                "expires_at": expires_at
            }
        else:
            result = {"success": False, "error": "Failed to create API key"}
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    except Exception as e:
        await audit_logger.log_security_event(
            AuditEventType.SYSTEM_ERROR,
            AuditLevel.ERROR,
            {"error": str(e), "tool": "create_api_key"}
        )
        return [TextContent(type="text", text=json.dumps({"error": f"Internal error: {str(e)}"}, indent=2))]

@server.tool()
async def logout() -> list[TextContent]:
    """Logout current user"""
    global current_auth_user
    
    if current_auth_user:
        username = current_auth_user.username
        current_auth_user = None
        result = {"success": True, "message": f"User {username} logged out"}
    else:
        result = {"success": False, "message": "No user logged in"}
    
    return [TextContent(type="text", text=json.dumps(result))]


# Resources are handled through tools in FastMCP

async def init_server():
    """Initialize the server and database"""
    await auth_manager.init_db()
    await audit_logger.init_db()
    
    # Log server start
    await audit_logger.log_security_event(
        AuditEventType.SERVER_START,
        AuditLevel.INFO,
        {"server": "auth_mcp_server"},
        {"database": DATABASE_PATH}
    )
    
    print(f"🔐 Authenticated MCP Server initialized")
    print(f"📊 Database: {DATABASE_PATH}")
    print(f"🔍 Audit logging enabled")
    print(f"🚀 Server ready for MCP connections")

if __name__ == "__main__":
    # Initialize server
    asyncio.run(init_server())
    # Run the FastMCP server
    server.run()
