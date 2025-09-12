# Tutorial: Building a File System MCP Server

Learn how to create an MCP server that provides file system operations as tools and resources.

## What You'll Build

A file system MCP server that provides:
- **Tools**: Create, read, write, delete files and directories
- **Resources**: Browse directory contents and file metadata
- **Prompts**: Generate file operation scripts and documentation

## Prerequisites

- Python 3.10+
- `uv` package manager
- Basic understanding of file systems

## Learning Objectives

By the end of this tutorial, you'll understand:
- How to implement file system operations safely
- Resource management for directory browsing
- Error handling and security considerations
- Testing file system operations

## Project Structure

```
file-system-server/
├── server.py          # Main MCP server
├── file_operations.py # File system utilities
├── security.py        # Security and validation
├── test_server.py     # Tests
└── client.py          # Example client
```

## Step 1: Setup

```bash
uv sync
```

## Step 2: Run the Server

```bash
# Option 1: Run with main.py
uv run python main.py

# Option 2: Run with MCP CLI (development mode)
uv run mcp dev main.py

# Option 3: Run server directly
uv run mcp run server.py
```

## Step 3: Test the Server

Run the comprehensive test suite:

```bash
# Run all tests
uv run pytest test_server.py

# Run tests with verbose output
uv run pytest test_server.py -v

# Run specific test class
uv run pytest test_server.py::TestFileSystemMCPServer

# Run specific test method
uv run pytest test_server.py::TestFileSystemMCPServer::test_read_file_success
```

### Test Coverage

The test suite covers:
- ✅ **All Tools**: read_file, write_file, create_directory, delete_file, list_directory, file_info
- ✅ **All Resources**: fs://dir/{path}, fs://file/{path}
- ✅ **All Prompts**: file_script, file_documentation
- ✅ **Security**: Path validation and safety checks
- ✅ **Performance**: Large files and many files handling
- ✅ **Integration**: Complete workflows

## Next Steps

Follow the implementation guide in the subsequent files to build your file system MCP server.

## Safety Note

⚠️ **Important**: This tutorial includes file system operations. Always validate paths and implement proper security measures in production use.
