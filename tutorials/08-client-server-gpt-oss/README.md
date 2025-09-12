# Tutorial: MCP Server with Local GPT-OSS Model

Learn how to build a complete MCP server with a local GPT-OSS model integrated Streamlit client that demonstrates MCP integration with open-source language models.

## What You'll Build

A complete MCP system that includes:
- **MCP Server**: Task management with tools, resources, and prompts (SSE transport)
- **Local GPT-OSS Client**: Streamlit chat interface powered by local open-source models
- **Full Integration**: End-to-end demonstration of MCP + local LLM capabilities

## Prerequisites

- Python 3.10+
- `uv` package manager
- Local GPT-OSS model (e.g., Ollama, llama.cpp, or Transformers)
- Basic understanding of MCP concepts
- At least 8GB RAM (16GB recommended for larger models)

## Learning Objectives

By the end of this tutorial, you'll understand:
- How to build a complete MCP server with SSE transport
- How to integrate MCP with local open-source LLM models
- How to create a Streamlit chat interface that uses MCP tools
- How to set up and run local GPT-OSS models efficiently
- How to seamlessly combine MCP tools, resources, and prompts with local LLM reasoning

## Project Structure

```
08-client-server-gpt-oss/
├── README.md                    # This tutorial guide
├── storage_mcp_server.py        # MCP server with SSE transport
├── start_client.py              # Streamlit chat client with local LLM
├── .env.example                 # Environment variables template
├── pyproject.toml              # Project configuration
├── requirements.txt            # Python dependencies
├── tasks.db                    # SQLite database for tasks
└── libs/                       # Supporting libraries
    ├── local_llm_client.py     # MCP client with local LLM integration
    ├── task_manager.py         # Task management logic
    └── storage.py              # Data persistence
```

## What Makes This Special

This tutorial is **different** from the others because:

✅ **Local LLM Integration** - Uses open-source models running locally (no API keys needed)  
✅ **SSE Transport** - HTTP-based server communication (not stdio)  
✅ **Privacy-First** - All processing happens locally, no data sent to external services  
✅ **Cost-Effective** - No API costs, runs entirely on your hardware  
✅ **Customizable** - Easy to swap different local models  

## Quick Start

1. **Install dependencies**:
   ```bash
   cd 08-client-server-gpt-oss
   uv sync
   ```

2. **Set up local model** (choose one):
   
   **Option A: Using Ollama (Recommended)**
   ```bash
   # Install Ollama
   brew install ollama
   
   # Pull SmolLM (lightweight and fast)
   ollama pull gpt-oss:20b
   ```
   
   **Option B: Using Transformers**
   ```bash
   # Models will be downloaded automatically when first run
   # Ensure you have sufficient disk space (5-15GB per model)
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env to set your preferred model
   ```

4. **Start the Streamlit client** (in another terminal):
   ```bash
   uv run streamlit run start_client.py
   ```

5. **Open your browser** to `http://localhost:8501`

## How It Works

### Architecture Overview

```
┌─────────────────┐    HTTP/SSE     ┌──────────────────┐
│  Streamlit UI   │ ◄─────────────► │   MCP Server     │
│                 │                 │                  │
│ ┌─────────────┐ │                 │ ┌──────────────┐ │
│ │ Local LLM   │ │                 │ │ Task Manager │ │
│ │ (Ollama/HF) │ │                 │ │              │ │
│ └─────────────┘ │                 │ └──────────────┘ │
└─────────────────┘                 └──────────────────┘
```

### Interaction Flow

1. **User Input** - User types a message in the Streamlit chat interface
2. **MCP Discovery** - Client discovers available tools, resources, and prompts
3. **Local LLM Processing** - Local model processes the request and decides which MCP tools to use
4. **Tool Execution** - MCP tools are executed on the server
5. **Response Generation** - The local LLM synthesizes tool results into a natural response
6. **Streaming UI** - Results are displayed with a typing animation

### 🎆 **Example Interactions**
- "Create a high priority task to finish the quarterly report by Friday"
- "Show me all my pending tasks"
- "Update task 5 to completed status"
- "What's the summary of my tasks this week?"

## Step-by-Step Implementation

### Step 1: Set Up the Project

Create the project structure:

```bash
mkdir 08-client-server-gpt-oss
cd 08-client-server-gpt-oss
mkdir libs
```

### Step 2: Environment Configuration

Create `.env.example`:

```env
# Local LLM Configuration
LLM_PROVIDER=ollama  # Options: ollama, transformers
MODEL_NAME=llama2:7b  # For Ollama: llama2:7b, codellama:7b, etc.
# MODEL_NAME=microsoft/DialoGPT-medium  # For Transformers

# Ollama Configuration (if using Ollama)
OLLAMA_HOST=http://localhost:11434

# Server Configuration
MCP_SERVER_URL=http://localhost:8000
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Database
DATABASE_PATH=./tasks.db
```

### Step 3: Create the Local LLM Client

The client integrates with local models and provides the Streamlit interface.

### Step 4: Implement Supporting Libraries

Create the task management, storage, and LLM integration libraries.

## Local Model Options

### Ollama (Recommended)
- **Pros**: Easy setup, good performance, model management
- **Models**: gpt-oss:20b, SmolLM, Llama 2, Code Llama, Mistral, Phi-3
- **Setup**: `ollama pull gpt-oss:20b` (recommended for this tutorial)

### Transformers (Hugging Face)
- **Pros**: Wide model selection, direct Python integration
- **Models**: GPT-2, DialoGPT, Flan-T5, CodeT5
- **Setup**: Models download automatically

### Performance Tips

1. **Memory Management**: Use smaller models (7B) for better performance
2. **GPU Acceleration**: Enable CUDA if you have a compatible GPU
3. **Model Quantization**: Use quantized models for faster inference
4. **Batch Processing**: Process multiple requests together when possible

## Troubleshooting

### Common Issues

1. **Out of Memory**: Use smaller models or increase swap space
2. **Slow Response**: Consider GPU acceleration or model quantization
3. **Model Download Fails**: Check internet connection and disk space
4. **Port Conflicts**: Change ports in `.env` file

### Performance Optimization

- Use quantized models (Q4, Q8) for better speed/memory trade-off
- Enable GPU acceleration if available
- Adjust context window size based on your use case
- Consider using streaming responses for better UX

## Next Steps

After completing this tutorial, you can:

1. **Experiment with Different Models**: Try various local models to find the best fit
2. **Add Custom Tools**: Extend the MCP server with domain-specific tools
3. **Improve UI**: Enhance the Streamlit interface with more features
4. **Deploy Locally**: Set up the system for local network access
5. **Performance Tuning**: Optimize for your specific hardware setup

## Resources

- [Ollama Documentation](https://ollama.ai/docs)
- [Hugging Face Transformers](https://huggingface.co/docs/transformers)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Streamlit Documentation](https://docs.streamlit.io/)

---

🎉 **Congratulations!** You've built a complete MCP system with local GPT-OSS integration!
