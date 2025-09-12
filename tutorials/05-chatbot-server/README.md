# Tutorial: Building a Chatbot MCP Server

Learn how to create an MCP server that provides AI chatbot capabilities and conversation management.

## What You'll Build

A chatbot MCP server that provides:
- **Tools**: Send messages, manage conversations, configure AI models
- **Resources**: Access conversation history and chatbot configurations
- **Prompts**: Generate chatbot personalities and conversation starters

## Prerequisites

- Python 3.10+
- `uv` package manager
- OpenAI API key (or other LLM provider)
- Basic understanding of AI/LLM concepts

## Learning Objectives

By the end of this tutorial, you'll understand:
- How to integrate LLM APIs through MCP
- Conversation state management and persistence
- Prompt engineering and personality configuration
- Token usage tracking and cost management

## Project Structure

```
chatbot-server/
├── server.py          # Main MCP server
├── chatbot.py          # Chatbot logic and AI integration
├── conversation.py     # Conversation management
├── personality.py      # Chatbot personality system
├── test_server.py      # Tests
└── client.py           # Example client
```

## Step 1: Setup

Create a new project:

```bash
uv init chatbot-server
cd chatbot-server
uv add "mcp[cli]" "openai" "tiktoken" "pydantic"
```

## Features

- **Multiple AI providers** (OpenAI, Anthropic, local models)
- **Conversation persistence** with SQLite storage
- **Personality system** for different chatbot behaviors
- **Token usage tracking** and cost estimation
- **Context window management** for long conversations

## Safety Note

⚠️ **Important**: This tutorial involves AI model integration. Always implement content filtering and usage monitoring in production.
