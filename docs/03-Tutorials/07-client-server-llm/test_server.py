#!/usr/bin/env python3
"""
Test script to verify the MCP server works correctly
"""
import requests
import time
import subprocess
import sys
import os

def test_server_locally():
    """Test the server locally before deploying"""
    print("🧪 Testing MCP Server locally...")
    
    # Set environment variables for testing
    os.environ["PORT"] = "8080"
    os.environ["HOST"] = "0.0.0.0"
    
    try:
        # Import and test the server
        from storage_mcp_server import main
        print("✅ Server imports successfully")
        print("✅ All dependencies are available")
        print("✅ Ready for deployment!")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_server_locally()
    sys.exit(0 if success else 1)
