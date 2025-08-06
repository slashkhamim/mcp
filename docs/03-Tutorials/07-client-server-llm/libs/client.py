# client/jira_mcp_client.py
import os
import json
import asyncio
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

try:
    from dotenv import load_dotenv
    # Load environment variables from .env file (for local development)
    load_dotenv()
except ImportError:
    pass

from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import AsyncOpenAI


def get_secret(key: str, default: str = None) -> str:
    """Get secret from Streamlit secrets first, then fallback to environment variables"""
    # Try Streamlit secrets first (for cloud deployment or when running in Streamlit)
    if STREAMLIT_AVAILABLE and hasattr(st, 'secrets'):
        try:
            value = st.secrets.get(key)
            if value:  # If value exists and is not empty
                return value
        except (KeyError, FileNotFoundError, AttributeError):
            pass
    
    # Fallback to environment variables (for local development with .env)
    return os.getenv(key, default)


class JiraMcpClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        
        # Get secrets from Streamlit secrets or environment variables
        api_key = get_secret("OPENAI_API_KEY")
        self.openai_client = AsyncOpenAI(api_key=api_key)
        self.model = get_secret("OPEN_AI_MODEL", "gpt-4o-mini")
        self.jira_mcp_server_url = get_secret("JIRA_MCP_SERVER_URL", "http://localhost:9999/sse")

        print(self.jira_mcp_server_url, api_key)
        # Keep a persistent event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def connect_to_server(self):
        self.loop.run_until_complete(self._async_connect())

    def process_prompt(self, query: str) -> str:
        return self.loop.run_until_complete(self._async_process_prompt(query))

    def cleanup(self):
        self.loop.run_until_complete(self._async_cleanup())
        self.loop.close()

    async def _async_connect(self):
        sse_transport = await self.exit_stack.enter_async_context(sse_client(self.jira_mcp_server_url))
        self.session = await self.exit_stack.enter_async_context(ClientSession(*sse_transport))
        await self.session.initialize()

    async def _async_cleanup(self):
        await self.exit_stack.aclose()

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

    async def _async_process_prompt(self, query: str) -> str:
        tools = await self._async_get_mcp_tools()

        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": query}],
            tools=tools,
            tool_choice="auto",
        )

        assistant_message = response.choices[0].message
        messages = [{"role": "user", "content": query}, assistant_message]

        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                try:
                    result = await self.session.call_tool(
                        tool_call.function.name,
                        arguments=json.loads(tool_call.function.arguments),
                    )
                    content = ""
                    if result.content:
                        content = " ".join(getattr(item, "text", str(item)) for item in result.content)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content,
                    })
                except Exception as e:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": f"Error: {str(e)}",
                    })

            final_response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="none",
            )
            return final_response.choices[0].message.content

        return assistant_message.content