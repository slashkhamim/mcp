---
title: Testing
sidebar_position: 2
---

# Testing

MCP provides comprehensive testing tools and frameworks to ensure reliable implementations.

## 1. Inspector
**MCP Inspector** is a debugging and development tool for MCP servers:

**Features:**
- **Interactive Testing**: Send requests and view responses in real-time
- **Protocol Validation**: Verify JSON-RPC message compliance
- **Resource Browser**: Explore available resources and their content
- **Tool Tester**: Execute tools with custom parameters
- **Performance Monitoring**: Track response times and resource usage
- **Error Analysis**: Detailed error reporting and stack traces

**command:**
```bash
uv run mcp dev main.py
```

## 2. Claude Desktop
**Claude Desktop** serves as a reference implementation and testing platform:

**Testing Capabilities:**
- **End-to-end Testing**: Full integration testing with real AI interactions
- **User Experience Testing**: Validate the complete user workflow
- **Performance Testing**: Measure real-world performance characteristics
- **Compatibility Testing**: Ensure compatibility with different server implementations

**command:**
```bash
uv run mcp install main.py
```

**Manual Configuration:**
When you don't have uv installed, you can manually configure the mcp server in claude desktop. And restart claude desktop to load the new server.
```bash
# find your uv path
which uv
```

```json
{
  "mcpServers": {
    "demo": {
      "command": "your-uv-path",
      "args": ["run",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "/path-to-your-project/mcp-server-demo/main.py"]
    }
  }
}
```

## 3. E2E Test
**End-to-End Testing Framework** provides automated testing capabilities:

**Test Types:**
- **Connection Tests**: Verify server startup and client connection
- **Resource Tests**: Test resource discovery and content retrieval
- **Tool Tests**: Validate tool execution and error handling
- **Performance Tests**: Measure throughput and latency
- **Security Tests**: Verify authentication and authorization

**Example Test:**

```bash
# Main dependencies
uv add "mcp[cli]" "pytest"
# Dev dependencies
uv add "pytest-asyncio" --dev
```

**test_mcp.py**

```python

import pytest
from main import mcp  # Import the actual server instance

class TestMCPServerCalls:
    """Test actual MCP server method calls."""
    
    def test_call_add_tool_real(self):
        """Test calling the real add tool through MCP server."""
        # Call the actual MCP server's call_tool method with correct signature
        import asyncio
        result = asyncio.run(mcp.call_tool("add", {"a": 5, "b": 3}))
        
        # Check that we got a result - it's a tuple (content, metadata)
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2
        
        content, metadata = result
        assert len(content) > 0
        # The result should be "8" as text
        assert "8" in str(content[0].text)
        # Check metadata contains the actual result
        assert metadata['result'] == 8
    
    
```

## 4. MCP Client
**MCP Client SDK** includes built-in testing utilities:

**Testing Features:**
- **Mock Servers**: Create mock servers for unit testing
- **Test Transports**: In-memory transports for fast testing
- **Assertion Helpers**: Specialized assertions for MCP protocols
- **Coverage Analysis**: Track protocol method coverage

**Client Example:**

```bash
# If you haven't created a uv-managed project yet, create one
uv init mcp-server-demo
cd mcp-server-demo
# Copy the client.py file from the examples directory
cp ../client.sample.py ./client.py
# Copy the interactive_client.py file from the examples directory
cp ../interactive_client.sample.py ./interactive_client.py
# Then add MCP to your project dependencies
uv add "mcp[cli]" 
# To run the mcp client command with uv
uv run python client.py 
# Or to run the mcp interactive client command with uv
uv run python interactive_client.py 
```
