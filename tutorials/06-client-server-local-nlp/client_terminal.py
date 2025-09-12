#!/usr/bin/env python3
"""
Interactive Task Manager Client

A chatbot-like client that provides natural language interaction with the MCP server.
Demonstrates how to create an engaging user experience with MCP.
"""

import asyncio
import json
import re
from contextlib import asynccontextmanager
from datetime import datetime, date
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


class TaskManagerClient:
    """Interactive client for the task management MCP server."""
    
    def __init__(self, session: ClientSession):
        self.session = session
        self.conversation_context = []
    
    async def process_natural_language(self, user_input: str) -> str:
        """Process natural language input and execute appropriate MCP calls."""
        user_input_lower = user_input.lower().strip()
        
        # Create task patterns
        create_patterns = [
            r"create.*task.*?['\"]([^'\"]+)['\"]",
            r"add.*task.*?['\"]([^'\"]+)['\"]",
            r"new task.*?['\"]([^'\"]+)['\"]",
            r"create.*['\"]([^'\"]+)['\"].*task",
            r"(?:create|add|new).*task.*?(?:to|for|about)\s+(.+?)(?:\s+(?:due|by|priority)|$)",
            r"i need to (.+?)(?:\s+(?:due|by|priority)|$)"
        ]
        
        # List task patterns
        list_patterns = [
            r"(?:show|list|display|get).*(?:task|todo)",
            r"what.*(?:task|todo|due)",
            r"(?:my|all).*(?:task|todo)",
            r"tasks?.*(?:due|pending|completed)"
        ]
        
        # Complete task patterns
        complete_patterns = [
            r"(?:complete|finish|done).*?['\"]([^'\"]+)['\"]",
            r"mark.*?['\"]([^'\"]+)['\"].*(?:complete|done)",
            r"finished.*?['\"]([^'\"]+)['\"]",
            r"(?:complete|finish|done).*?(?:task|the)\s+(.+?)(?:\s|$)"
        ]
        
        # Help patterns
        help_patterns = [
            r"help", r"what can you do", r"commands", r"how to", r"usage"
        ]
        
        try:
            # Try to match create task patterns
            for pattern in create_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    task_title = match.group(1).strip()
                    return await self.create_task_from_input(user_input, task_title)
            
            # Try to match list task patterns
            for pattern in list_patterns:
                if re.search(pattern, user_input_lower):
                    return await self.list_tasks_from_input(user_input)
            
            # Try to match complete task patterns
            for pattern in complete_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    task_title = match.group(1).strip()
                    return await self.complete_task_from_input(task_title)
            
            # Try to match help patterns
            for pattern in help_patterns:
                if re.search(pattern, user_input_lower):
                    return await self.show_help()
            
            # If no patterns match, try to be helpful
            return await self.handle_unclear_input(user_input)
            
        except Exception as e:
            return f"❌ Sorry, I encountered an error: {str(e)}\nTry asking for 'help' to see what I can do."
    
    async def create_task_from_input(self, full_input: str, task_title: str) -> str:
        """Create a task from natural language input."""
        # Extract additional details from input
        priority = "medium"
        due_date = ""
        description = ""
        project = ""
        
        # Look for priority indicators
        if any(word in full_input.lower() for word in ["urgent", "critical", "important", "asap"]):
            priority = "high"
        elif any(word in full_input.lower() for word in ["low", "minor", "later", "someday"]):
            priority = "low"
        
        # Look for due date indicators
        if "today" in full_input.lower():
            due_date = "today"
        elif "tomorrow" in full_input.lower():
            due_date = "tomorrow"
        elif "this week" in full_input.lower():
            # Set to Friday of current week
            due_date = "friday"
        
        # Look for project indicators
        project_match = re.search(r"(?:for|in|project)\s+([a-zA-Z0-9\s]+?)(?:\s|$)", full_input.lower())
        if project_match:
            project = project_match.group(1).strip()
        
        # Call the MCP tool
        result = await self.session.call_tool("create_task", {
            "title": task_title,
            "description": description,
            "priority": priority,
            "due_date": due_date,
            "project": project
        })
        
        response = result.content[0].text
        
        # Add conversational context
        self.conversation_context.append(f"Created task: {task_title}")
        
        return f"{response}\n\n💡 You can also say 'show my tasks' to see all your tasks!"
    
    async def list_tasks_from_input(self, user_input: str) -> str:
        """List tasks based on natural language input."""
        status = "all"
        priority = "all"
        limit = 10
        
        # Determine what kind of tasks to show
        if any(word in user_input.lower() for word in ["pending", "todo", "unfinished", "incomplete"]):
            status = "pending"
        elif any(word in user_input.lower() for word in ["completed", "done", "finished"]):
            status = "completed"
        
        if "high priority" in user_input.lower() or "urgent" in user_input.lower():
            priority = "high"
        elif "low priority" in user_input.lower():
            priority = "low"
        
        if "due today" in user_input.lower() or "today" in user_input.lower():
            # We'll filter this after getting the results
            pass
        
        # Call the MCP tool
        result = await self.session.call_tool("list_tasks", {
            "status": status,
            "priority": priority,
            "limit": limit
        })
        
        response = result.content[0].text
        
        # Add helpful suggestions
        if "No tasks found" in response:
            return f"{response}\n\n💡 Try creating a task by saying: 'Create a task to finish my project'"
        else:
            return f"{response}\n\n💡 You can complete a task by saying: 'Complete the [task name]'"
    
    async def complete_task_from_input(self, task_title: str) -> str:
        """Complete a task based on natural language input."""
        # Call the MCP tool
        result = await self.session.call_tool("complete_task", {
            "title": task_title
        })
        
        response = result.content[0].text
        
        # Add conversational context
        if "Completed task" in response:
            self.conversation_context.append(f"Completed task: {task_title}")
            return f"{response}\n\n🎉 Great job! You can see your progress with 'show completed tasks'"
        else:
            return f"{response}\n\n💡 Try being more specific with the task name, or use 'show my tasks' to see available tasks."
    
    async def show_help(self) -> str:
        """Show help information."""
        return """🤖 **Task Manager Assistant Help**

I can help you manage your tasks using natural language! Here's what you can say:

**Creating Tasks:**
• "Create a task to finish the project report"
• "Add a task to call the client"
• "I need to prepare for the meeting"
• "New task: review the budget"

**Viewing Tasks:**
• "Show my tasks"
• "What tasks are due today?"
• "List all pending tasks"
• "Show completed tasks"
• "Display high priority tasks"

**Completing Tasks:**
• "Complete the project report"
• "Mark the client call as done"
• "Finished preparing for meeting"

**Getting Help:**
• "Help" - Show this help message
• "What can you do?" - Show capabilities

**Tips:**
• I understand natural language, so speak normally!
• You can mention priority (urgent, important, low priority)
• You can mention due dates (today, tomorrow, this week)
• You can mention projects (for project X, in the marketing project)

Try saying something like: "Create an urgent task to fix the login bug due today"
"""
    
    async def handle_unclear_input(self, user_input: str) -> str:
        """Handle input that doesn't match clear patterns."""
        # Try to be helpful based on keywords
        if any(word in user_input.lower() for word in ["task", "todo", "do", "need"]):
            return f"""🤔 I'm not sure exactly what you want to do with: "{user_input}"

Here are some examples of what you can say:
• "Create a task to {user_input.lower()}"
• "Show me tasks about {user_input.lower()}"
• "Complete the {user_input.lower()} task"

Or just say 'help' to see all my capabilities!"""
        
        return f"""🤔 I'm not sure how to help with: "{user_input}"

I'm a task management assistant. I can help you:
• Create tasks
• List and view tasks  
• Complete tasks
• Organize your work

Try saying 'help' to see examples, or ask me to "create a task" or "show my tasks"!"""
    
    async def get_task_statistics(self) -> str:
        """Get and format task statistics."""
        try:
            # Get tasks from different resources
            all_tasks_result = await self.session.read_resource("tasks://all")
            pending_tasks_result = await self.session.read_resource("tasks://pending")
            completed_tasks_result = await self.session.read_resource("tasks://completed")
            
            all_data = json.loads(all_tasks_result.contents[0].text)
            pending_data = json.loads(pending_tasks_result.contents[0].text)
            completed_data = json.loads(completed_tasks_result.contents[0].text)
            
            stats = f"""📊 **Your Task Statistics**

**Overview:**
• Total tasks: {all_data['total_tasks']}
• Pending tasks: {pending_data['pending_tasks']}
• Completed tasks: {completed_data['completed_tasks']}

**Progress:**
• Completion rate: {(completed_data['completed_tasks'] / max(all_data['total_tasks'], 1) * 100):.1f}%
"""
            
            return stats
            
        except Exception as e:
            return f"❌ Couldn't get statistics: {str(e)}"


