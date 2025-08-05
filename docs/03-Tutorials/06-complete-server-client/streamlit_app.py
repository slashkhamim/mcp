#!/usr/bin/env python3
"""
Streamlit Chat App for Task Manager MCP Server

A production-ready web-based chat interface that properly handles async MCP connections.
Run with: streamlit run streamlit_app.py
"""

import asyncio
import json
import re
import streamlit as st
import threading
import queue
from datetime import datetime
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# Configure Streamlit page
st.set_page_config(
    page_title="🤖 Task Manager Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful chat interface
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    
    .chat-message {
        padding: 1rem 1.5rem;
        border-radius: 1rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 3rem;
        margin-right: 1rem;
    }
    
    .assistant-message {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        margin-left: 1rem;
        margin-right: 3rem;
    }
    
    .message-header {
        font-weight: 600;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        opacity: 0.9;
    }
    
    .message-content {
        line-height: 1.6;
        font-size: 1rem;
    }
    
    .stats-card {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .quick-action-btn {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 2rem;
        margin: 0.25rem;
        cursor: pointer;
        font-weight: 500;
        transition: transform 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .quick-action-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    .connection-status {
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        font-weight: 500;
        margin-bottom: 1rem;
    }
    
    .connected {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    
    .disconnected {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    
    .sidebar .element-container {
        margin-bottom: 1rem;
    }
    
    .welcome-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 1rem;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


class MCPConnectionManager:
    """Manages MCP server connections in a thread-safe way."""
    
    def __init__(self):
        self.connection_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.is_connected = False
        self.connection_thread = None
    
    def start_connection_thread(self):
        """Start the connection thread."""
        if self.connection_thread is None or not self.connection_thread.is_alive():
            self.connection_thread = threading.Thread(target=self._connection_worker, daemon=True)
            self.connection_thread.start()
    
    def _connection_worker(self):
        """Worker thread that handles MCP connections."""
        async def async_worker():
            try:
                server_params = StdioServerParameters(
                    command="uv", 
                    args=["run", "mcp", "run", "server.py"],
                    env=None
                )
                
                async with stdio_client(server_params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        self.is_connected = True
                        
                        while True:
                            try:
                                # Check for new requests
                                request = self.connection_queue.get(timeout=0.1)
                                
                                if request["type"] == "tool_call":
                                    result = await session.call_tool(
                                        request["tool_name"], 
                                        request["arguments"]
                                    )
                                    response = result.content[0].text
                                    self.response_queue.put({
                                        "id": request["id"],
                                        "response": response,
                                        "error": None
                                    })
                                
                                elif request["type"] == "read_resource":
                                    result = await session.read_resource(request["uri"])
                                    response = result.contents[0].text
                                    self.response_queue.put({
                                        "id": request["id"],
                                        "response": response,
                                        "error": None
                                    })
                                
                            except queue.Empty:
                                continue
                            except Exception as e:
                                self.response_queue.put({
                                    "id": request.get("id", "unknown"),
                                    "response": None,
                                    "error": str(e)
                                })
                                
            except Exception as e:
                self.is_connected = False
                self.response_queue.put({
                    "id": "connection_error",
                    "response": None,
                    "error": f"Connection failed: {str(e)}"
                })
        
        # Run the async worker
        try:
            asyncio.run(async_worker())
        except Exception as e:
            self.is_connected = False
    
    def send_request(self, request_type: str, request_id: str, **kwargs):
        """Send a request to the MCP server."""
        request = {
            "type": request_type,
            "id": request_id,
            **kwargs
        }
        self.connection_queue.put(request)
    
    def get_response(self, timeout=5.0):
        """Get a response from the MCP server."""
        try:
            return self.response_queue.get(timeout=timeout)
        except queue.Empty:
            return {
                "id": "timeout",
                "response": None,
                "error": "Request timed out"
            }


def initialize_session_state():
    """Initialize Streamlit session state."""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'mcp_manager' not in st.session_state:
        st.session_state.mcp_manager = MCPConnectionManager()
        st.session_state.mcp_manager.start_connection_thread()
    
    if 'request_counter' not in st.session_state:
        st.session_state.request_counter = 0


def get_next_request_id():
    """Get next request ID."""
    st.session_state.request_counter += 1
    return f"req_{st.session_state.request_counter}"


def process_natural_language_input(user_input: str) -> dict:
    """Process natural language and determine MCP action."""
    user_input_lower = user_input.lower().strip()
    
    # Create task patterns
    create_patterns = [
        r"create.*task.*?['\"]([^'\"]+)['\"]",
        r"add.*task.*?['\"]([^'\"]+)['\"]",
        r"new task.*?['\"]([^'\"]+)['\"]",
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
        r"(?:complete|finish|done).*?(?:task|the)\s+(.+?)(?:\s|$)"
    ]
    
    # Try to match create task patterns
    for pattern in create_patterns:
        match = re.search(pattern, user_input_lower)
        if match:
            task_title = match.group(1).strip()
            
            # Extract additional details
            priority = "medium"
            due_date = ""
            project = ""
            
            if any(word in user_input_lower for word in ["urgent", "critical", "important", "asap"]):
                priority = "high"
            elif any(word in user_input_lower for word in ["low", "minor", "later"]):
                priority = "low"
            
            if "today" in user_input_lower:
                due_date = "today"
            elif "tomorrow" in user_input_lower:
                due_date = "tomorrow"
            
            project_match = re.search(r"(?:for|in|project)\s+([a-zA-Z0-9\s]+?)(?:\s|$)", user_input_lower)
            if project_match:
                project = project_match.group(1).strip()
            
            return {
                "action": "create_task",
                "tool_name": "create_task",
                "arguments": {
                    "title": task_title,
                    "priority": priority,
                    "due_date": due_date,
                    "project": project
                }
            }
    
    # Try to match list task patterns
    for pattern in list_patterns:
        if re.search(pattern, user_input_lower):
            status = "all"
            priority = "all"
            
            if any(word in user_input_lower for word in ["pending", "todo", "unfinished"]):
                status = "pending"
            elif any(word in user_input_lower for word in ["completed", "done", "finished"]):
                status = "completed"
            
            if "high priority" in user_input_lower or "urgent" in user_input_lower:
                priority = "high"
            elif "low priority" in user_input_lower:
                priority = "low"
            
            return {
                "action": "list_tasks",
                "tool_name": "list_tasks",
                "arguments": {
                    "status": status,
                    "priority": priority,
                    "limit": 10
                }
            }
    
    # Try to match complete task patterns
    for pattern in complete_patterns:
        match = re.search(pattern, user_input_lower)
        if match:
            task_title = match.group(1).strip()
            return {
                "action": "complete_task",
                "tool_name": "complete_task",
                "arguments": {
                    "title": task_title
                }
            }
    
    # Special commands
    if any(word in user_input_lower for word in ["stats", "statistics", "progress"]):
        return {
            "action": "get_stats",
            "resource_uri": "tasks://all"
        }
    
    # Default help response
    return {
        "action": "help",
        "response": """🤖 **I can help you with:**

**Creating Tasks:**
• "Create a task to finish the project report"
• "Add an urgent task to fix the bug"
• "I need to prepare for the meeting tomorrow"

**Viewing Tasks:**
• "Show my tasks"
• "List pending tasks"
• "What tasks are due today?"

**Completing Tasks:**
• "Complete the project report"
• "Mark the meeting as done"

**Getting Info:**
• "Show my statistics"
• "Help"

Try being specific with task names and mentioning priority or due dates!"""
    }


def render_chat_message(message: dict):
    """Render a chat message with beautiful styling."""
    is_user = message["role"] == "user"
    
    if is_user:
        st.markdown(f"""
        <div class="chat-message user-message">
            <div class="message-header">
                👤 You
            </div>
            <div class="message-content">
                {message["content"]}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <div class="message-header">
                🤖 Task Manager Assistant
            </div>
            <div class="message-content">
                {message["content"]}
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_sidebar():
    """Render the sidebar with controls and stats."""
    with st.sidebar:
        st.markdown("### 🎛️ Control Panel")
        
        # Connection status
        manager = st.session_state.mcp_manager
        if manager.is_connected:
            st.markdown("""
            <div class="connection-status connected">
                ✅ Connected to MCP Server
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="connection-status disconnected">
                ❌ Disconnected from MCP Server
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🔄 Reconnect"):
                st.session_state.mcp_manager = MCPConnectionManager()
                st.session_state.mcp_manager.start_connection_thread()
                st.rerun()
        
        st.markdown("---")
        
        # Quick stats
        st.markdown("### 📊 Quick Stats")
        if manager.is_connected:
            if st.button("📈 Refresh Stats"):
                request_id = get_next_request_id()
                manager.send_request("read_resource", request_id, uri="tasks://all")
                
                response = manager.get_response(timeout=3.0)
                if response["error"]:
                    st.error(f"Error: {response['error']}")
                else:
                    try:
                        data = json.loads(response["response"])
                        st.markdown(f"""
                        <div class="stats-card">
                            <strong>📝 Total Tasks:</strong> {data.get('total_tasks', 0)}<br>
                            <strong>⏳ Active:</strong> Loading...<br>
                            <strong>✅ Completed:</strong> Loading...
                        </div>
                        """, unsafe_allow_html=True)
                    except:
                        st.error("Could not parse stats")
        else:
            st.markdown("""
            <div class="stats-card">
                <strong>📝 Total Tasks:</strong> --<br>
                <strong>⏳ Active:</strong> --<br>
                <strong>✅ Completed:</strong> --
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Quick actions
        st.markdown("### 🚀 Quick Actions")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝 My Tasks", key="sidebar_tasks"):
                return "show my tasks"
            if st.button("✅ Create Task", key="sidebar_create"):
                return "create a task"
        
        with col2:
            if st.button("📊 Statistics", key="sidebar_stats"):
                return "show statistics"
            if st.button("❓ Help", key="sidebar_help"):
                return "help"
        
        st.markdown("---")
        
        # Clear chat
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 💡 Tips")
        st.markdown("""
        • Use natural language
        • Be specific with task names  
        • Mention priority (urgent, low)
        • Include due dates (today, tomorrow)
        • Try: "Create urgent task to fix login bug due today"
        """)
    
    return None


def main():
    """Main Streamlit application."""
    initialize_session_state()
    
    # Header
    st.markdown("""
    <div class="welcome-message">
        <h1>🤖 Task Manager Assistant</h1>
        <p>Your intelligent task management companion powered by MCP</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    sidebar_action = render_sidebar()
    
    # Main chat area
    chat_container = st.container()
    
    with chat_container:
        # Display welcome message if no messages
        if not st.session_state.messages:
            st.markdown("""
            <div style="text-align: center; padding: 2rem; color: #666;">
                <h3>👋 Welcome! How can I help you manage your tasks today?</h3>
                <p>Try saying: "Create a task to review the quarterly report"</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Display chat messages
        for message in st.session_state.messages:
            render_chat_message(message)
    
    # Handle sidebar actions
    if sidebar_action:
        process_user_input(sidebar_action)
    
    # Chat input
    user_input = st.chat_input("💬 Type your message here... (e.g., 'Create a task to review the budget')")
    
    if user_input:
        process_user_input(user_input)


def process_user_input(user_input: str):
    """Process user input and generate response."""
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    
    # Process the input
    with st.spinner("🤖 Processing your request..."):
        action_info = process_natural_language_input(user_input)
        
        if action_info["action"] == "help":
            response = action_info["response"]
        elif not st.session_state.mcp_manager.is_connected:
            response = """❌ **Not connected to MCP server**

To start the server:
1. Open a terminal
2. Navigate to this directory
3. Run: `uv run mcp run server.py`
4. Then refresh this page

The server needs to be running for me to manage your tasks!"""
        else:
            # Send request to MCP server
            request_id = get_next_request_id()
            
            if "tool_name" in action_info:
                st.session_state.mcp_manager.send_request(
                    "tool_call",
                    request_id,
                    tool_name=action_info["tool_name"],
                    arguments=action_info["arguments"]
                )
            elif "resource_uri" in action_info:
                st.session_state.mcp_manager.send_request(
                    "read_resource",
                    request_id,
                    uri=action_info["resource_uri"]
                )
            
            # Get response
            mcp_response = st.session_state.mcp_manager.get_response(timeout=5.0)
            
            if mcp_response["error"]:
                response = f"❌ Error: {mcp_response['error']}"
            else:
                response = mcp_response["response"]
                
                # Add helpful suggestions
                if action_info["action"] == "create_task" and "Created task" in response:
                    response += "\n\n💡 You can view all your tasks by saying 'show my tasks'"
                elif action_info["action"] == "list_tasks" and "No tasks found" in response:
                    response += "\n\n💡 Try creating your first task: 'Create a task to get started'"
    
    # Add assistant response
    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })
    
    st.rerun()


if __name__ == "__main__":
    main()
