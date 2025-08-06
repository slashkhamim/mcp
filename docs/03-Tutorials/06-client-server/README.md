# Tutorial: Complete MCP Server & Interactive Client

Learn how to build a complete MCP server with an interactive chatbot-like client that demonstrates the full MCP experience.

## What You'll Build

A complete MCP system that includes:
- **MCP Server**: Task management with tools, resources, and prompts
- **Interactive Client**: Chatbot-like interface for natural interaction
- **Full Integration**: End-to-end demonstration of MCP capabilities

## Prerequisites

- Python 3.10+
- `uv` package manager
- Basic understanding of MCP concepts

## Learning Objectives

By the end of this tutorial, you'll understand:
- How to build a complete MCP server from scratch
- How to create an interactive client with natural language interface
- How to integrate tools, resources, and prompts seamlessly
- How to handle real-world MCP communication patterns

## Project Structure

```
06-client-server/
├── README.md                           # This tutorial guide
├── server.py                           # Complete MCP server implementation
├── client_terminal.py                  # Interactive command-line client
├── client_demo.py                      # Quick demonstration client
├── client_streamlit_local_nlp_v1.py    # Basic Streamlit web UI
├── client_streamlit_local_nlp_v2.py    # Advanced Streamlit chat UI
├── pyproject.toml                      # Project configuration
├── uv.lock                             # Dependency lock file
├── tasks.db                            # SQLite database for tasks
└── libs/                               # Supporting libraries
    ├── task_manager.py                 # Task management logic
    └── storage.py                      # Data persistence
```

## What Makes This Special

This tutorial is **different** from the others because:

✅ **Complete System** - Both server and client in one tutorial  
✅ **Interactive Experience** - Chatbot-like natural language interface  
✅ **Real-world Example** - Task management system you can actually use  
✅ **Full Integration** - Demonstrates all MCP concepts together  
✅ **Production Ready** - Includes error handling, persistence, and testing  

## The Task Management Server

Our MCP server provides a complete task management system:

### 🔧 **Tools Available:**
- `create_task` - Create new tasks with priorities and due dates
- `complete_task` - Mark tasks as completed
- `list_tasks` - List tasks with filtering options
- `update_task` - Modify existing tasks
- `delete_task` - Remove tasks
- `add_note` - Add notes to tasks
- `set_reminder` - Set reminders for tasks

### 📚 **Resources Available:**
- `tasks://all` - All tasks in the system
- `tasks://pending` - Only pending tasks
- `tasks://completed` - Only completed tasks
- `tasks://priority/{level}` - Tasks by priority level
- `tasks://project/{name}` - Tasks by project

### 💬 **Prompts Available:**
- `task_breakdown` - Break down complex tasks into subtasks
- `project_plan` - Generate project plans from descriptions
- `daily_summary` - Create daily task summaries
- `productivity_tips` - Get productivity suggestions

## The Interactive Client

Our client provides a **chatbot-like experience**:

```
🤖 Task Manager Assistant
How can I help you manage your tasks today?

> create a task to finish the project report
✅ Created task: "Finish the project report" (Priority: Medium, Due: Tomorrow)

> show me all my high priority tasks
📋 High Priority Tasks (2):
• Fix critical bug in authentication system (Due: Today)
• Complete quarterly review presentation (Due: Friday)

> help me break down the project report task
💡 Task Breakdown Suggestions:
1. Research and gather data sources
2. Create outline and structure
3. Write introduction and executive summary
4. Develop main content sections
5. Review and edit for clarity
6. Format and finalize document
```

## Client Implementations

This tutorial includes **four different client implementations** to demonstrate various approaches to MCP integration:

### 🖥️ **Terminal Client** (`client_terminal.py`)
- **Interactive command-line interface** with natural language processing
- **Real-time MCP connection** using async/await patterns
- **Best for**: Learning MCP basics, debugging, and automation
- **Features**: Full async support, error handling, connection status

### 🚀 **Demo Client** (`client_demo.py`)
- **Quick demonstration** of core MCP functionality
- **Simple examples** of tools, resources, and prompts
- **Best for**: Understanding MCP concepts quickly
- **Features**: Minimal setup, clear examples, educational focus

### 🌐 **Basic Streamlit App** (`client_streamlit_app1.py`)
- **Simple web interface** with basic MCP integration
- **Form-based interaction** for task management
- **Best for**: Simple web UIs, form-based workflows
- **Features**: Web forms, basic styling, straightforward layout

### 💬 **Advanced Streamlit Chat** (`client_streamlit_app2.py`)
- **ChatGPT-like interface** with full MCP integration
- **Natural language chat** with beautiful UI
- **Best for**: Production-like chat experiences
- **Features**: Chat interface, async MCP connection, modern UI, real-time responses

## Step 1: Setup

Navigate to the tutorial directory:

```bash
cd docs/03-Tutorials/06-client-server
```

The project is already configured with `pyproject.toml` and dependencies.

Install dependencies:
```bash
uv sync
```

## Step 2: Run the System

### Option 1: Advanced Chat Interface (Recommended)

Start the advanced chat interface:
```bash
uv run streamlit run client_streamlit_app2.py
```

### Option 2: Basic Web Interface

Start the basic web interface:
```bash
uv run streamlit run client_streamlit_app1.py
```

### Option 3: Terminal Interface

Start the interactive terminal client:
```bash
uv run python client_terminal.py
```

### Option 4: Quick Demo

Start the demo:
```bash
uv run python client_demo.py
```

## Step 3: Try It Out

The client provides natural language interaction:

- **"Create a task to..."** - Creates new tasks
- **"Show me..."** - Lists and filters tasks  
- **"Complete the..."** - Marks tasks as done
- **"Help me plan..."** - Uses prompts for planning
- **"What tasks are due today?"** - Smart filtering
- **"Break down this task..."** - Task decomposition