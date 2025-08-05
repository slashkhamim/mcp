#!/usr/bin/env python3
"""
Main entry point for the File System MCP Server
"""

import asyncio
import sys
from server import mcp

def main():
    """Run the File System MCP Server"""
    print("🚀 Starting File System MCP Server...")
    print("📁 Ready to handle file operations!")
    
    try:
        # Run the MCP server
        mcp.run()
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
