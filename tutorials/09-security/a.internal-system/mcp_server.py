"""
MCP Server for Internal Systems with JWT Authentication.
Provides secure access to internal databases and APIs with RBAC.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import mcp.types as types
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
import requests

from libs.database_manager import DatabaseManager
from libs.rbac_manager import RBACManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
db_manager: Optional[DatabaseManager] = None
rbac_manager: Optional[RBACManager] = None
config: Dict[str, Any] = {}
rbac_proxy_url: str = ""


def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    return {
        # Database Configuration
        'db_type': os.getenv('DB_TYPE', 'sqlite').lower(),
        'database_url': os.getenv('DATABASE_URL', 'data/internal_system.db'),
        
        # JWT Configuration
        'jwt_secret_key': os.getenv('JWT_SECRET_KEY'),
        'jwt_algorithm': os.getenv('JWT_ALGORITHM', 'HS256'),
        'issuer': os.getenv('JWT_ISSUER', 'internal-rbac-proxy'),
        'audience': os.getenv('JWT_AUDIENCE', 'internal-mcp-server'),
        
        # RBAC Proxy Configuration
        'rbac_proxy_url': os.getenv('RBAC_PROXY_URL', 'http://localhost:8080'),
        'jwks_url': os.getenv('JWKS_URL'),  # Optional for RS256
        
        # Server Configuration
        'audit_enabled': os.getenv('AUDIT_ENABLED', 'true').lower() == 'true',
        'role_mappings_file': os.getenv('ROLE_MAPPINGS_FILE', 'config/role_mappings.yaml')
    }


async def validate_jwt_token(token: str) -> Dict[str, Any]:
    """Validate JWT token with RBAC proxy."""
    try:
        # First try local validation if we have the secret/keys
        if rbac_manager:
            return rbac_manager.validate_jwt_token(token)
    except Exception as e:
        logger.warning(f"Local JWT validation failed: {e}")
    
    # Fallback to RBAC proxy validation
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.post(
            f"{rbac_proxy_url}/auth/validate",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['user_context']
        else:
            raise Exception(f"Token validation failed: {response.text}")
            
    except Exception as e:
        raise Exception(f"JWT validation error: {str(e)}")


def extract_token_from_context(context: Dict[str, Any]) -> Optional[str]:
    """Extract JWT token from MCP context."""
    # Check for Authorization header
    headers = context.get('headers', {})
    auth_header = headers.get('authorization') or headers.get('Authorization')
    
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Check for token in context metadata
    metadata = context.get('metadata', {})
    return metadata.get('jwt_token')


# Initialize MCP server
server = Server("internal-system-mcp")


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """List available internal system resources."""
    return [
        types.Resource(
            uri="internal://employees",
            name="Employee Database",
            description="Access to employee records and HR data",
            mimeType="application/json"
        ),
        types.Resource(
            uri="internal://financial",
            name="Financial Records",
            description="Access to financial data and records",
            mimeType="application/json"
        ),
        types.Resource(
            uri="internal://public",
            name="Public Information",
            description="Company policies, announcements, and public data",
            mimeType="application/json"
        ),
        types.Resource(
            uri="internal://system",
            name="System Logs",
            description="System logs and monitoring data",
            mimeType="application/json"
        )
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read internal system resources with authentication."""
    # This would typically be called with authentication context
    # For now, return resource descriptions
    
    resource_info = {
        "internal://employees": {
            "description": "Employee database access",
            "required_scopes": ["db:read:employee", "api:hr:read"],
            "endpoints": [
                "GET /employees - List all employees",
                "GET /employees/{id} - Get specific employee"
            ]
        },
        "internal://financial": {
            "description": "Financial records access",
            "required_scopes": ["db:read:financial", "api:finance:read"],
            "endpoints": [
                "GET /financial - List financial records",
                "GET /financial/{type} - Get records by type"
            ]
        },
        "internal://public": {
            "description": "Public information access",
            "required_scopes": ["db:read:public"],
            "endpoints": [
                "GET /public - List public information",
                "GET /public/{category} - Get info by category"
            ]
        },
        "internal://system": {
            "description": "System logs access",
            "required_scopes": ["db:read:system", "api:system:read"],
            "endpoints": [
                "GET /logs - List system logs",
                "GET /logs/{level} - Get logs by level"
            ]
        }
    }
    
    if uri in resource_info:
        return json.dumps(resource_info[uri], indent=2)
    else:
        raise ValueError(f"Unknown resource: {uri}")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available internal system tools."""
    return [
        types.Tool(
            name="query_employees",
            description="Query employee database with RBAC controls",
            inputSchema={
                "type": "object",
                "properties": {
                    "employee_id": {
                        "type": "string",
                        "description": "Specific employee ID to query (optional)"
                    },
                    "department": {
                        "type": "string",
                        "description": "Filter by department (optional)"
                    },
                    "jwt_token": {
                        "type": "string",
                        "description": "JWT authentication token"
                    }
                },
                "required": ["jwt_token"]
            }
        ),
        types.Tool(
            name="query_financial",
            description="Query financial records with strict access controls",
            inputSchema={
                "type": "object",
                "properties": {
                    "record_type": {
                        "type": "string",
                        "description": "Type of financial record (salary, bonus, expense, etc.)"
                    },
                    "fiscal_year": {
                        "type": "integer",
                        "description": "Fiscal year filter (optional)"
                    },
                    "jwt_token": {
                        "type": "string",
                        "description": "JWT authentication token"
                    }
                },
                "required": ["jwt_token"]
            }
        ),
        types.Tool(
            name="query_public_info",
            description="Query public company information",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Information category (policies, announcements, etc.)"
                    },
                    "jwt_token": {
                        "type": "string",
                        "description": "JWT authentication token"
                    }
                },
                "required": ["jwt_token"]
            }
        ),
        types.Tool(
            name="query_system_logs",
            description="Query system logs (admin access required)",
            inputSchema={
                "type": "object",
                "properties": {
                    "log_level": {
                        "type": "string",
                        "description": "Log level filter (error, warning, info, debug)"
                    },
                    "component": {
                        "type": "string",
                        "description": "System component filter (optional)"
                    },
                    "jwt_token": {
                        "type": "string",
                        "description": "JWT authentication token"
                    }
                },
                "required": ["jwt_token"]
            }
        ),
        types.Tool(
            name="create_employee",
            description="Create new employee record (HR admin access required)",
            inputSchema={
                "type": "object",
                "properties": {
                    "employee_data": {
                        "type": "object",
                        "properties": {
                            "employee_id": {"type": "string"},
                            "first_name": {"type": "string"},
                            "last_name": {"type": "string"},
                            "email": {"type": "string"},
                            "department": {"type": "string"},
                            "position": {"type": "string"},
                            "salary": {"type": "number"},
                            "hire_date": {"type": "string"}
                        },
                        "required": ["employee_id", "first_name", "last_name", "email", "department"]
                    },
                    "jwt_token": {
                        "type": "string",
                        "description": "JWT authentication token"
                    }
                },
                "required": ["employee_data", "jwt_token"]
            }
        ),
        types.Tool(
            name="execute_custom_query",
            description="Execute custom database query (admin access required)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Query parameters (optional)"
                    },
                    "jwt_token": {
                        "type": "string",
                        "description": "JWT authentication token"
                    }
                },
                "required": ["query", "jwt_token"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls with JWT authentication."""
    try:
        # Extract and validate JWT token
        jwt_token = arguments.get('jwt_token')
        if not jwt_token:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": "JWT token is required"}, indent=2)
            )]
        
        # Validate token and get user context
        try:
            user_context = await validate_jwt_token(jwt_token)
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=json.dumps({"error": f"Authentication failed: {str(e)}"}, indent=2)
            )]
        
        # Route to appropriate handler
        if name == "query_employees":
            result = await handle_query_employees(arguments, user_context)
        elif name == "query_financial":
            result = await handle_query_financial(arguments, user_context)
        elif name == "query_public_info":
            result = await handle_query_public_info(arguments, user_context)
        elif name == "query_system_logs":
            result = await handle_query_system_logs(arguments, user_context)
        elif name == "create_employee":
            result = await handle_create_employee(arguments, user_context)
        elif name == "execute_custom_query":
            result = await handle_custom_query(arguments, user_context)
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return [types.TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]
        
    except Exception as e:
        logger.error(f"Tool call error: {e}")
        return [types.TextContent(
            type="text",
            text=json.dumps({"error": str(e)}, indent=2)
        )]


