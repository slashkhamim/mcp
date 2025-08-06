#!/usr/bin/env python3
"""
Streamlit Chat UI for Task Manager MCP Server

A beautiful web-based chat interface that connects to the MCP server.
Provides a ChatGPT-like experience for task management.
"""

import asyncio
import json
import re
import streamlit as st
from datetime import datetime, date
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Configure Streamlit page
st.set_page_config(
    page_title="Task Manager Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for chat interface
st.markdown("""
<style>
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 2rem;
    }
    .assistant-message {
        background-color: #f5f5f5;
        margin-right: 2rem;
    }
    .message-header {
        font-weight: bold;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .user-header {
        color: #1976d2;
    }
    .assistant-header {
        color: #388e3c;
    }
    .message-content {
        line-height: 1.6;
    }
    .sidebar-stats {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .quick-action {
        margin: 0.25rem;
        padding: 0.5rem 1rem;
        background-color: #e8f4f8;
        border: 1px solid #b3e5fc;
        border-radius: 1rem;
        cursor: pointer;
        display: inline-block;
        font-size: 0.9rem;
    }
    .quick-action:hover {
        background-color: #b3e5fc;
    }
</style>
""", unsafe_allow_html=True)


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


class StreamlitTaskManagerClient:
    """Streamlit-based client for the task management MCP server."""
    
    def __init__(self):
        self.session = None
    
    async def connect(self):
        """Connect to the MCP server."""
        if 'mcp_session' not in st.session_state:
            try:
                server_params = StdioServerParameters(
                    command="uv", 
                    args=["run", "mcp", "run", "server.py"],
                    env=None
                )
                # Note: In a real Streamlit app, you'd need to handle async connections differently
                # This is a simplified version for demonstration
                st.session_state.connection_status = "connected"
            except Exception as e:
                st.session_state.connection_status = f"error: {str(e)}"
    
    async def process_natural_language(self, user_input: str, session: ClientSession) -> str:
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
        
        try:
            # Try to match create task patterns
            for pattern in create_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    task_title = match.group(1).strip()
                    return await self.create_task_from_input(session, user_input, task_title)
            
            # Try to match list task patterns
            for pattern in list_patterns:
                if re.search(pattern, user_input_lower):
                    return await self.list_tasks_from_input(session, user_input)
            
            # Try to match complete task patterns
            for pattern in complete_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    task_title = match.group(1).strip()
                    return await self.complete_task_from_input(session, task_title)
            
            # Special commands
            if any(word in user_input_lower for word in ["help", "what can you do"]):
                return self.get_help_message()
            
            if any(word in user_input_lower for word in ["stats", "statistics", "progress"]):
                return await self.get_task_statistics(session)
            
            # If no patterns match, try to be helpful
            return self.handle_unclear_input(user_input)
            
        except Exception as e:
            return f"❌ Sorry, I encountered an error: {str(e)}\nTry asking for 'help' to see what I can do."
    
    async def create_task_from_input(self, session: ClientSession, full_input: str, task_title: str) -> str:
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
            due_date = "friday"
        
        # Look for project indicators
        project_match = re.search(r"(?:for|in|project)\s+([a-zA-Z0-9\s]+?)(?:\s|$)", full_input.lower())
        if project_match:
            project = project_match.group(1).strip()
        
        # Call the MCP tool
        result = await session.call_tool("create_task", {
            "title": task_title,
            "description": description,
            "priority": priority,
            "due_date": due_date,
            "project": project
        })
        
        response = result.content[0].text
        return f"{response}\n\n💡 You can also ask me to 'show my tasks' to see all your tasks!"
    
    async def list_tasks_from_input(self, session: ClientSession, user_input: str) -> str:
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
        
        # Call the MCP tool
        result = await session.call_tool("list_tasks", {
            "status": status,
            "priority": priority,
            "limit": limit
        })
        
        response = result.content[0].text
        
        if "No tasks found" in response:
            return f"{response}\n\n💡 Try creating a task by saying: 'Create a task to finish my project'"
        else:
            return f"{response}\n\n💡 You can complete a task by saying: 'Complete the [task name]'"
    
    async def complete_task_from_input(self, session: ClientSession, task_title: str) -> str:
        """Complete a task based on natural language input."""
        result = await session.call_tool("complete_task", {
            "title": task_title
        })
        
        response = result.content[0].text
        
        if "Completed task" in response:
            return f"{response}\n\n🎉 Great job! You can see your progress with 'show completed tasks'"
        else:
            return f"{response}\n\n💡 Try being more specific with the task name, or ask me to 'show my tasks' to see available tasks."
    
    async def get_task_statistics(self, session: ClientSession) -> str:
        """Get and format task statistics."""
        try:
            # Get tasks from different resources
            all_tasks_result = await session.read_resource("tasks://all")
            pending_tasks_result = await session.read_resource("tasks://pending")
            completed_tasks_result = await session.read_resource("tasks://completed")
            
            all_data = json.loads(all_tasks_result.contents[0].text)
            pending_data = json.loads(pending_tasks_result.contents[0].text)
            completed_data = json.loads(completed_tasks_result.contents[0].text)
            
            completion_rate = (completed_data['completed_tasks'] / max(all_data['total_tasks'], 1) * 100)
            
            stats = f"""📊 **Your Task Statistics**

**Overview:**
• Total tasks: {all_data['total_tasks']}
• Pending tasks: {pending_data['pending_tasks']}
• Completed tasks: {completed_data['completed_tasks']}

**Progress:**
• Completion rate: {completion_rate:.1f}%
"""
            return stats
            
        except Exception as e:
            return f"❌ Couldn't get statistics: {str(e)}"
    
    def get_help_message(self) -> str:
        """Get help message."""
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

**Getting Info:**
• "Help" - Show this help message
• "Stats" - Show task statistics

**Tips:**
• I understand natural language, so speak normally!
• You can mention priority (urgent, important, low priority)
• You can mention due dates (today, tomorrow, this week)
• You can mention projects (for project X, in the marketing project)

Try saying something like: "Create an urgent task to fix the login bug due today"
"""
    
    def handle_unclear_input(self, user_input: str) -> str:
        """Handle input that doesn't match clear patterns."""
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


def render_chat_message(message, is_user=True):
    """Render a chat message with styling."""
    if is_user:
        st.markdown(f"""
        <div class="chat-message user-message">
            <div class="message-header user-header">
                👤 You
            </div>
            <div class="message-content">
                {message}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <div class="message-header assistant-header">
                🤖 Task Manager Assistant
            </div>
            <div class="message-content">
                {message}
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_quick_actions():
    """Render quick action buttons."""
    st.markdown("### 🚀 Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Show My Tasks", key="show_tasks"):
            return "show my tasks"
        if st.button("📊 Task Statistics", key="stats"):
            return "stats"
    
    with col2:
        if st.button("✅ Create Task", key="create_task"):
            return "create a task"
        if st.button("🎯 High Priority Tasks", key="high_priority"):
            return "show high priority tasks"
    
    with col3:
        if st.button("✨ Completed Tasks", key="completed"):
            return "show completed tasks"
        if st.button("❓ Help", key="help"):
            return "help"
    
    return None


async def process_message_async(client, user_input):
    """Process message asynchronously."""
    try:
        async with create_server_connection() as session:
            response = await client.process_natural_language(user_input, session)
            return response
    except Exception as e:
        return f"❌ Error connecting to server: {str(e)}\n\nMake sure the server is running:\n```bash\nuv run mcp run server.py\n```"


def main():
    """Main Streamlit application."""
    st.title("🤖 Task Manager Assistant")
    st.markdown("Your intelligent task management companion powered by MCP")
    
    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": """👋 Hello! I'm your Task Manager Assistant. I can help you:

• **Create tasks** - "Create a task to finish the project report"
• **View tasks** - "Show me my pending tasks"  
• **Complete tasks** - "Complete the client meeting task"
• **Get statistics** - "Show my task progress"

What would you like to do today?"""
            }
        ]
    
    if 'client' not in st.session_state:
        st.session_state.client = StreamlitTaskManagerClient()
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🎛️ Controls")
        
        # Connection status
        st.markdown("#### 🔌 Connection Status")
        if st.button("🔄 Check Server Connection"):
            try:
                # Test actual connection to MCP server
                test_response = asyncio.run(process_message_async(st.session_state.client, "help"))
                if "Error connecting to server" in test_response:
                    st.error("❌ Server not responding")
                    st.error(test_response)
                else:
                    st.success("✅ Server is running")
            except Exception as e:
                st.error(f"❌ Server not responding: {str(e)}")
        
        st.markdown("---")
        
        # Quick stats (placeholder)
        st.markdown("### 📊 Quick Stats")
        st.markdown("""
        <div class="sidebar-stats">
            <strong>Today's Progress</strong><br>
            📝 Tasks: Loading...<br>
            ✅ Completed: Loading...<br>
            ⏳ Pending: Loading...<br>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Clear chat
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = [st.session_state.messages[0]]  # Keep welcome message
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 💡 Tips")
        st.markdown("""
        • Use natural language
        • Be specific with task names
        • Mention priority and due dates
        • Ask for help anytime!
        """)
    
    # Main chat interface
    chat_container = st.container()
    
    with chat_container:
        # Display chat messages
        for message in st.session_state.messages:
            render_chat_message(
                message["content"], 
                is_user=(message["role"] == "user")
            )
    
    # Quick actions
    quick_action = render_quick_actions()
    if quick_action:
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": quick_action
        })
        
        # Process and add assistant response
        with st.spinner("🤖 Processing..."):
            try:
                # Use the actual async connection to MCP server
                response = asyncio.run(process_message_async(st.session_state.client, quick_action))
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response
                })
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Chat input
    st.markdown("---")
    user_input = st.chat_input("Type your message here... (e.g., 'Create a task to review the budget')")
    
    if user_input:
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Process and add assistant response
        with st.spinner("🤖 Processing your request..."):
            try:
                # Use the actual async connection to MCP server
                response = asyncio.run(process_message_async(st.session_state.client, user_input))
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })
                st.rerun()
            except Exception as e:
                st.error(f"Error processing message: {str(e)}")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        🤖 Task Manager Assistant powered by MCP | 
        <a href="#" style="color: #1976d2;">Documentation</a> | 
        <a href="#" style="color: #1976d2;">GitHub</a>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
