#!/usr/bin/env python3
"""
Database MCP Server

Provides database operations through MCP protocol.
Includes tools for queries, resources for schema browsing, and prompts for SQL generation.
"""

import json
import sqlite3
from typing import Optional, Dict, Any, List
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from db_manager import DatabaseManager
from query_builder import QueryBuilder
from schema import SchemaInspector

# Create MCP server
mcp = FastMCP("Database")

# Initialize components
db_manager = DatabaseManager()
query_builder = QueryBuilder()
schema_inspector = SchemaInspector()

# Database operation tools
@mcp.tool()
def execute_query(sql: str, params: str = "[]", database: str = "default") -> str:
    """Execute a SQL query with optional parameters"""
    try:
        # Parse parameters
        param_list = json.loads(params) if params else []
        
        result = db_manager.execute_query(sql, param_list, database)
        
        if result["type"] == "select":
            return f"Query executed successfully. Rows returned: {len(result['data'])}\n" + \
                   json.dumps(result["data"][:10], indent=2)  # Limit to first 10 rows
        else:
            return f"Query executed successfully. Rows affected: {result.get('rows_affected', 0)}"
    
    except json.JSONDecodeError:
        return "Error: Parameters must be valid JSON array"
    except Exception as e:
        return f"Error executing query: {str(e)}"

@mcp.tool()
def create_table(table_name: str, columns: str, database: str = "default") -> str:
    """Create a new table with specified columns"""
    try:
        # Parse column definitions
        column_defs = json.loads(columns)
        
        sql = query_builder.build_create_table(table_name, column_defs)
        result = db_manager.execute_query(sql, [], database)
        
        return f"Table '{table_name}' created successfully"
    
    except json.JSONDecodeError:
        return "Error: Columns must be valid JSON format"
    except Exception as e:
        return f"Error creating table: {str(e)}"

@mcp.tool()
def insert_data(table_name: str, data: str, database: str = "default") -> str:
    """Insert data into a table"""
    try:
        # Parse data
        records = json.loads(data)
        if not isinstance(records, list):
            records = [records]
        
        sql, params = query_builder.build_insert(table_name, records)
        result = db_manager.execute_query(sql, params, database)
        
        return f"Inserted {len(records)} record(s) into '{table_name}'"
    
    except json.JSONDecodeError:
        return "Error: Data must be valid JSON format"
    except Exception as e:
        return f"Error inserting data: {str(e)}"

@mcp.tool()
def update_data(table_name: str, set_values: str, where_clause: str = "", database: str = "default") -> str:
    """Update data in a table"""
    try:
        # Parse set values
        values = json.loads(set_values)
        
        sql, params = query_builder.build_update(table_name, values, where_clause)
        result = db_manager.execute_query(sql, params, database)
        
        return f"Updated {result.get('rows_affected', 0)} record(s) in '{table_name}'"
    
    except json.JSONDecodeError:
        return "Error: Set values must be valid JSON format"
    except Exception as e:
        return f"Error updating data: {str(e)}"

@mcp.tool()
def delete_data(table_name: str, where_clause: str, database: str = "default") -> str:
    """Delete data from a table"""
    try:
        if not where_clause:
            return "Error: WHERE clause is required for DELETE operations (safety measure)"
        
        sql = f"DELETE FROM {table_name} WHERE {where_clause}"
        result = db_manager.execute_query(sql, [], database)
        
        return f"Deleted {result.get('rows_affected', 0)} record(s) from '{table_name}'"
    
    except Exception as e:
        return f"Error deleting data: {str(e)}"

@mcp.tool()
def backup_database(database: str = "default", backup_path: str = None) -> str:
    """Create a backup of the database"""
    try:
        backup_file = db_manager.backup_database(database, backup_path)
        return f"Database backed up to: {backup_file}"
    except Exception as e:
        return f"Error backing up database: {str(e)}"

@mcp.tool()
def get_table_info(table_name: str, database: str = "default") -> str:
    """Get detailed information about a table"""
    try:
        info = schema_inspector.get_table_info(table_name, database)
        return json.dumps(info, indent=2)
    except Exception as e:
        return f"Error getting table info: {str(e)}"

# Database schema resources
@mcp.resource("db://schema/{database}")
def get_database_schema(database: str) -> str:
    """Get complete database schema"""
    try:
        schema = schema_inspector.get_full_schema(database)
        return json.dumps(schema, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource("db://table/{database}/{table_name}")
def get_table_data(database: str, table_name: str) -> str:
    """Get sample data from a table"""
    try:
        # Get first 50 rows
        result = db_manager.execute_query(
            f"SELECT * FROM {table_name} LIMIT 50", 
            [], 
            database
        )
        
        return json.dumps({
            "table": table_name,
            "sample_data": result["data"],
            "total_shown": len(result["data"])
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource("db://query/{database}")
def get_query_history(database: str) -> str:
    """Get recent query history for a database"""
    try:
        history = db_manager.get_query_history(database)
        return json.dumps({
            "database": database,
            "recent_queries": history
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

# SQL generation prompts
@mcp.prompt()
def generate_sql(description: str, table_info: str = "", query_type: str = "SELECT") -> str:
    """Generate SQL query from natural language description"""
    query_types = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER"]
    
    if query_type.upper() not in query_types:
        return f"Unknown query type: {query_type}. Available: {', '.join(query_types)}"
    
    return f"""Generate a {query_type} SQL query based on this description: {description}

Table Information:
{table_info}

Requirements:
- Write clean, readable SQL with proper formatting
- Include comments explaining complex logic
- Use parameterized queries for user inputs
- Add appropriate indexes suggestions if needed
- Consider performance implications
- Include error handling considerations

Query Type: {query_type}
Description: {description}

Please provide the complete SQL query with explanations."""

@mcp.prompt()
def database_migration(from_schema: str, to_schema: str, database_type: str = "sqlite") -> str:
    """Generate database migration script"""
    return f"""Generate a database migration script to transform the schema.

From Schema:
{from_schema}

To Schema:
{to_schema}

Database Type: {database_type}

Please provide:
1. Complete migration script (UP)
2. Rollback script (DOWN)
3. Data migration steps if needed
4. Index and constraint updates
5. Performance considerations
6. Safety checks and validations

Make it production-ready with proper error handling."""

@mcp.prompt()
def optimize_query(slow_query: str, table_schemas: str = "") -> str:
    """Generate query optimization suggestions"""
    return f"""Analyze this SQL query and provide optimization suggestions:

Query:
{slow_query}

Table Schemas:
{table_schemas}

Please provide:
1. Performance analysis of the current query
2. Suggested optimizations and rewrites
3. Index recommendations
4. Query execution plan considerations
5. Alternative approaches
6. Benchmarking strategies

Focus on practical improvements that will have measurable impact."""

if __name__ == "__main__":
    # Run the server
    import asyncio
    mcp.run()
