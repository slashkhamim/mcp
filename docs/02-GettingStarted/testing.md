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
```python
import pytest

from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import (
    create_connected_server_and_client_session as create_session,
)

# Mark the whole module for async tests
pytestmark = pytest.mark.anyio

async def test_list_tools_cursor_parameter():
    """Test that the cursor parameter is accepted for list_tools.

    Note: FastMCP doesn't currently implement pagination, so this test
    only verifies that the cursor parameter is accepted by the client.
    """

    from .main import create_server
    server = create_server()

    async with create_session(server._mcp_server) as client_session:
        # Test without cursor parameter (omitted)
        result1 = await client_session.list_tools()
        assert len(result1.tools) == 2

        # Test with cursor=None
        result2 = await client_session.list_tools(cursor=None)
        assert len(result2.tools) == 2

        # Test with cursor as string
        result3 = await client_session.list_tools(cursor="some_cursor_value")
        assert len(result3.tools) == 2

        # Test with empty string cursor
        result4 = await client_session.list_tools(cursor="")
        assert len(result4.tools) == 2
    
    
```

## 4. MCP Client
**MCP Client SDK** includes built-in testing utilities:

**Testing Features:**
- **Mock Servers**: Create mock servers for unit testing
- **Test Transports**: In-memory transports for fast testing
- **Assertion Helpers**: Specialized assertions for MCP protocols
- **Coverage Analysis**: Track protocol method coverage

**Mock Server Example:**
```python
from mcp.client import MCPClient
from mcp.testing import MockMCPServer

mock_server = MockMCPServer(
    resources=[
        {"uri": "test://resource1", "name": "Test Resource"}
    ],
    tools=[
        {"name": "test_tool", "description": "Test tool"}
    ]
)

client = MCPClient()
await client.connect(mock_server.transport)
```
