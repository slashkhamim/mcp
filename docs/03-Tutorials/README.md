# MCP Server Tutorials

Welcome to the MCP Server tutorials! These comprehensive guides will teach you how to build different types of MCP servers for various use cases.

## Available Tutorials

### 1. [File System Server](./01-file-system-server/)
**Difficulty: Beginner** 🟢

Learn to build an MCP server that provides file system operations.

**What you'll learn:**
- File and directory operations through MCP tools
- Resource browsing for directory contents
- Security validation and path sanitization
- Error handling for file operations

**Key Features:**
- ✅ Read, write, create, delete files and directories
- ✅ Directory browsing as resources
- ✅ File information and metadata
- ✅ Security validation and sandboxing

---

### 2. [Web Scraper Server](./02-web-scraper-server/)
**Difficulty: Intermediate** 🟡

Build an MCP server for web scraping and data extraction.

**What you'll learn:**
- HTTP requests and response handling
- HTML parsing and data extraction
- Rate limiting and caching strategies
- Ethical scraping practices

**Key Features:**
- ✅ Fetch and parse web pages
- ✅ Extract links, text, and structured data
- ✅ Table parsing and data extraction
- ✅ Cached content resources

---

### 3. [Database Server](./03-database-server/)
**Difficulty: Intermediate** 🟡

Create an MCP server for database operations and management.

**What you'll learn:**
- Safe SQL query execution
- Database schema introspection
- Transaction management
- Query optimization and performance

**Key Features:**
- ✅ Execute queries with parameter binding
- ✅ Create, read, update, delete operations
- ✅ Schema browsing as resources
- ✅ Backup and restore functionality

---

### 4. [API Integration Server](./04-api-integration-server/)
**Difficulty: Intermediate** 🟡

Build an MCP server that integrates with external APIs.

**What you'll learn:**
- REST API integration patterns
- Authentication handling (API keys, OAuth)
- Rate limiting and error handling
- Response caching and validation

**Key Features:**
- ✅ Generic API request tools
- ✅ GitHub and weather API examples
- ✅ Authentication management
- ✅ Rate limiting and caching

---

### 5. [Chatbot Server](./05-chatbot-server/)
**Difficulty: Advanced** 🔴

Create an MCP server with AI chatbot capabilities.

**What you'll learn:**
- LLM API integration
- Conversation state management
- Personality system design
- Token usage and cost tracking

**Key Features:**
- ✅ Multi-model AI integration
- ✅ Conversation persistence
- ✅ Personality configuration
- ✅ Usage analytics and cost tracking

---

## Getting Started

Each tutorial is self-contained and includes:

- **📖 README.md** - Tutorial overview and setup instructions
- **🔧 server.py** - Complete MCP server implementation
- **🧪 Supporting modules** - Utility classes and helpers
- **✅ test_server.py** - Comprehensive test suite
- **👥 client.py** - Example client for testing

## Prerequisites

All tutorials require:
- **Python 3.10+**
- **uv package manager**
- **Basic MCP knowledge** (complete Getting Started first)

## Tutorial Structure

Each tutorial follows this structure:

```
tutorial-name/
├── README.md          # Tutorial guide
├── server.py          # Main MCP server
├── *.py               # Supporting modules
├── test_server.py     # Test suite
├── client.py          # Example client
└── requirements.txt   # Dependencies
```

## Learning Path

**Recommended order for beginners:**

1. **File System Server** - Learn basic MCP concepts
2. **API Integration Server** - Understand external integrations
3. **Web Scraper Server** - Practice data processing
4. **Database Server** - Master data persistence
5. **Chatbot Server** - Advanced AI integration

## Common Patterns

All tutorials demonstrate these MCP patterns:

### 🔧 **Tools Pattern**
```python
@mcp.tool()
def my_tool(param: str) -> str:
    """Tool description"""
    # Implementation
    return result
```

### 📚 **Resources Pattern**
```python
@mcp.resource("scheme://path/{param}")
def my_resource(param: str) -> str:
    """Resource description"""
    # Return JSON data
    return json.dumps(data)
```

### 💬 **Prompts Pattern**
```python
@mcp.prompt()
def my_prompt(context: str) -> str:
    """Prompt description"""
    # Return prompt template
    return f"Generate {context}..."
```

## Best Practices

Each tutorial emphasizes:

- ✅ **Error handling** and graceful failures
- ✅ **Input validation** and security
- ✅ **Resource management** and cleanup
- ✅ **Testing** and quality assurance
- ✅ **Documentation** and examples

## Support

If you encounter issues:

1. Check the tutorial's README for troubleshooting
2. Review the test files for usage examples
3. Examine the client.py for integration patterns
4. Refer to the main MCP documentation

## Contributing

Found an issue or want to improve a tutorial?

1. Test your changes thoroughly
2. Update documentation as needed
3. Add tests for new functionality
4. Follow the existing code style

Happy learning! 🚀
