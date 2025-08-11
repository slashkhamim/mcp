import os
import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.sse import sse_client
from typing import Any, Dict, List, Optional
import httpx

class MCPClient:
    def __init__(self, provider: str = "openai", model_name: str = "gpt-4o-mini"):
       self.storage_mcp_server_url =  os.getenv("STORAGE_MCP_SERVER_URL", "http://localhost:9999/sse")
       self.exit_stack = AsyncExitStack()
       self.session: Optional[ClientSession] = None

    def connect_to_server(self):
        """Connect synchronously if no loop is running; otherwise schedule the task."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            # Schedule without awaiting (caller is likely in async context)
            return asyncio.create_task(self._async_connect())
        else:
            asyncio.run(self._async_connect())

    async def _async_connect(self):
        sse_transport = await self.exit_stack.enter_async_context(sse_client(self.storage_mcp_server_url))
        self.session = await self.exit_stack.enter_async_context(ClientSession(*sse_transport))
        await self.session.initialize()
    
    async def ensure_connected(self):
        """Ensure there is an active MCP session using the current event loop.
        Safe to call from any async context; no-op if already connected.
        """
        if self.session is None:
            await self._async_connect()
    
    def cleanup(self):
        """Cleanup resources; safe in both sync and async contexts."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            return asyncio.create_task(self._async_cleanup())
        else:
            asyncio.run(self._async_cleanup())
    
    async def _async_cleanup(self):
        await self.exit_stack.aclose()
        
    async def _async_get_mcp_tools(self) -> List[Dict[str, Any]]:
        # Prefer HTTP JSON-RPC discovery to avoid SSE generator closing issues
        try:
            tools = await self._http_discover_tools()
            print(f"Discovered {len(tools)} tools via HTTP JSON-RPC")
            return tools
        except Exception as e:
            print(f"HTTP discovery failed ({e}); attempting SSE list_tools() with timeout...")
        
        # Fallback to SSE if HTTP discovery fails
        try:
            await self.ensure_connected()
            tools_result = await asyncio.wait_for(self.session.list_tools(), timeout=5.0)
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
        except asyncio.TimeoutError:
            raise RuntimeError("SSE list_tools() timed out; please ensure the FastMCP server supports MCP list_tools over SSE")
        
    async def _http_discover_tools(self) -> List[Dict[str, Any]]:
        """Discover tools using FastMCP HTTP JSON-RPC endpoint (tools/list)."""
        base_url = self.storage_mcp_server_url.replace('/sse', '')
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{base_url}/mcp",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
            data = resp.json()
            raw_tools = data.get("result", {}).get("tools", [])
            # Map to OpenAI tool schema
            tools: List[Dict[str, Any]] = []
            for t in raw_tools:
                schema = t.get("inputSchema") or {"type": "object", "properties": {}}
                if "properties" not in schema:
                    schema["properties"] = {}
                tools.append({
                    "type": "function",
                    "function": {
                        "name": t.get("name"),
                        "description": t.get("description", ""),
                        "parameters": schema,
                    },
                })
            return tools
