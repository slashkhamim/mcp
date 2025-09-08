#!/usr/bin/env python3
"""
Example usage of the MCP Authentication Tutorial
Demonstrates various authentication scenarios and use cases.
"""

import asyncio
import json
from auth_client import AuthenticatedMCPClient


async def example_basic_auth():
    """Example: Basic username/password authentication"""
    print("🔐 Example: Basic Authentication")
    print("-" * 40)
    
    async with AuthenticatedMCPClient() as client:
        # Login with default admin credentials
        success = await client.login_with_password("admin", "admin123")
        
        if success:
            # Get user profile
            profile = await client.call_tool("get_user_profile")
            print("User Profile:", json.dumps(profile, indent=2))
            
            # Create a secure note
            note = await client.call_tool("create_secure_note", {
                "title": "Welcome Note",
                "content": "This is a secure note created after authentication"
            })
            print("Created Note:", json.dumps(note, indent=2))


async def example_api_key_workflow():
    """Example: Complete API key workflow"""
    print("\n🔑 Example: API Key Workflow")
    print("-" * 40)
    
    async with AuthenticatedMCPClient() as client:
        # Step 1: Login with password to create API key
        await client.login_with_password("admin", "admin123")
        
        # Step 2: Create API key
        api_key = await client.create_api_key(
            name="automation_key",
            permissions=["read", "write", "create"],
            expires_days=30
        )
        
        if api_key:
            # Step 3: Clear JWT token and use API key
            client.access_token = None
            await client.login_with_api_key(api_key)
            
            # Step 4: Use API key for operations
            profile = await client.call_tool("get_user_profile")
            print("Profile via API Key:", json.dumps(profile, indent=2))


async def example_user_management():
    """Example: User registration and management"""
    print("\n👥 Example: User Management")
    print("-" * 40)
    
    async with AuthenticatedMCPClient() as client:
        # Register new user
        success = await client.register_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            role="user"
        )
        
        if success:
            # Login as new user
            await client.login_with_password("testuser", "TestPass123!")
            
            # Try to access user-level resources
            profile = await client.call_tool("get_user_profile")
            print("New User Profile:", json.dumps(profile, indent=2))
            
            # Try admin function (should fail)
            audit_events = await client.call_tool("list_audit_events")
            if not audit_events:
                print("✅ Correctly denied admin access to regular user")


async def example_security_monitoring():
    """Example: Security monitoring and audit logs"""
    print("\n🛡️  Example: Security Monitoring")
    print("-" * 40)
    
    async with AuthenticatedMCPClient() as client:
        # Login as admin
        await client.login_with_password("admin", "admin123")
        
        # Get security summary
        summary = await client.call_tool("get_security_summary", {"hours": 1})
        if summary:
            print("Security Summary:", json.dumps(summary, indent=2))
        
        # Get recent audit events
        events = await client.call_tool("list_audit_events", {"limit": 5})
        if events:
            print("Recent Events:", json.dumps(events, indent=2))


async def example_error_handling():
    """Example: Error handling and security scenarios"""
    print("\n⚠️  Example: Error Handling")
    print("-" * 40)
    
    async with AuthenticatedMCPClient() as client:
        # Test invalid credentials
        print("Testing invalid login...")
        success = await client.login_with_password("invalid", "wrong")
        print(f"Invalid login result: {success}")
        
        # Test unauthenticated access
        print("Testing unauthenticated access...")
        result = await client.call_tool("get_user_profile")
        print(f"Unauthenticated access result: {result}")
        
        # Test invalid API key
        print("Testing invalid API key...")
        success = await client.login_with_api_key("invalid_key_12345")
        print(f"Invalid API key result: {success}")


async def run_all_examples():
    """Run all authentication examples"""
    print("🚀 MCP Authentication Examples")
    print("=" * 50)
    
    try:
        await example_basic_auth()
        await example_api_key_workflow()
        await example_user_management()
        await example_security_monitoring()
        await example_error_handling()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("Make sure the MCP server is running with: python auth_server.py")


if __name__ == "__main__":
    asyncio.run(run_all_examples())