async def handle_query_employees(arguments: dict, user_context: dict) -> dict:
    """Handle employee queries."""
    try:
        employee_id = arguments.get('employee_id')
        department = arguments.get('department')
        
        if employee_id:
            results = db_manager.get_employee_data(employee_id, user_context)
        else:
            results = db_manager.get_employee_data(user_context=user_context)
        
        # Filter by department if specified
        if department:
            results = [r for r in results if r.get('department', '').lower() == department.lower()]
        
        return {
            "success": True,
            "data": results,
            "count": len(results),
            "user": user_context.get('email'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_query_financial(arguments: dict, user_context: dict) -> dict:
    """Handle financial data queries."""
    try:
        record_type = arguments.get('record_type')
        fiscal_year = arguments.get('fiscal_year')
        
        results = db_manager.get_financial_data(record_type, user_context)
        
        # Filter by fiscal year if specified
        if fiscal_year:
            results = [r for r in results if r.get('fiscal_year') == fiscal_year]
        
        return {
            "success": True,
            "data": results,
            "count": len(results),
            "user": user_context.get('email'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_query_public_info(arguments: dict, user_context: dict) -> dict:
    """Handle public information queries."""
    try:
        category = arguments.get('category')
        
        results = db_manager.get_public_info(category, user_context)
        
        return {
            "success": True,
            "data": results,
            "count": len(results),
            "user": user_context.get('email'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_query_system_logs(arguments: dict, user_context: dict) -> dict:
    """Handle system log queries."""
    try:
        log_level = arguments.get('log_level')
        
        results = db_manager.get_system_logs(log_level, user_context)
        
        return {
            "success": True,
            "data": results,
            "count": len(results),
            "user": user_context.get('email'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_create_employee(arguments: dict, user_context: dict) -> dict:
    """Handle employee creation."""
    try:
        employee_data = arguments.get('employee_data')
        
        result = db_manager.create_employee(employee_data, user_context)
        
        return {
            "success": True,
            "result": result,
            "user": user_context.get('email'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


async def handle_custom_query(arguments: dict, user_context: dict) -> dict:
    """Handle custom database queries."""
    try:
        query = arguments.get('query')
        parameters = arguments.get('parameters', {})
        
        # Additional security check for custom queries
        user_scopes = user_context.get('scopes', [])
        has_admin_access = any(scope in ['*', 'admin:*', 'db:admin'] for scope in user_scopes)
        
        if not has_admin_access:
            return {"success": False, "error": "Admin access required for custom queries"}
        
        results = db_manager.execute_query(query, parameters, user_context)
        
        return {
            "success": True,
            "data": results,
            "count": len(results),
            "user": user_context.get('email'),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """List available prompts for internal system operations."""
    return [
        types.Prompt(
            name="employee_report",
            description="Generate employee report with proper access controls",
            arguments=[
                types.PromptArgument(
                    name="department",
                    description="Department to generate report for",
                    required=False
                ),
                types.PromptArgument(
                    name="jwt_token",
                    description="JWT authentication token",
                    required=True
                )
            ]
        ),
        types.Prompt(
            name="financial_summary",
            description="Generate financial summary (finance access required)",
            arguments=[
                types.PromptArgument(
                    name="fiscal_year",
                    description="Fiscal year for summary",
                    required=False
                ),
                types.PromptArgument(
                    name="jwt_token",
                    description="JWT authentication token",
                    required=True
                )
            ]
        )
    ]


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict) -> types.GetPromptResult:
    """Handle prompt requests with authentication."""
    jwt_token = arguments.get('jwt_token')
    if not jwt_token:
        return types.GetPromptResult(
            description="Authentication required",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text="Error: JWT token is required for all operations"
                    )
                )
            ]
        )
    
    try:
        user_context = await validate_jwt_token(jwt_token)
    except Exception as e:
        return types.GetPromptResult(
            description="Authentication failed",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Authentication error: {str(e)}"
                    )
                )
            ]
        )
    
    if name == "employee_report":
        return await generate_employee_report(arguments, user_context)
    elif name == "financial_summary":
        return await generate_financial_summary(arguments, user_context)
    else:
        return types.GetPromptResult(
            description="Unknown prompt",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Unknown prompt: {name}"
                    )
                )
            ]
        )


async def generate_employee_report(arguments: dict, user_context: dict) -> types.GetPromptResult:
    """Generate employee report prompt."""
    department = arguments.get('department')
    
    try:
        # Get employee data
        employees = db_manager.get_employee_data(user_context=user_context)
        
        if department:
            employees = [e for e in employees if e.get('department', '').lower() == department.lower()]
        
        report_text = f"""
Employee Report for {user_context.get('email')}
Generated: {datetime.utcnow().isoformat()}
Department Filter: {department or 'All'}

Total Employees: {len(employees)}

Employee Details:
"""
        
        for emp in employees:
            report_text += f"""
- {emp.get('first_name')} {emp.get('last_name')} ({emp.get('employee_id')})
  Email: {emp.get('email')}
  Department: {emp.get('department')}
  Position: {emp.get('position')}
  Status: {emp.get('status')}
"""
        
        return types.GetPromptResult(
            description=f"Employee report for {department or 'all departments'}",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=report_text
                    )
                )
            ]
        )
        
    except Exception as e:
        return types.GetPromptResult(
            description="Report generation failed",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Error generating employee report: {str(e)}"
                    )
                )
            ]
        )


