import os
import asyncio
from contextlib import AsyncExitStack
from typing import List, Dict, Any
from mcp.client.sse import sse_client
from mcp.types import Tool
from mcp.client.session import ClientSession

class MCPAdapter:
    """Client for interacting with the MCP server using FastMCP client."""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:9999/sse")
        self.token = None
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def connect_to_server(self, token=None):
        self.token = token
        self.loop.run_until_complete(self._async_connect())
    
    def list_tools(self):
        return self.loop.run_until_complete(self._async_get_mcp_tools())

    def call_tool(self, tool_name: str, parameters: Dict[str, Any]):
        return self.loop.run_until_complete(self._async_call_mcp_tool(tool_name, parameters))

    def read_resource(self, uri: str) -> Any:
        return self.loop.run_until_complete(self._async_read_resource(uri))

    async def _async_connect(self):
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            
        sse_transport = await self.exit_stack.enter_async_context(sse_client(self.mcp_server_url, headers=headers))
        self.session = await self.exit_stack.enter_async_context(ClientSession(*sse_transport))
        await self.session.initialize()

    async def _async_get_mcp_tools(self) -> List[Dict[str, Any]]:
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        tools_result = await self.session.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for tool in tools_result.tools
        ]
    
    async def _async_call_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        try:
            return await self.session.call_tool(tool_name, parameters)
        except Exception as e:
            print(f"Error calling tool {tool_name}: {str(e)}")
            raise

    async def _async_read_resource(self, uri: str) -> Any:
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        
        try:
            return await self.session.read_resource(uri)
        except Exception as e:
            print(f"Error reading resource {uri}: {str(e)}")
            raise