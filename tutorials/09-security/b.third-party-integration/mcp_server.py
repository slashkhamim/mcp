"""
MCP Server for Internal Systems with JWT Authentication.
Provides secure access to internal databases and APIs with RBAC.
"""

import os
import uvicorn
import json
import asyncio
import logging
from typing import Callable, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

from fastmcp import FastMCP, Context
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.http import create_sse_app

from libs.google_api_adapter import GoogleApiAdapter

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
config: Dict[str, Any] = {}
rbac_proxy_url: str = ""
gapi_cache: dict[str, GoogleApiAdapter] = {}

def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    return {
        # JWT Configuration
        "jwt_issuer": os.getenv("JWT_ISSUER", "rbac-proxy"),
        "jwt_audience": os.getenv("JWT_AUDIENCE", "google-mcp-server"),
        
        # RBAC Proxy Configuration
        "rbac_proxy_url": os.getenv("RBAC_PROXY_URL", "http://localhost:8081"),
        "jwks_uri": os.getenv("JWKS_URI", "http://localhost:8081/auth/jwks"),

        # Google API Configuration
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "google_client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
    }

config = load_config()

auth = JWTVerifier(
    jwks_uri=config["jwks_uri"],
    issuer=config["jwt_issuer"],
    audience=config["jwt_audience"],
)
# Initialize MCP server
server = FastMCP(
    name="Google API MCP Server",
    instructions="A MCP server to interact with google api",
    auth=auth,
)

def get_google_api_adapter(rbac_token: str) -> GoogleApiAdapter:
    global gapi_cache
    if rbac_token not in gapi_cache:
        gapi_cache[rbac_token] = GoogleApiAdapter(
            client_id=config["google_client_id"],
            client_secret=config["google_client_secret"],
            rbac_proxy_url=config["rbac_proxy_url"],
            rbac_token=rbac_token,
        )
    return gapi_cache[rbac_token]