async def generate_financial_summary(arguments: dict, user_context: dict) -> types.GetPromptResult:
    """Generate financial summary prompt."""
    fiscal_year = arguments.get('fiscal_year')
    
    try:
        # Get financial data
        financial_data = db_manager.get_financial_data(user_context=user_context)
        
        if fiscal_year:
            financial_data = [f for f in financial_data if f.get('fiscal_year') == int(fiscal_year)]
        
        # Calculate summaries
        total_amount = sum(f.get('amount', 0) for f in financial_data)
        record_types = {}
        
        for record in financial_data:
            record_type = record.get('record_type', 'unknown')
            if record_type not in record_types:
                record_types[record_type] = {'count': 0, 'amount': 0}
            record_types[record_type]['count'] += 1
            record_types[record_type]['amount'] += record.get('amount', 0)
        
        summary_text = f"""
Financial Summary for {user_context.get('email')}
Generated: {datetime.utcnow().isoformat()}
Fiscal Year Filter: {fiscal_year or 'All'}

Total Records: {len(financial_data)}
Total Amount: ${total_amount:,.2f}

Breakdown by Record Type:
"""
        
        for record_type, data in record_types.items():
            summary_text += f"""
- {record_type.title()}: {data['count']} records, ${data['amount']:,.2f}
"""
        
        return types.GetPromptResult(
            description=f"Financial summary for {fiscal_year or 'all years'}",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=summary_text
                    )
                )
            ]
        )
        
    except Exception as e:
        return types.GetPromptResult(
            description="Summary generation failed",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Error generating financial summary: {str(e)}"
                    )
                )
            ]
        )


async def main():
    """Main server function."""
    global db_manager, rbac_manager, config, rbac_proxy_url
    
    # Load configuration
    config = load_config()
    rbac_proxy_url = config['rbac_proxy_url']
    
    # Initialize database manager
    db_manager = DatabaseManager(config)
    
    # Initialize RBAC manager for local token validation
    try:
        rbac_manager = RBACManager(config)
        logger.info("RBAC manager initialized for local token validation")
    except Exception as e:
        logger.warning(f"RBAC manager initialization failed: {e}. Using proxy validation only.")
        rbac_manager = None
    
    logger.info("Internal System MCP Server starting...")
    logger.info(f"Database type: {config['db_type']}")
    logger.info(f"RBAC Proxy URL: {rbac_proxy_url}")
    
    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="internal-system-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
