#!/usr/bin/env python3
"""
MCP Authentication Client
Demonstrates how to connect to and authenticate with an MCP server.
"""

import asyncio
import json
from typing import Optional, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class AuthenticatedMCPClient:
    """MCP client with authentication capabilities"""
    
    def __init__(self, server_command: str = "mcp_server.py"):
        self.server_command = server_command
        self.session: Optional[ClientSession] = None
        self.authenticated = False
        self.current_user = None
        self.access_token = None
        self.api_key = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self):
        """Connect to the MCP server"""
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "python", self.server_command],
            env=None
        )
        
        self.stdio_client = stdio_client(server_params)
        self.read, self.write = await self.stdio_client.__aenter__()
        self.session = ClientSession(self.read, self.write)
        await self.session.__aenter__()
        await self.session.initialize()
        
        print("✅ Connected to MCP server")
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.session:
            await self.session.__aexit__(None, None, None)
        if hasattr(self, 'stdio_client'):
            await self.stdio_client.__aexit__(None, None, None)
        print("🔌 Disconnected from MCP server")
    
    async def login_with_password(self, username: str, password: str) -> bool:
        """Authenticate using username and password"""
        try:
            result = await self.session.call_tool(
                "authenticate_user",
                {"username": username, "password": password}
            )
            
            response = json.loads(result.content[0].text)
            
            if response.get("success"):
                self.authenticated = True
                self.current_user = response.get("user")
                self.access_token = response.get("access_token")
                print(f"✅ Logged in as {username} (Role: {self.current_user['role']})")
                return True
            else:
                print(f"❌ Login failed: {response.get('error')}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    async def login_with_api_key(self, api_key: str) -> bool:
        """Authenticate using API key"""
        try:
            result = await self.session.call_tool(
                "authenticate_with_api_key",
                {"api_key": api_key}
            )
            
            response = json.loads(result.content[0].text)
            
            if response.get("success"):
                self.authenticated = True
                self.current_user = response.get("user")
                self.api_key = api_key
                print(f"✅ Authenticated with API key (User: {self.current_user['username']})")
                return True
            else:
                print(f"❌ API key authentication failed: {response.get('error')}")
                return False
                
        except Exception as e:
            print(f"❌ API key authentication error: {e}")
            return False
    
    async def logout(self) -> bool:
        """Logout current user"""
        try:
            result = await self.session.call_tool("logout", {})
            response = json.loads(result.content[0].text)
            
            if response.get("success"):
                self.authenticated = False
                self.current_user = None
                self.access_token = None
                self.api_key = None
                print("✅ Logged out successfully")
                return True
            else:
                print(f"❌ Logout failed: {response.get('message')}")
                return False
                
        except Exception as e:
            print(f"❌ Logout error: {e}")
            return False
    
    async def get_user_profile(self) -> Optional[Dict[str, Any]]:
        """Get current user's profile"""
        try:
            result = await self.session.call_tool("get_user_profile", {})
            response = json.loads(result.content[0].text)
            
            if "error" in response:
                print(f"❌ Profile access denied: {response['error']}")
                return None
            
            return response
            
        except Exception as e:
            print(f"❌ Profile error: {e}")
            return None
    
    async def create_secure_note(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        """Create a secure note"""
        try:
            result = await self.session.call_tool(
                "create_secure_note",
                {"title": title, "content": content}
            )
            response = json.loads(result.content[0].text)
            
            if "error" in response:
                print(f"❌ Note creation failed: {response['error']}")
                return None
            
            return response
            
        except Exception as e:
            print(f"❌ Note creation error: {e}")
            return None
    
    async def create_api_key(self, name: str, permissions: list = None, expires_days: int = None) -> Optional[str]:
        """Create a new API key"""
        try:
            args = {"name": name}
            if permissions:
                args["permissions"] = permissions
            if expires_days:
                args["expires_days"] = expires_days
            
            result = await self.session.call_tool("create_api_key", args)
            response = json.loads(result.content[0].text)
            
            if response.get("success"):
                api_key = response.get("api_key")
                print(f"✅ Created API key '{name}': {api_key}")
                return api_key
            else:
                print(f"❌ API key creation failed: {response.get('error')}")
                return None
                
        except Exception as e:
            print(f"❌ API key creation error: {e}")
            return None
    
    async def list_audit_events(self, limit: int = 10) -> Optional[list]:
        """List audit events (admin only)"""
        try:
            result = await self.session.call_tool(
                "list_audit_events",
                {"limit": limit}
            )
            response = json.loads(result.content[0].text)
            
            if "error" in response:
                print(f"❌ Audit access denied: {response['error']}")
                return None
            
            return response
            
        except Exception as e:
            print(f"❌ Audit events error: {e}")
            return None
    
    async def get_security_summary(self, hours: int = 24) -> Optional[Dict[str, Any]]:
        """Get security summary (admin only)"""
        try:
            result = await self.session.call_tool(
                "get_security_summary",
                {"hours": hours}
            )
            response = json.loads(result.content[0].text)
            
            if "error" in response:
                print(f"❌ Security summary access denied: {response['error']}")
                return None
            
            return response
            
        except Exception as e:
            print(f"❌ Security summary error: {e}")
            return None
    
    async def list_tools(self) -> list:
        """List available tools"""
        try:
            tools = await self.session.list_tools()
            return [tool.name for tool in tools.tools]
        except Exception as e:
            print(f"❌ Tools listing error: {e}")
            return []
    
    async def list_resources(self) -> list:
        """List available resources"""
        try:
            resources = await self.session.list_resources()
            return [str(res.uri) for res in resources.resources]
        except Exception as e:
            print(f"❌ Resources listing error: {e}")
            return []
    
    async def read_resource(self, uri: str) -> Optional[str]:
        """Read a resource"""
        try:
            result = await self.session.read_resource(uri)
            return result.contents[0].text
        except Exception as e:
            print(f"❌ Resource read error: {e}")
            return None


async def demo_authentication_flow():
    """Demonstrate the complete authentication flow"""
    print("🚀 MCP Authentication Client Demo")
    print("=" * 50)
    
    async with AuthenticatedMCPClient() as client:
        
        # Show available tools
        print("\n📋 Available tools:")
        tools = await client.list_tools()
        for tool in tools:
            print(f"  - {tool}")
        
        # Show available resources
        print("\n📚 Available resources:")
        resources = await client.list_resources()
        for resource in resources:
            print(f"  - {resource}")
        
        # Test 1: Login with admin credentials
        print("\n1️⃣  Testing admin login...")
        success = await client.login_with_password("admin", "admin123")
        
        if success:
            # Get user profile
            print("\n👤 User Profile:")
            profile = await client.get_user_profile()
            if profile:
                print(json.dumps(profile, indent=2))
            
            # Create a secure note
            print("\n📝 Creating secure note...")
            note = await client.create_secure_note(
                "Demo Note",
                "This note was created through the MCP client"
            )
            if note:
                print(f"Created note: {note['title']}")
            
            # Test admin functions
            print("\n🔍 Testing admin functions...")
            events = await client.list_audit_events(3)
            if events:
                print(f"Found {len(events)} audit events")
            
            summary = await client.get_security_summary(1)
            if summary:
                print("Security summary retrieved")
            
            # Create API key
            print("\n🔑 Creating API key...")
            api_key = await client.create_api_key(
                "demo_key",
                ["read", "write"],
                30
            )
            
            # Test API key authentication
            if api_key:
                print("\n🔐 Testing API key authentication...")
                await client.logout()
                
                success = await client.login_with_api_key(api_key)
                if success:
                    profile = await client.get_user_profile()
                    if profile:
                        print(f"API key login successful for: {profile['username']}")
        
        # Test 2: Regular user login
        print("\n2️⃣  Testing regular user login...")
        await client.logout()
        
        success = await client.login_with_password("testuser", "TestPass123!")
        if success:
            # Try admin function (should fail)
            print("\n🚫 Testing access control...")
            events = await client.list_audit_events()
            if not events:
                print("✅ Access control working - regular user denied admin access")
        
        print("\n✅ Demo completed!")


async def interactive_client():
    """Interactive MCP client for manual testing"""
    print("🎮 Interactive MCP Authentication Client")
    print("=" * 50)
    print("Commands: login, profile, note, apikey, audit, summary, logout, quit")
    
    async with AuthenticatedMCPClient() as client:
        while True:
            try:
                command = input("\n> ").strip().lower()
                
                if command == "quit":
                    break
                elif command == "login":
                    username = input("Username: ")
                    password = input("Password: ")
                    await client.login_with_password(username, password)
                elif command == "profile":
                    profile = await client.get_user_profile()
                    if profile:
                        print(json.dumps(profile, indent=2))
                elif command == "note":
                    title = input("Note title: ")
                    content = input("Note content: ")
                    note = await client.create_secure_note(title, content)
                    if note:
                        print(f"Created: {note['title']}")
                elif command == "apikey":
                    name = input("API key name: ")
                    api_key = await client.create_api_key(name)
                    if api_key:
                        print(f"API Key: {api_key}")
                elif command == "audit":
                    events = await client.list_audit_events(5)
                    if events:
                        print(json.dumps(events, indent=2))
                elif command == "summary":
                    summary = await client.get_security_summary()
                    if summary:
                        print(json.dumps(summary, indent=2))
                elif command == "logout":
                    await client.logout()
                else:
                    print("Unknown command. Available: login, profile, note, apikey, audit, summary, logout, quit")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(interactive_client())
    else:
        asyncio.run(demo_authentication_flow())
