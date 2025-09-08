#!/usr/bin/env python3
"""
Simple test client for auth_server_working.py
Tests MCP server functionality and authentication.
"""

import asyncio
import json
import subprocess
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp_server():
    """Test the MCP authentication server"""
    print("🧪 Testing MCP Authentication Server")
    print("=" * 50)
    
    # Start the server process
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "mcp_server.py"],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            # Initialize the session
            await session.initialize()
            
            print("✅ Connected to MCP server")
            
            # Test 1: List available tools
            print("\n1️⃣  Testing tool listing...")
            tools = await session.list_tools()
            print(f"Available tools: {[tool.name for tool in tools.tools]}")
            
            # Test 2: Authentication with username/password
            print("\n2️⃣  Testing user authentication...")
            auth_result = await session.call_tool(
                "authenticate_user",
                {"username": "admin", "password": "admin123"}
            )
            print(f"Authentication result: {auth_result.content[0].text}")
            
            # Test 3: Get user profile (should work after auth)
            print("\n3️⃣  Testing authenticated access...")
            profile_result = await session.call_tool("get_user_profile", {})
            print(f"User profile: {profile_result.content[0].text}")
            
            # Test 4: Create a secure note
            print("\n4️⃣  Testing secure note creation...")
            note_result = await session.call_tool(
                "create_secure_note",
                {"title": "Test Note", "content": "This is a test note"}
            )
            print(f"Note created: {note_result.content[0].text}")
            
            # Test 5: Try admin function
            print("\n5️⃣  Testing admin access...")
            audit_result = await session.call_tool("list_audit_events", {"limit": 3})
            print(f"Audit events: {audit_result.content[0].text}")
            
            # Test 6: API Key creation
            print("\n6️⃣  Testing API key creation...")
            api_key_result = await session.call_tool(
                "create_api_key",
                {"name": "test_key", "permissions": ["read", "write"]}
            )
            print(f"API key created: {api_key_result.content[0].text}")
            
            # Test 7: Logout
            print("\n7️⃣  Testing logout...")
            logout_result = await session.call_tool("logout", {})
            print(f"Logout result: {logout_result.content[0].text}")
            
            # Test 8: Try access after logout (should fail)
            print("\n8️⃣  Testing access after logout...")
            profile_after_logout = await session.call_tool("get_user_profile", {})
            print(f"Profile after logout: {profile_after_logout.content[0].text}")
            
            print("\n✅ All tests completed!")

async def test_server_startup():
    """Test if server starts up correctly"""
    print("🚀 Testing server startup...")
    
    try:
        # Start server process and check if it initializes
        process = subprocess.Popen(
            ["uv", "run", "python", "mcp_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for startup
        await asyncio.sleep(2)
        
        # Check if process is still running (not crashed)
        if process.poll() is None:
            print("✅ Server started successfully")
            process.terminate()
            process.wait()
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ Server failed to start")
            print(f"STDOUT: {stdout}")
            print(f"STDERR: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return False

if __name__ == "__main__":
    async def main():
        # Test 1: Server startup
        startup_ok = await test_server_startup()
        
        if startup_ok:
            print("\n" + "="*50)
            # Test 2: Full MCP functionality
            try:
                await test_mcp_server()
            except Exception as e:
                print(f"❌ MCP test failed: {e}")
                print("Make sure the server is running: uv run python mcp_server.py")
        else:
            print("❌ Cannot test MCP functionality - server startup failed")
    
    asyncio.run(main())
