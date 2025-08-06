# Tutorial: MCP Server with LLM-Integrated Client

Learn how to build a complete MCP server with an LLM-powered Streamlit client that demonstrates advanced MCP integration with OpenAI.

## What You'll Build

A complete MCP system that includes:
- **MCP Server**: Task management with tools, resources, and prompts (SSE transport)
- **LLM-Integrated Client**: Streamlit chat interface powered by OpenAI GPT models
- **Full Integration**: End-to-end demonstration of MCP + LLM capabilities

## Prerequisites

- Python 3.10+
- `uv` package manager
- OpenAI API key (for LLM integration)
- Basic understanding of MCP concepts

## Learning Objectives

By the end of this tutorial, you'll understand:
- How to build a complete MCP server with SSE transport
- How to integrate MCP with OpenAI LLM models
- How to create a Streamlit chat interface that uses MCP tools
- How to handle environment variables and API keys securely
- How to seamlessly combine MCP tools, resources, and prompts with LLM reasoning

## Project Structure

```
07-client-server-llm/
├── README.md                    # This tutorial guide
├── storage_mcp_server.py        # MCP server with SSE transport
├── start_client.py              # Streamlit chat client with LLM integration
├── .env.example                 # Environment variables template
├── pyproject.toml              # Project configuration
├── uv.lock                     # Dependency lock file
├── tasks.db                    # SQLite database for tasks
└── libs/                       # Supporting libraries
    ├── client.py               # MCP client with OpenAI integration
    ├── task_manager.py         # Task management logic
    └── storage.py              # Data persistence
```

## What Makes This Special

This tutorial is **different** from the others because:

✅ **LLM Integration** - OpenAI GPT models reason with MCP tools automatically  
✅ **SSE Transport** - HTTP-based server communication (not stdio)  
✅ **Modern UI** - Beautiful Streamlit chat interface with streaming responses  
✅ **Real-world Example** - Task management system you can actually use  
✅ **Full Integration** - Demonstrates MCP + LLM working together seamlessly  
✅ **Production Ready** - Environment variables, error handling, and persistence  

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

## The LLM-Integrated Client

This tutorial features a **revolutionary approach** to MCP integration:

### 🤖 **LLM-Powered Chat Interface** (`start_client.py`)
- **OpenAI GPT Integration** - Uses GPT models to reason about when and how to use MCP tools
- **Intelligent Tool Selection** - The LLM automatically chooses the right MCP tools based on user requests
- **Streamlit Chat UI** - Beautiful, modern chat interface with streaming responses
- **SSE Transport** - Connects to MCP server via HTTP/SSE (not stdio)
- **Environment Variables** - Secure handling of API keys and configuration

### 🔧 **How It Works**
1. **User Input** - You type a natural language request in the chat
2. **LLM Reasoning** - OpenAI GPT analyzes your request and available MCP tools
3. **Tool Execution** - The LLM automatically calls the appropriate MCP tools
4. **Response Generation** - The LLM synthesizes tool results into a natural response
5. **Streaming UI** - Results are displayed with a typing animation

### 🎆 **Example Interactions**
- "Create a high priority task to finish the quarterly report by Friday"
- "Show me all my overdue tasks"
- "Help me break down the website redesign project into smaller tasks"
- "What's my productivity looking like this week?"

The LLM understands context and automatically uses the right combination of MCP tools, resources, and prompts!

## Step 1: Setup

Navigate to the tutorial directory:

```bash
cd docs/03-Tutorials/07-client-server-llm
```

The project is already configured with `pyproject.toml` and dependencies.

### Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```bash
JIRA_MCP_SERVER_URL=http://localhost:9999/sse
OPEN_AI_MODEL=gpt-4o-mini
OPENAI_API_KEY=your_openai_api_key_here
```

### Install Dependencies
```bash
uv sync
```

## Step 2: Run the System

### Start the MCP Server

In your first terminal, start the MCP server with SSE transport:
```bash
uv run python storage_mcp_server.py
```

You should see:
```
🚀 Starting MCP server with SSE transport...
📡 Server will be available at: http://localhost:9999
📡 Your MCP endpoint: http://localhost:9999/sse
```

### Start the LLM-Integrated Client

In a second terminal, start the Streamlit chat interface:
```bash
uv run streamlit run start_client.py
```

You should see:
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8502
```

### Open and Use the Chat Interface

1. **Open your browser** to `http://localhost:8502`
2. **Start chatting!** Try these example requests:
   - "Create a high priority task to review the budget"
   - "Show me all my pending tasks"
   - "Help me break down the project planning task"
   - "What's my task completion rate this week?"

## Step 3: Try It Out

The client provides natural language interaction:

- **"Create a task to..."** - Creates new tasks
- **"Show me..."** - Lists and filters tasks  
- **"Complete the..."** - Marks tasks as done
- **"Help me plan..."** - Uses prompts for planning
- **"What tasks are due today?"** - Smart filtering
- **"Break down this task..."** - Task decomposition

## 🚀 Deployment to Streamlit Cloud

### Prerequisites for Cloud Deployment
- GitHub repository with your code
- OpenAI API key
- Note: The MCP server component cannot run on Streamlit Cloud (it only supports the Streamlit app)

### Step 1: Prepare Your Repository

1. **Push your code to GitHub** (make sure `.env` is in `.gitignore`)
2. **The code is already configured** to work with both local `.env` files and Streamlit Cloud secrets

### Step 2: Deploy to Streamlit Cloud

1. **Go to** [share.streamlit.io](https://share.streamlit.io)
2. **Sign in** with your GitHub account
3. **Click "New app"**
4. **Select your repository** and branch
5. **Set main file path**: `docs/03-Tutorials/07-client-server-llm/start_client.py`
6. **Click "Deploy"**

### Step 3: Configure Secrets

1. **In your Streamlit Cloud dashboard**, go to your app settings
2. **Click the "Secrets" tab**
3. **Add your secrets** in TOML format:

```toml
JIRA_MCP_SERVER_URL = "https://your-mcp-server-url.com/sse"
OPEN_AI_MODEL = "gpt-4o-mini"
OPENAI_API_KEY = "sk-your-actual-openai-api-key-here"
```