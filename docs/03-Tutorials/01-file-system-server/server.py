#!/usr/bin/env python3
"""
File System MCP Server

Provides file system operations through MCP protocol.
Includes tools for file operations, resources for browsing, and prompts for automation.
"""

import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP
from file_operations import FileManager
from security import SecurityValidator

# Create MCP server
mcp = FastMCP("FileSystem")

# Initialize components
file_manager = FileManager()
security = SecurityValidator()

# File operation tools
@mcp.tool()
def read_file(path: str) -> str:
    """Read contents of a file"""
    try:
        validated_path = security.validate_path(path)
        return file_manager.read_file(validated_path)
    except Exception as e:
        return f"Error reading file: {str(e)}"

@mcp.tool()
def write_file(path: str, content: str, create_dirs: bool = False) -> str:
    """Write content to a file"""
    try:
        validated_path = security.validate_path(path)
        file_manager.write_file(validated_path, content, create_dirs)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

@mcp.tool()
def create_directory(path: str) -> str:
    """Create a new directory"""
    try:
        validated_path = security.validate_path(path)
        file_manager.create_directory(validated_path)
        return f"Successfully created directory {path}"
    except Exception as e:
        return f"Error creating directory: {str(e)}"

@mcp.tool()
def delete_file(path: str) -> str:
    """Delete a file"""
    try:
        validated_path = security.validate_path(path)
        file_manager.delete_file(validated_path)
        return f"Successfully deleted {path}"
    except Exception as e:
        return f"Error deleting file: {str(e)}"

@mcp.tool()
def list_directory(path: str = ".", show_hidden: bool = False) -> str:
    """List contents of a directory"""
    try:
        validated_path = security.validate_path(path)
        items = file_manager.list_directory(validated_path, show_hidden)
        
        result = f"Contents of {path}:\n"
        for item in items:
            icon = "📁" if item["is_dir"] else "📄"
            size = f" ({item['size']} bytes)" if not item["is_dir"] else ""
            result += f"{icon} {item['name']}{size}\n"
        
        return result
    except Exception as e:
        return f"Error listing directory: {str(e)}"

@mcp.tool()
def file_info(path: str) -> str:
    """Get detailed information about a file or directory"""
    try:
        validated_path = security.validate_path(path)
        info = file_manager.get_file_info(validated_path)
        
        result = f"File Information for {path}:\n"
        result += f"Type: {'Directory' if info['is_dir'] else 'File'}\n"
        result += f"Size: {info['size']} bytes\n"
        result += f"Modified: {info['modified']}\n"
        result += f"Permissions: {info['permissions']}\n"
        
        return result
    except Exception as e:
        return f"Error getting file info: {str(e)}"

# Directory browsing resources
@mcp.resource("fs://dir/{path}")
def browse_directory(path: str) -> str:
    """Browse directory contents as a resource"""
    try:
        # Decode URL-encoded path
        import urllib.parse
        decoded_path = urllib.parse.unquote(path)
        validated_path = security.validate_path(decoded_path)
        
        items = file_manager.list_directory(validated_path, show_hidden=False)
        
        # Format as JSON for structured access
        return json.dumps({
            "path": decoded_path,
            "items": items
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource("fs://file/{path}")
def file_content(path: str) -> str:
    """Get file content as a resource"""
    try:
        import urllib.parse
        decoded_path = urllib.parse.unquote(path)
        validated_path = security.validate_path(decoded_path)
        
        if not validated_path.is_file():
            return json.dumps({"error": "Path is not a file"})
        
        content = file_manager.read_file(validated_path)
        info = file_manager.get_file_info(validated_path)
        
        return json.dumps({
            "path": decoded_path,
            "content": content,
            "info": info
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

# File operation prompts
@mcp.prompt()
def file_script(operation: str, target: str, language: str = "bash") -> str:
    """Generate a script for file operations"""
    operations = {
        "backup": f"Create a backup script for {target}",
        "cleanup": f"Create a cleanup script for {target}",
        "organize": f"Create a file organization script for {target}",
        "sync": f"Create a sync script for {target}"
    }
    
    if operation not in operations:
        return f"Unknown operation: {operation}. Available: {', '.join(operations.keys())}"
    
    return f"""Generate a {language} script to {operations[operation]}.

Requirements:
- Include error handling
- Add logging/output messages
- Make it safe (no destructive operations without confirmation)
- Include comments explaining each step
- Handle edge cases (missing files, permissions, etc.)

Target: {target}
Language: {language}

Please provide a complete, production-ready script."""

@mcp.prompt()
def file_documentation(path: str, doc_type: str = "README") -> str:
    """Generate documentation for files/directories"""
    doc_types = {
        "README": "comprehensive README.md file",
        "API": "API documentation",
        "CHANGELOG": "changelog documentation",
        "CONTRIBUTING": "contributing guidelines"
    }
    
    selected_type = doc_types.get(doc_type, doc_types["README"])
    
    return f"""Generate {selected_type} for the project/directory at: {path}

Please analyze the structure and contents, then create:
- Clear project description
- Installation/setup instructions
- Usage examples
- File/directory structure explanation
- Any relevant configuration details

Make it comprehensive and user-friendly."""

if __name__ == "__main__":
    # Run the server
    import asyncio
    mcp.run()
