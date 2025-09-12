import os
import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.client.sse import sse_client
from typing import Any, Dict, List, Optional
import httpx
import logging

# Configure logging to reduce noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("mcp").setLevel(logging.WARNING)

class MCPClient:
    def __init__(self, provider: str = "openai", model_name: str = "gpt-4o-mini"):
        self.storage_mcp_server_url = os.getenv("STORAGE_MCP_SERVER_URL", "http://localhost:8000/sse")
        self.exit_stack = None
        self.session: Optional[ClientSession] = None
        self._connection_lock = asyncio.Lock()

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
        """Connect to MCP server with proper async context management."""
        async with self._connection_lock:
            if self.session is not None:
                return  # Already connected
            
            try:
                print(f"🔗 Connecting to FastMCP SSE stream at: {self.storage_mcp_server_url}")
                self.exit_stack = AsyncExitStack()
                sse_transport = await self.exit_stack.enter_async_context(
                    sse_client(self.storage_mcp_server_url)
                )
                self.session = await self.exit_stack.enter_async_context(
                    ClientSession(*sse_transport)
                )
                await self.session.initialize()
            except Exception as e:
                print(f"❌ Failed to connect to MCP server: {e}")
                if self.exit_stack:
                    try:
                        await self.exit_stack.aclose()
                    except Exception:
                        pass
                    self.exit_stack = None
                self.session = None
                raise
    
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
        """Properly cleanup all resources."""
        async with self._connection_lock:
            if self.exit_stack:
                try:
                    await self.exit_stack.aclose()
                except Exception as e:
                    print(f"Warning: Error during cleanup: {e}")
                finally:
                    self.exit_stack = None
            self.session = None
        
    async def _async_get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get MCP tools with improved error handling and connection management."""
        # Prefer HTTP JSON-RPC discovery to avoid SSE generator closing issues
        try:
            tools = await self._http_discover_tools()
            print(f"Discovered {len(tools)} tools via HTTP JSON-RPC")
            return tools
        except Exception as e:
            print(f"HTTP discovery failed ({e}); attempting SSE list_tools() with timeout...")
        
        # Fallback to SSE with improved connection handling
        return await self._sse_discover_tools_safe()
    
    async def _sse_discover_tools_safe(self) -> List[Dict[str, Any]]:
        """Safely discover tools via SSE with proper cleanup handling."""
        session = None
        exit_stack = None
        
        try:
            # Create a new, isolated connection for tool discovery
            exit_stack = AsyncExitStack()
            print(f"🔗 Connecting to FastMCP SSE stream at: {self.storage_mcp_server_url}")
            
            # Use a shorter-lived connection just for discovery
            sse_transport = await exit_stack.enter_async_context(
                sse_client(self.storage_mcp_server_url)
            )
            session = await exit_stack.enter_async_context(
                ClientSession(*sse_transport)
            )
            await session.initialize()
            
            # Get tools with timeout
            tools_result = await asyncio.wait_for(session.list_tools(), timeout=8.0)
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema or {"type": "object", "properties": {}},
                    },
                }
                for tool in tools_result.tools
            ]
            print(f"Fetched {len(tools)} MCP tools via SSE")
            
            # Clean up immediately after getting tools
            await exit_stack.aclose()
            return tools
            
        except asyncio.TimeoutError:
            print("SSE list_tools() timed out")
            return []
        except Exception as e:
            print(f"SSE discovery failed: {e}")
            return []
        finally:
            # Ensure cleanup happens even if there's an error
            if exit_stack:
                try:
                    await exit_stack.aclose()
                except Exception as cleanup_error:
                    # Suppress cleanup errors to avoid the original issue
                    print(f"Warning: SSE cleanup error (suppressed): {cleanup_error}")
        
    async def _http_discover_tools(self) -> List[Dict[str, Any]]:
        """Discover tools using FastMCP HTTP JSON-RPC endpoint (tools/list)."""
        base_url = self.storage_mcp_server_url.replace('/sse', '')
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        timeout = httpx.Timeout(10.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                resp = await client.post(
                    f"{base_url}/mcp",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
                    
                data = resp.json()
                if "error" in data:
                    raise RuntimeError(f"JSON-RPC error: {data['error']}")
                    
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
            except httpx.ConnectError as e:
                raise RuntimeError(f"Connection failed: {e}")
            except httpx.TimeoutException as e:
                raise RuntimeError(f"Request timed out: {e}")
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call an MCP tool with the given arguments using a safe connection."""
        exit_stack = None
        session = None
        
        try:
            # Create a dedicated connection for this tool call
            exit_stack = AsyncExitStack()
            
            sse_transport = await exit_stack.enter_async_context(
                sse_client(self.storage_mcp_server_url)
            )
            session = await exit_stack.enter_async_context(
                ClientSession(*sse_transport)
            )
            await session.initialize()
            
            # Call the tool with timeout
            result = await asyncio.wait_for(
                session.call_tool(tool_name, arguments),
                timeout=30.0
            )
            
            if result.isError:
                error_msg = result.content[0].text if result.content else 'Unknown error'
                return f"Tool error: {error_msg}"
            
            success_msg = result.content[0].text if result.content else "Tool executed successfully"
            
            # Clean up immediately after tool execution
            await exit_stack.aclose()
            return success_msg
            
        except asyncio.TimeoutError:
            return f"Error: Tool '{tool_name}' timed out"
        except Exception as e:
            return f"Error calling tool '{tool_name}': {e}"
        finally:
            # Ensure cleanup happens even if there's an error
            if exit_stack:
                try:
                    await exit_stack.aclose()
                except Exception as cleanup_error:
                    # Suppress cleanup errors to avoid the original issue
                    print(f"Warning: Tool execution cleanup error (suppressed): {cleanup_error}")
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """Public method to get available MCP tools."""
        try:
            return await self._async_get_mcp_tools()
        except Exception as e:
            print(f"Failed to get MCP tools: {e}")
            return []