# Generic request processor
async def process_request(
    ctx: Context, 
    api_call: Callable[[Any, dict], Any]
) -> dict:
    """
    Generic request processor that extracts auth, gets API adapter, and calls the method.
    
    Args:
        ctx: The request context
        api_call: A callable that receives (adapter, claims) and returns result
    """
    try:
        claims = ctx.request_context.request.user.access_token.claims
        auth_header = (
            ctx.request_context.request.headers.get("authorization")
            or ctx.request_context.request.headers.get("Authorization")
        )
        rbac_token = auth_header.split(" ")[1]
        
        adapter = get_google_api_adapter(rbac_token)
        result = api_call(adapter, claims)

        return {
            "success": True,
            "data": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error in process_request: {e}")
        return {"success": False, "error": str(e)}


@server.tool("profile")
async def get_profile(ctx: Context) -> dict:
    """
    Query google profile data

    Returns:
        dict: The profile data.
    """
    return await process_request(
        ctx, 
        lambda adapter, claims: adapter.get_profile(claims)
    )


@server.tool("list_files")
async def list_files(ctx: Context, page_size: int = 10) -> dict:
    """
    List files from Google Drive
    
    Args:
        page_size: Number of files to return (default: 10)
    
    Returns:
        dict: List of files with their IDs and names
    """
    return await process_request(
        ctx,
        lambda adapter, claims: adapter.list_files(page_size, claims)
    )


@server.tool("list_emails")
async def list_emails(ctx: Context, max_results: int = 10) -> dict:
    """
    List emails from Gmail
    
    Args:
        max_results: Maximum number of emails to return (default: 10)
    
    Returns:
        dict: List of email messages
    """
    return await process_request(
        ctx,
        lambda adapter, claims: adapter.list_emails(max_results, claims)
    )


@server.tool("send_email")
async def send_email(ctx: Context, to: str, subject: str, body_text: str) -> dict:
    """
    Send an email via Gmail
    
    Args:
        to: Recipient email address
        subject: Email subject
        body_text: Email body content
    
    Returns:
        dict: Response from Gmail API with message details
    """
    return await process_request(
        ctx,
        lambda adapter, claims: adapter.send_email(to, subject, body_text, claims)
    )


@server.tool("list_calendars")
async def list_calendars(ctx: Context) -> dict:
    """
    List all calendars for the user
    
    Returns:
        dict: List of calendar items
    """
    return await process_request(
        ctx,
        lambda adapter, claims: adapter.list_calendars(claims)
    )


@server.tool("create_calendar")
async def create_calendar(ctx: Context, summary: str = "New Calendar") -> dict:
    """
    Create a new calendar
    
    Args:
        summary: Calendar name/title (default: "New Calendar")
    
    Returns:
        dict: Created calendar details
    """
    return await process_request(
        ctx,
        lambda adapter, claims: adapter.create_calendar(summary, claims)
    )


@server.tool("remove_calendar")
async def remove_calendar(ctx: Context, calendar_id: str) -> dict:
    """
    Remove/delete a calendar
    
    Args:
        calendar_id: ID of the calendar to remove
    
    Returns:
        dict: Status of the deletion operation
    """
    return await process_request(
        ctx,
        lambda adapter, claims: adapter.remove_calendar(calendar_id, claims)
    )


@server.tool("list_events")
async def list_events(ctx: Context, calendar_id: str = "primary", max_results: int = 10) -> dict:
    """
    List events from a calendar
    
    Args:
        calendar_id: Calendar ID to list events from (default: "primary")
        max_results: Maximum number of events to return (default: 10)
    
    Returns:
        dict: List of calendar events
    """
    return await process_request(
        ctx,
        lambda adapter, claims: adapter.list_events(calendar_id, max_results, claims)
    )


@server.tool("create_event")
async def create_event(
    ctx: Context, 
    summary: str,
    start_time: str,
    end_time: str,
    calendar_id: str = "primary",
    description: str = ""
) -> dict:
    """
    Create a new calendar event
    
    Args:
        summary: Event title/summary
        start_time: ISO 8601 datetime string (e.g., "2025-10-02T10:00:00Z")
        end_time: ISO 8601 datetime string (e.g., "2025-10-02T11:00:00Z")
        calendar_id: Calendar ID to create event in (default: "primary")
        description: Event description (default: "")
    
    Returns:
        dict: Created event details
    """
    return await process_request(
        ctx,
        lambda adapter, claims: adapter.create_event(
            calendar_id, 
            summary, 
            start_time, 
            end_time, 
            description, 
            claims
        )
    )

@server.resource("google://profile")
async def profile_resource() -> str:
    return json.dumps({
        "description": "Google profile access",
        "endpoints": [
            {
                "api": "GET /profile - get profile",
                "required_scopes": ["api:google:read"]
            }
        ]
    }, indent=2)

@server.resource("google://email")
async def email_resource() -> str:
    return json.dumps({
        "description": "Gmail access for managing emails",
        "required_scopes": ["api:google:read", "api:google:write"],
        "endpoints": [
            {
                "api": "GET /list_emails - list recent emails",
                "required_scopes": ["api:google:read"]
            },
            {
                "api": "POST /send_email - send a new email",
                "required_scopes": ["api:google:write"]
            }
        ]
    }, indent=2)

@server.resource("google://file")
async def file_resource() -> str:
    return json.dumps({
        "description": "Google Drive file access",
        "endpoints": [
            {
                "api": "GET /list_files - list files from Google Drive",
                "required_scopes": ["api:google:read"]
            }
        ]
    }, indent=2)

@server.resource("google://calendar")
async def calendar_resource() -> str:
    return json.dumps({
        "description": "Google Calendar management",
        "endpoints": [
            {
                "api": "GET /list_calendars - list all calendars",
                "required_scopes": ["api:google:read"]
            },
            {
                "api": "POST /create_calendar - create a new calendar",
                "required_scopes": ["api:google:write"]
            },
            {
                "api": "DELETE /remove_calendar - remove a calendar",
                "required_scopes": ["api:google:write"]
            }
        ]
    }, indent=2)

@server.resource("google://event")
async def event_resource() -> str:
    return json.dumps({
        "description": "Google Calendar event management",
        "endpoints": [
            {
                "api": "GET /list_events - list events from a calendar",
                "required_scopes": ["api:google:read"]
            },
            {
                "api": "POST /create_event - create a new calendar event",
                "required_scopes": ["api:google:write"]
            }
        ]
    }, indent=2)

async def main():
    global config, rbac_proxy_url
    rbac_proxy_url = config["rbac_proxy_url"]

if __name__ == "__main__":
    asyncio.run(main())
    print("🚀 Starting MCP server with SSE transport...")
    print("📡 Server will be available at: http://localhost:9999")
    app = create_sse_app(server, sse_path="/sse", message_path="/message", auth=auth)
    uvicorn.run(app, host="0.0.0.0", port=9999)