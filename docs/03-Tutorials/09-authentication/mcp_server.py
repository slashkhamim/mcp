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

from mcp.server import Server
from mcp.types import Tool, TextContent, Resource
import mcp.server.stdio

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
server = Server("authenticated-mcp-server")

# Global variable to store current authenticated user
current_auth_user = None

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="authenticate_user",
            description="Authenticate user with username and password",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "password": {"type": "string"}
                },
                "required": ["username", "password"]
            }
        ),
        Tool(
            name="authenticate_with_api_key",
            description="Authenticate using API key",
            inputSchema={
                "type": "object",
                "properties": {
                    "api_key": {"type": "string"}
                },
                "required": ["api_key"]
            }
        ),
        Tool(
            name="get_user_profile",
            description="Get current user's profile information (requires authentication)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="create_secure_note",
            description="Create a secure note (authenticated users only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["title", "content"]
            }
        ),
        Tool(
            name="list_audit_events",
            description="List recent audit events (admin only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10}
                }
            }
        ),
        Tool(
            name="get_security_summary",
            description="Get security summary for the last N hours (admin only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "hours": {"type": "integer", "default": 24}
                }
            }
        ),
        Tool(
            name="create_api_key",
            description="Create a new API key (authenticated users only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "permissions": {"type": "array", "items": {"type": "string"}},
                    "expires_days": {"type": "integer"}
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="logout",
            description="Logout current user",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    global current_auth_user
    
    if name == "authenticate_user":
        username = arguments.get("username")
        password = arguments.get("password")
        
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
    
    elif name == "authenticate_with_api_key":
        api_key = arguments.get("api_key")
        
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
    
    elif name == "get_user_profile":
        if not current_auth_user:
            result = {"error": "Authentication required"}
            return [TextContent(type="text", text=json.dumps(result))]
        
        profile = {
            "id": current_auth_user.id,
            "username": current_auth_user.username,
            "email": current_auth_user.email,
            "role": current_auth_user.role.value,
            "created_at": current_auth_user.created_at.isoformat(),
            "last_login": current_auth_user.last_login.isoformat() if current_auth_user.last_login else None
        }
        return [TextContent(type="text", text=json.dumps(profile, indent=2))]
    
    elif name == "create_secure_note":
        if not current_auth_user:
            result = {"error": "Authentication required"}
            return [TextContent(type="text", text=json.dumps(result))]
        
        title = arguments.get("title", "")
        content = arguments.get("content", "")
        
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
    
    elif name == "list_audit_events":
        if not current_auth_user:
            result = {"error": "Authentication required"}
            return [TextContent(type="text", text=json.dumps(result))]
        
        if current_auth_user.role != UserRole.ADMIN:
            result = {"error": "Admin access required"}
            return [TextContent(type="text", text=json.dumps(result))]
        
        limit = arguments.get("limit", 10)
        events = await audit_logger.get_audit_events(limit=limit)
        return [TextContent(type="text", text=json.dumps(events, indent=2))]
    
    elif name == "get_security_summary":
        if not current_auth_user:
            result = {"error": "Authentication required"}
            return [TextContent(type="text", text=json.dumps(result))]
        
        if current_auth_user.role != UserRole.ADMIN:
            result = {"error": "Admin access required"}
            return [TextContent(type="text", text=json.dumps(result))]
        
        hours = arguments.get("hours", 24)
        summary = await audit_logger.get_security_summary(hours)
        return [TextContent(type="text", text=json.dumps(summary, indent=2))]
    
    elif name == "create_api_key":
        if not current_auth_user:
            result = {"error": "Authentication required"}
            return [TextContent(type="text", text=json.dumps(result))]
        
        name_arg = arguments.get("name")
        permissions = arguments.get("permissions", ["read"])
        expires_days = arguments.get("expires_days")
        
        api_key = await auth_manager.create_api_key(
            current_auth_user.id,
            name_arg,
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
                name_arg, {"ip_address": "localhost"},
                {"permissions": permissions, "expires_days": expires_days}
            )
            
            result = {
                "success": True,
                "api_key": api_key,
                "name": name_arg,
                "expires_at": expires_at
            }
        else:
            result = {"success": False, "error": "Failed to create API key"}
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "logout":
        if current_auth_user:
            username = current_auth_user.username
            current_auth_user = None
            result = {"success": True, "message": f"User {username} logged out"}
        else:
            result = {"success": False, "message": "No user logged in"}
        
        return [TextContent(type="text", text=json.dumps(result))]
    
    else:
        result = {"error": f"Unknown tool: {name}"}
        return [TextContent(type="text", text=json.dumps(result))]

@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="user://profile",
            name="User Profile",
            description="Current user's profile information",
            mimeType="application/json"
        ),
        Resource(
            uri="security://summary",
            name="Security Summary",
            description="Security summary and audit information",
            mimeType="application/json"
        )
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Handle resource reads"""
    if str(uri) == "user://profile":
        if not current_auth_user:
            return json.dumps({"error": "Authentication required"})
        
        profile = {
            "id": current_auth_user.id,
            "username": current_auth_user.username,
            "email": current_auth_user.email,
            "role": current_auth_user.role.value,
            "created_at": current_auth_user.created_at.isoformat(),
            "last_login": current_auth_user.last_login.isoformat() if current_auth_user.last_login else None
        }
        return json.dumps(profile, indent=2)
    
    elif str(uri) == "security://summary":
        if not current_auth_user:
            return json.dumps({"error": "Authentication required"})
        
        if current_auth_user.role != UserRole.ADMIN:
            return json.dumps({"error": "Admin access required"})
        
        summary = await audit_logger.get_security_summary(24)
        return json.dumps(summary, indent=2)
    
    else:
        return json.dumps({"error": f"Unknown resource: {uri}"})

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

async def main():
    # Initialize server
    await init_server()
    
    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
