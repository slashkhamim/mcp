import os
import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.sse import sse_client
from typing import Any, Dict, List, Optional

class MCPClient:
    def __init__(self, provider: str = "openai", model_name: str = "gpt-4o-mini"):
       self.storage_mcp_server_url =  os.getenv("STORAGE_MCP_SERVER_URL", "http://localhost:9999/sse")
       self.exit_stack = AsyncExitStack()
       self.session: Optional[ClientSession] = None

       # Keep a persistent event loop (mirrors pattern used in JiraMcpClient)
       self.loop = asyncio.new_event_loop()
       asyncio.set_event_loop(self.loop)

    def connect_to_server(self):
        self.loop.run_until_complete(self._async_connect())

    async def _async_connect(self):
        sse_transport = await self.exit_stack.enter_async_context(sse_client(self.storage_mcp_server_url))
        self.session = await self.exit_stack.enter_async_context(ClientSession(*sse_transport))
        await self.session.initialize()
    
    def cleanup(self):
        # Optional: clean up resources if needed by caller
        self.loop.run_until_complete(self._async_cleanup())
        self.loop.close()
    
    async def _async_cleanup(self):
        await self.exit_stack.aclose()
        
    async def _async_get_mcp_tools(self) -> List[Dict[str, Any]]:
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
        tools_result = await self.session.list_tools()
        print(f"tools_result: {tools_result}")
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
