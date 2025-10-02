"""
MCP Server for Internal Systems with JWT Authentication.
Provides secure access to internal databases and APIs with RBAC.
"""

import os
import uvicorn
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv

from fastmcp import FastMCP, Context
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.http import create_sse_app

from libs.database_manager import DatabaseManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
db_manager: Optional[DatabaseManager] = None
config: Dict[str, Any] = {}
rbac_proxy_url: str = ""


def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    return {
        # Database Configuration
        "db_type": os.getenv("DB_TYPE", "sqlite").lower(),
        "database_url": os.getenv("DATABASE_URL", "data/internal_system.db"),
        # JWT Configuration
        "jwt_issuer": os.getenv("JWT_ISSUER", "internal-rbac-proxy"),
        "jwt_audience": os.getenv("JWT_AUDIENCE", "internal-mcp-server"),
        # RBAC Proxy Configuration
        "rbac_proxy_url": os.getenv("RBAC_PROXY_URL", "http://localhost:8081"),
        "jwks_uri": os.getenv("JWKS_URI", "http://localhost:8081/auth/jwks"),
    }

config = load_config()

auth = JWTVerifier(
    jwks_uri=config["jwks_uri"],
    issuer=config["jwt_issuer"],
    audience=config["jwt_audience"],
)
# Initialize MCP server
server = FastMCP(
    name="Internal System MCP Server",
    instructions="A internal system server to list, create, update, and change status from internal system",
    auth=auth,
)

@server.tool("employees")
async def query_employees(
    ctx: Context,
    employee_id: Optional[str] = None
) -> dict:
    """
    Query employee data

    Args:
        employee_id (str): The ID of the employee.
        department (str): The department of the employee.

    Returns:
        dict: The employee data.
    """
    try:
        claims = ctx.request_context.request.user.access_token.claims
        # Query database
        if employee_id:
            results = db_manager.get_employee_data(employee_id, claims)
        else:
            results = db_manager.get_employee_data(None, claims)

        return {
            "success": True,
            "data": results,
            "count": len(results),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except ValueError as e:
        return {"success": False, "error": f"Authentication failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Error in query_employees: {e}")
        return {"success": False, "error": str(e)}

@server.tool("financial")
async def query_financial(
    ctx: Context,
    record_type: Optional[str] = None,
) -> dict:
    """
    Query financial data

    Args:
        record_type (str): The type of financial record.
        fiscal_year (str): The fiscal year of the financial record.

    Returns:
        dict: The financial data.
    """
    try:
        claims = ctx.request_context.request.user.access_token.claims
        results = db_manager.get_financial_data(record_type, claims)
        
        return {
            "success": True,
            "data": results,
            "count": len(results),
            "user": claims.get('email'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@server.tool("public_info")        
async def query_public_info(
    ctx: Context,
    category: Optional[str] = None,
) -> dict:
    """
    Query public information

    Args:
        category (str): The category of public information.

    Returns:
        dict: The public information.
    """
    try:
        claims = ctx.request_context.request.user.access_token.claims
        results = db_manager.get_public_info(category, claims)
        
        return {
            "success": True,
            "data": results,
            "count": len(results),
            "user": claims.get('email'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@server.resource("internal://employees")
async def employees_resource() -> str:
    return json.dumps({
        "description": "Employee database access",
        "required_scopes": ["db:read:employee", "api:hr:read"],
        "endpoints": [
            "GET /employees - List all employees",
            "GET /employees/{id} - Get specific employee"
        ]
    }, indent=2)

@server.resource("internal://financial")
async def financial_resource() -> str:
    return json.dumps({
        "description": "Financial records access",
        "required_scopes": ["db:read:financial", "api:finance:read"],
        "endpoints": [
            "GET /financial - List financial records",
            "GET /financial/{type} - Get records by type"
        ]
    }, indent=2)

async def main():
    global db_manager, config, rbac_proxy_url
    rbac_proxy_url = config["rbac_proxy_url"]
    db_manager = DatabaseManager(config)

    logger.info("Internal System MCP Server starting...")
    logger.info(f"Database type: {config['db_type']}")
    logger.info(f"RBAC Proxy URL: {rbac_proxy_url}")


if __name__ == "__main__":
    asyncio.run(main())
    print("🚀 Starting MCP server with SSE transport...")
    print("📡 Server will be available at: http://localhost:9999")
    app = create_sse_app(server, sse_path="/sse", message_path="/message", auth=auth)
    uvicorn.run(app, host="0.0.0.0", port=9999)