async def main():
    """Main interactive client loop."""
    print("🚀 Starting Task Manager Assistant...")
    print("Connecting to server...")
    
    try:
        async with create_server_connection() as session:
            client = TaskManagerClient(session)
            
            # Welcome message
            print("\n" + "="*60)
            print("🤖 **Task Manager Assistant**")
            print("="*60)
            print("Hello! I'm your personal task management assistant.")
            print("I understand natural language, so just tell me what you need!")
            print("\nExamples:")
            print("• 'Create a task to finish the project report'")
            print("• 'Show me my pending tasks'")
            print("• 'Complete the client meeting task'")
            print("\nType 'help' for more examples, or 'quit' to exit.")
            print("-"*60)
            
            # Show initial statistics
            stats = await client.get_task_statistics()
            print(f"\n{stats}")
            
            # Main interaction loop
            while True:
                try:
                    print("\n💬 What would you like to do?")
                    user_input = input("> ").strip()
                    
                    if not user_input:
                        continue
                    
                    if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                        print("\n👋 Goodbye! Have a productive day!")
                        break
                    
                    if user_input.lower() in ['stats', 'statistics', 'progress']:
                        response = await client.get_task_statistics()
                    else:
                        response = await client.process_natural_language(user_input)
                    
                    print(f"\n{response}")
                    
                except KeyboardInterrupt:
                    print("\n\n👋 Goodbye! Have a productive day!")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {str(e)}")
                    print("Please try again or type 'help' for assistance.")
    
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        print("\nMake sure the server is running:")
        print("1. Open another terminal")
        print("2. Navigate to this directory")
        print("3. Run: uv run mcp run server.py")
        print("4. Then run this client again")


if __name__ == "__main__":
    asyncio.run(main())
