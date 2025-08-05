#!/usr/bin/env python3
"""
MCP Client example to connect with main.py server.

This client demonstrates how to:
1. Connect to the MCP server
2. List available tools, resources, and prompts
3. Call tools with parameters
4. Read resources
5. Get prompts with arguments
"""

import asyncio
import subprocess
import sys
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@asynccontextmanager
async def create_server_connection():
    """Create a connection to the MCP server."""
    # The MCP server needs to be run with specific arguments for stdio mode
    server_params = StdioServerParameters(
        command="uv", 
        args=["run", "mcp", "run", "main.py"],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            yield session


async def demonstrate_tools(session: ClientSession):
    """Demonstrate tool functionality."""
    print("🔧 TOOLS DEMONSTRATION")
    print("=" * 50)
    
    # List available tools
    tools_result = await session.list_tools()
    print(f"Available tools: {len(tools_result.tools)}")
    for tool in tools_result.tools:
        print(f"  - {tool.name}: {tool.description}")
    
    print()
    
    # Call the add tool
    print("Calling add tool with a=15, b=25:")
    add_result = await session.call_tool("add", {"a": 15, "b": 25})
    print(f"Result: {add_result.content[0].text}")
    print(f"Is error: {add_result.isError}")
    
    print()


async def demonstrate_resources(session: ClientSession):
    """Demonstrate resource functionality."""
    print("📚 RESOURCES DEMONSTRATION")
    print("=" * 50)
    
    # List available resources
    resources_result = await session.list_resources()
    print(f"Available resources: {len(resources_result.resources)}")
    for resource in resources_result.resources:
        print(f"  - {resource.uri}: {resource.name}")
    
    print()
    
    # Read user profiles
    users_to_test = ["alice", "bob", "charlie", "unknown"]
    
    for user_id in users_to_test:
        print(f"Reading user profile for '{user_id}':")
        try:
            resource_result = await session.read_resource(f"user://{user_id}")
            for content in resource_result.contents:
                print(f"  {content.text}")
        except Exception as e:
            print(f"  Error: {e}")
        print()


async def demonstrate_prompts(session: ClientSession):
    """Demonstrate prompt functionality."""
    print("💬 PROMPTS DEMONSTRATION")
    print("=" * 50)
    
    # List available prompts
    prompts_result = await session.list_prompts()
    print(f"Available prompts: {len(prompts_result.prompts)}")
    for prompt in prompts_result.prompts:
        print(f"  - {prompt.name}: {prompt.description}")
        if prompt.arguments:
            args_info = ", ".join([f"{arg.name}{'*' if arg.required else ''}" for arg in prompt.arguments])
            print(f"    Arguments: {args_info} (* = required)")
    
    print()
    
    # Test code review prompt
    print("Getting code review prompt for Python class:")
    code_review_result = await session.get_prompt(
        "code_review", 
        {"language": "Python", "code_type": "class"}
    )
    for message in code_review_result.messages:
        print(f"  {message.content.text}")
    
    print()
    
    # Test email composition prompt
    print("Getting email composition prompt:")
    email_result = await session.get_prompt(
        "compose_email", 
        {"purpose": "project status update", "tone": "friendly"}
    )
    for message in email_result.messages:
        print(f"  {message.content.text}")
    
    print()


async def main():
    """Main client demonstration."""
    print("🚀 MCP CLIENT DEMONSTRATION")
    print("Connecting to MCP server...")
    print()
    
    try:
        async with create_server_connection() as session:
            # Demonstrate each component
            await demonstrate_tools(session)
            await demonstrate_resources(session)
            await demonstrate_prompts(session)
            
            print("✅ All demonstrations completed successfully!")
            
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        print("\nMake sure the server is properly configured and dependencies are installed.")
        print("Try running: uv run python main.py")
        sys.exit(1)


if __name__ == "__main__":
    # Run the client demonstration
    asyncio.run(main())
