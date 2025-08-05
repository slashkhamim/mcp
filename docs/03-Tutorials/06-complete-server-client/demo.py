#!/usr/bin/env python3
"""
Quick Demo Script

Demonstrates the task management MCP server capabilities with automated examples.
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
        args=["run", "mcp", "run", "server.py"],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def demo_tools(session: ClientSession):
    """Demonstrate all the tools."""
    print("🔧 **TOOLS DEMONSTRATION**")
    print("="*50)
    
    # Create some sample tasks
    print("\n1. Creating sample tasks...")
    
    tasks_to_create = [
        {
            "title": "Complete project proposal",
            "description": "Write and review the Q1 project proposal",
            "priority": "high",
            "due_date": "today",
            "project": "Q1 Planning"
        },
        {
            "title": "Team meeting preparation",
            "description": "Prepare agenda and materials for weekly team meeting",
            "priority": "medium",
            "due_date": "tomorrow",
            "project": "Team Management"
        },
        {
            "title": "Code review for authentication",
            "description": "Review pull request for new authentication system",
            "priority": "high",
            "due_date": "",
            "project": "Security"
        },
        {
            "title": "Update documentation",
            "description": "Update API documentation with new endpoints",
            "priority": "low",
            "due_date": "",
            "project": "Documentation"
        }
    ]
    
    created_tasks = []
    for task_data in tasks_to_create:
        result = await session.call_tool("create_task", task_data)
        print(f"   {result.content[0].text}")
        # Extract task ID from response if needed
        created_tasks.append(task_data["title"])
    
    # List tasks
    print("\n2. Listing all tasks...")
    result = await session.call_tool("list_tasks", {"limit": 10})
    print(f"   {result.content[0].text}")
    
    # List high priority tasks
    print("\n3. Listing high priority tasks...")
    result = await session.call_tool("list_tasks", {"priority": "high"})
    print(f"   {result.content[0].text}")
    
    # Complete a task
    print("\n4. Completing a task...")
    result = await session.call_tool("complete_task", {"title": "Code review"})
    print(f"   {result.content[0].text}")
    
    # Add a note to a task
    print("\n5. Adding a note to a task...")
    result = await session.call_tool("add_note", {
        "task_id": 1,
        "note": "Discussed with stakeholders, deadline confirmed"
    })
    print(f"   {result.content[0].text}")
    
    # Get task details
    print("\n6. Getting detailed task information...")
    result = await session.call_tool("get_task_details", {"task_id": 1})
    print(f"   {result.content[0].text}")


async def demo_resources(session: ClientSession):
    """Demonstrate all the resources."""
    print("\n\n📚 **RESOURCES DEMONSTRATION**")
    print("="*50)
    
    # Get all tasks
    print("\n1. Getting all tasks resource...")
    result = await session.read_resource("tasks://all")
    data = json.loads(result.contents[0].text)
    print(f"   Total tasks in system: {data['total_tasks']}")
    
    # Get pending tasks
    print("\n2. Getting pending tasks resource...")
    result = await session.read_resource("tasks://pending")
    data = json.loads(result.contents[0].text)
    print(f"   Pending tasks: {data['pending_tasks']}")
    
    # Get completed tasks
    print("\n3. Getting completed tasks resource...")
    result = await session.read_resource("tasks://completed")
    data = json.loads(result.contents[0].text)
    print(f"   Completed tasks: {data['completed_tasks']}")
    
    # Get high priority tasks
    print("\n4. Getting high priority tasks resource...")
    result = await session.read_resource("tasks://priority/high")
    data = json.loads(result.contents[0].text)
    print(f"   High priority tasks: {data['task_count']}")
    
    # Get project tasks
    print("\n5. Getting project-specific tasks...")
    result = await session.read_resource("tasks://project/Q1%20Planning")
    data = json.loads(result.contents[0].text)
    print(f"   Tasks in 'Q1 Planning' project: {data['task_count']}")


async def demo_prompts(session: ClientSession):
    """Demonstrate all the prompts."""
    print("\n\n💬 **PROMPTS DEMONSTRATION**")
    print("="*50)
    
    # Task breakdown prompt
    print("\n1. Task breakdown prompt...")
    result = await session.get_prompt("task_breakdown", {
        "task_description": "Launch new mobile app",
        "complexity": "complex"
    })
    print("   Generated task breakdown:")
    print(f"   {result.messages[0].content.text[:200]}...")
    
    # Project plan prompt
    print("\n2. Project plan prompt...")
    result = await session.get_prompt("project_plan", {
        "project_description": "Implement user authentication system",
        "timeline": "2 months",
        "team_size": "3"
    })
    print("   Generated project plan:")
    print(f"   {result.messages[0].content.text[:200]}...")
    
    # Daily summary prompt
    print("\n3. Daily summary prompt...")
    result = await session.get_prompt("daily_summary", {
        "date": "today"
    })
    print("   Generated daily summary:")
    print(f"   {result.messages[0].content.text[:200]}...")
    
    # Productivity tips prompt
    print("\n4. Productivity tips prompt...")
    result = await session.get_prompt("productivity_tips", {
        "current_tasks": "Multiple high-priority development tasks",
        "work_style": "focused"
    })
    print("   Generated productivity tips:")
    print(f"   {result.messages[0].content.text[:200]}...")


async def main():
    """Run the complete demonstration."""
    print("🚀 **TASK MANAGER MCP SERVER DEMO**")
    print("="*60)
    print("This demo shows all the capabilities of our task management MCP server.")
    print("It demonstrates tools, resources, and prompts working together.")
    print("\nConnecting to server...")
    
    try:
        async with create_server_connection() as session:
            print("✅ Connected successfully!\n")
            
            # Run all demonstrations
            await demo_tools(session)
            await demo_resources(session)
            await demo_prompts(session)
            
            print("\n\n🎉 **DEMO COMPLETED SUCCESSFULLY!**")
            print("="*60)
            print("The task management MCP server is fully functional with:")
            print("• ✅ 8 Tools for task management")
            print("• ✅ 5 Resources for data access")
            print("• ✅ 4 Prompts for AI assistance")
            print("• ✅ SQLite database for persistence")
            print("• ✅ Natural language client interface")
            print("\nTry running the interactive client:")
            print("   uv run python client.py")
            
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        print("\nMake sure to start the server first:")
        print("   uv run mcp run server.py")


if __name__ == "__main__":
    asyncio.run(main())
