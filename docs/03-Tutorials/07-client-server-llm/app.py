#!/usr/bin/env python3
"""
App Runner entry point for the MCP server
This file serves as the main entry point for AWS App Runner
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import and run the main server
from storage_mcp_server import main

if __name__ == "__main__":
    main()
