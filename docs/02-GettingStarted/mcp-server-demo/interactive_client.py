#!/usr/bin/env python3
"""
Interactive MCP Client for testing the server.

This provides a simple command-line interface to interact with your MCP server.
"""

import asyncio
import json
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@asynccontextmanager
async def create_server_connection():
    """Create a connection to the MCP server."""
    server_params = StdioServerParameters(
        command="uv", 
        args=["run", "mcp", "run", "main.py"],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


class MCPInteractiveClient:
    def __init__(self, session: ClientSession):
        self.session = session
    
    async def list_tools(self):
        """List all available tools."""
        result = await self.session.list_tools()
        print(f"\n📋 Available Tools ({len(result.tools)}):")
        for tool in result.tools:
            print(f"  • {tool.name}: {tool.description}")
            if tool.inputSchema and 'properties' in tool.inputSchema:
                params = list(tool.inputSchema['properties'].keys())
                print(f"    Parameters: {', '.join(params)}")
    
    async def call_tool(self, name: str, args: dict):
        """Call a tool with given arguments."""
        try:
            result = await self.session.call_tool(name, args)
            print(f"\n🔧 Tool '{name}' result:")
            for content in result.content:
                print(f"  {content.text}")
            if result.isError:
                print("  ⚠️  This result contains an error")
        except Exception as e:
            print(f"❌ Error calling tool '{name}': {e}")
    
    async def list_resources(self):
        """List all available resources."""
        result = await self.session.list_resources()
        print(f"\n📚 Available Resources ({len(result.resources)}):")
        for resource in result.resources:
            print(f"  • {resource.uri}: {resource.name}")
    
    async def read_resource(self, uri: str):
        """Read a resource by URI."""
        try:
            result = await self.session.read_resource(uri)
            print(f"\n📖 Resource '{uri}':")
            for content in result.contents:
                print(f"  {content.text}")
        except Exception as e:
            print(f"❌ Error reading resource '{uri}': {e}")
    
    async def list_prompts(self):
        """List all available prompts."""
        result = await self.session.list_prompts()
        print(f"\n💬 Available Prompts ({len(result.prompts)}):")
        for prompt in result.prompts:
            print(f"  • {prompt.name}: {prompt.description}")
            if prompt.arguments:
                args_info = []
                for arg in prompt.arguments:
                    arg_str = arg.name
                    if arg.required:
                        arg_str += "*"
                    args_info.append(arg_str)
                print(f"    Arguments: {', '.join(args_info)} (* = required)")
    
    async def get_prompt(self, name: str, args: dict):
        """Get a prompt with given arguments."""
        try:
            result = await self.session.get_prompt(name, args)
            print(f"\n💭 Prompt '{name}' result:")
            for message in result.messages:
                print(f"  {message.content.text}")
        except Exception as e:
            print(f"❌ Error getting prompt '{name}': {e}")


async def interactive_menu(client: MCPInteractiveClient):
    """Display interactive menu and handle user input."""
    while True:
        print("\n" + "="*60)
        print("🤖 MCP Interactive Client")
        print("="*60)
        print("1. List Tools")
        print("2. Call Tool")
        print("3. List Resources") 
        print("4. Read Resource")
        print("5. List Prompts")
        print("6. Get Prompt")
        print("7. Quick Demo")
        print("0. Exit")
        print("-"*60)
        
        choice = input("Enter your choice (0-7): ").strip()
        
        if choice == "0":
            print("👋 Goodbye!")
            break
        elif choice == "1":
            await client.list_tools()
        elif choice == "2":
            await handle_call_tool(client)
        elif choice == "3":
            await client.list_resources()
        elif choice == "4":
            await handle_read_resource(client)
        elif choice == "5":
            await client.list_prompts()
        elif choice == "6":
            await handle_get_prompt(client)
        elif choice == "7":
            await quick_demo(client)
        else:
            print("❌ Invalid choice. Please try again.")


async def handle_call_tool(client: MCPInteractiveClient):
    """Handle tool calling with user input."""
    print("\n🔧 Call Tool")
    tool_name = input("Enter tool name (e.g., 'add'): ").strip()
    
    if tool_name == "add":
        try:
            a = int(input("Enter first number (a): "))
            b = int(input("Enter second number (b): "))
            await client.call_tool(tool_name, {"a": a, "b": b})
        except ValueError:
            print("❌ Please enter valid numbers")
    else:
        print("Enter arguments as JSON (e.g., {\"a\": 5, \"b\": 3}):")
        args_str = input("Arguments: ").strip()
        try:
            args = json.loads(args_str) if args_str else {}
            await client.call_tool(tool_name, args)
        except json.JSONDecodeError:
            print("❌ Invalid JSON format")


async def handle_read_resource(client: MCPInteractiveClient):
    """Handle resource reading with user input."""
    print("\n📖 Read Resource")
    print("Examples:")
    print("  - user://alice")
    print("  - user://bob") 
    print("  - user://charlie")
    
    uri = input("Enter resource URI: ").strip()
    if uri:
        await client.read_resource(uri)


async def handle_get_prompt(client: MCPInteractiveClient):
    """Handle prompt getting with user input."""
    print("\n💭 Get Prompt")
    prompt_name = input("Enter prompt name (e.g., 'code_review', 'compose_email'): ").strip()
    
    if prompt_name == "code_review":
        language = input("Enter programming language (e.g., 'Python'): ").strip()
        code_type = input("Enter code type (default: 'function'): ").strip() or "function"
        await client.get_prompt(prompt_name, {"language": language, "code_type": code_type})
    elif prompt_name == "compose_email":
        purpose = input("Enter email purpose: ").strip()
        tone = input("Enter tone (professional/friendly/urgent/apologetic, default: professional): ").strip() or "professional"
        await client.get_prompt(prompt_name, {"purpose": purpose, "tone": tone})
    else:
        print("Enter arguments as JSON:")
        args_str = input("Arguments: ").strip()
        try:
            args = json.loads(args_str) if args_str else {}
            await client.get_prompt(prompt_name, args)
        except json.JSONDecodeError:
            print("❌ Invalid JSON format")


async def quick_demo(client: MCPInteractiveClient):
    """Run a quick demonstration of all features."""
    print("\n🚀 Quick Demo - Testing all features...")
    
    # Test tool
    print("\n1. Testing add tool:")
    await client.call_tool("add", {"a": 10, "b": 20})
    
    # Test resources
    print("\n2. Testing user resources:")
    await client.read_resource("user://alice")
    await client.read_resource("user://unknown")
    
    # Test prompts
    print("\n3. Testing prompts:")
    await client.get_prompt("code_review", {"language": "JavaScript", "code_type": "component"})
    await client.get_prompt("compose_email", {"purpose": "team meeting", "tone": "friendly"})
    
    print("\n✅ Demo completed!")


async def main():
    """Main interactive client."""
    print("🚀 Starting MCP Interactive Client...")
    print("Connecting to server...")
    
    try:
        async with create_server_connection() as session:
            client = MCPInteractiveClient(session)
            await interactive_menu(client)
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        print("\nMake sure the server is running. Try: uv run python main.py")


if __name__ == "__main__":
    asyncio.run(main())
