#!/usr/bin/env python3
"""
App Runner entry point for the MCP server
This file serves as the main entry point for AWS App Runner
"""
import os
import sys

# Set environment variables for App Runner
os.environ.setdefault("PORT", "8080")
os.environ.setdefault("HOST", "0.0.0.0")

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main server
from storage_mcp_server import main

if __name__ == "__main__":
    print(f"🚀 Starting MCP server on {os.getenv('HOST')}:{os.getenv('PORT')}")
    main()
