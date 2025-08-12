"""
Local LLM Client for chatting with multiple backends.
Supports OpenAI-compatible (AsyncOpenAI), Ollama, and Transformers backends.
"""
import asyncio
import os
import json
from termios import tcdrain
import streamlit as st
from typing import Dict, List, Any, AsyncGenerator
from libs.mcp_client import MCPClient

# Optional imports for different LLM providers
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

# OpenAI-compatible client (AsyncOpenAI)
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False




class LocalLLMClient:
    def __init__(self, provider: str = "openai", model_name: str = "gpt-4o-mini"):
        self.provider = provider.lower()
        self.model_name = model_name
        print(f"provider: {self.provider}")
        print(f"OPENAI_AVAILABLE: {OPENAI_AVAILABLE}")
        self.mcp_client = self.initialize_mcp_client()
        # Initialize LLM based on provider
        if self.provider == "openai" and OPENAI_AVAILABLE:
            # Allow custom base_url for local OpenAI-compatible servers
            base_url = os.getenv("OPENAI_BASE_URL")
            api_key = os.getenv("OPENAI_API_KEY", "")
            # AsyncOpenAI requires an API key even for some local proxies; provide dummy if not set
            print(f"base_url: {base_url}")
            print(f"api_key: {api_key}")
            if not api_key:
                api_key = "not-set"
            self.client = AsyncOpenAI(base_url=base_url, api_key=api_key) if base_url else AsyncOpenAI(api_key=api_key)
        elif self.provider == "ollama" and OLLAMA_AVAILABLE:
            self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
            self.client = ollama.Client(host=self.ollama_host)
        elif self.provider == "transformers" and TRANSFORMERS_AVAILABLE:
            self._init_transformers()
        else:
            raise ValueError(f"Provider '{provider}' not available or not installed")
    
    def _init_transformers(self):
        """Initialize Transformers model and tokenizer."""
        try:
            from transformers import AutoModelForSeq2SeqLM
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Check if it's a seq2seq model (like Flan-T5) or causal LM
            if "t5" in self.model_name.lower() or "flan" in self.model_name.lower():
                self.model = AutoModelForSeq2SeqLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    device_map="auto" if torch.cuda.is_available() else None
                )
                self.is_seq2seq = True
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                    device_map="auto" if torch.cuda.is_available() else None
                )
                self.is_seq2seq = False
            
            # Set pad token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Transformers model: {e}")
    
    async def generate_response(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Dispatch chat generation to the selected provider."""
        print(f"generate_response provider: {self.provider}")
        if self.provider == "openai":
            async for chunk in self.generate_response_openai(messages):
                yield chunk
        elif self.provider == "ollama":
            async for chunk in self.generate_response_ollama(messages):
                yield chunk
        elif self.provider == "transformers":
            async for chunk in self.generate_response_transformers(messages):
                yield chunk
        else:
            yield f"Unsupported provider: {self.provider}"
    
    def initialize_mcp_client(self):
        try:
            # Instantiate without connecting; HTTP JSON-RPC will be used for tools
            client = MCPClient()
            return client
        except Exception as e:
            st.error(f"Failed to initialize MCP client: {e}")
            return None
    
    async def connect_to_mcp_server(self):
        """Connect to FastMCP server via SSE stream and discover capabilities."""
        try:
            print(f"🔗 Connecting to FastMCP SSE stream at: {self.mcp_server_url}")
            
            # Ensure URL ends with /sse for FastMCP SSE transport
            if not self.mcp_server_url.endswith('/sse'):
                sse_url = f"{self.mcp_server_url}/sse"
            else:
                sse_url = self.mcp_server_url
            
            # Test SSE stream connectivity with proper headers
            async with httpx.AsyncClient(timeout=15.0) as client:
                try:
                    print(f"📡 Testing SSE stream connection: {sse_url}")
                    
                    # SSE connections require specific headers
                    headers = {
                        'Accept': 'text/event-stream',
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive'
                    }
                    
                    # Test the SSE endpoint with a brief connection
                    async with client.stream('GET', sse_url, headers=headers) as response:
                        if response.status_code == 200:
                            print("✅ FastMCP SSE stream is accessible")
                            
                            # Read a small amount to verify it's actually streaming
                            try:
                                async for line in response.aiter_lines():
                                    if line.strip():
                                        print(f"📨 SSE stream active: {line[:50]}...")
                                        break
                            except:
                                # Even if we can't read the stream, connection is valid
                                print("✅ SSE endpoint responding (stream format confirmed)")
                        else:
                            print(f"❌ SSE endpoint returned status: {response.status_code}")
                            return False
                            
                except httpx.ConnectError as e:
                    print(f"❌ Cannot connect to FastMCP server: {e}")
                    return False
                except httpx.TimeoutException:
                    print(f"❌ Connection timeout to FastMCP server")
                    return False
                except Exception as e:
                    print(f"❌ SSE connection test failed: {e}")
                    return False
            
            # Dynamically discover FastMCP server capabilities
            print("🔍 Discovering FastMCP server capabilities...")
            
            # Initialize empty capabilities
            self.tools = []
            self.resources = []
            self.prompts = []
            
            # Discover tools, resources, and prompts from the MCP server
            async with httpx.AsyncClient(timeout=10.0) as discovery_client:
                try:
                    # Discover available tools
                    tools_response = await discovery_client.post(
                        f"{self.mcp_server_url.replace('/sse', '')}/mcp",
                        json={
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "tools/list",
                            "params": {}
                        },
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if tools_response.status_code == 200:
                        tools_data = tools_response.json()
                        if "result" in tools_data and "tools" in tools_data["result"]:
                            self.tools = tools_data["result"]["tools"]
                            print(f"📋 Discovered {len(self.tools)} tools from MCP server")
                        else:
                            print("⚠️ No tools found in MCP server response")
                    else:
                        print(f"⚠️ Failed to discover tools: {tools_response.status_code}")
                        
                except Exception as e:
                    print(f"⚠️ Tool discovery failed: {e}")
                
                try:
                    # Discover available resources
                    resources_response = await discovery_client.post(
                        f"{self.mcp_server_url.replace('/sse', '')}/mcp",
                        json={
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "resources/list",
                            "params": {}
                        },
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if resources_response.status_code == 200:
                        resources_data = resources_response.json()
                        if "result" in resources_data and "resources" in resources_data["result"]:
                            self.resources = resources_data["result"]["resources"]
                            print(f"📚 Discovered {len(self.resources)} resources from MCP server")
                        else:
                            print("⚠️ No resources found in MCP server response")
                    else:
                        print(f"⚠️ Failed to discover resources: {resources_response.status_code}")
                        
                except Exception as e:
                    print(f"⚠️ Resource discovery failed: {e}")
                
                try:
                    # Discover available prompts
                    prompts_response = await discovery_client.post(
                        f"{self.mcp_server_url.replace('/sse', '')}/mcp",
                        json={
                            "jsonrpc": "2.0",
                            "id": 3,
                            "method": "prompts/list",
                            "params": {}
                        },
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if prompts_response.status_code == 200:
                        prompts_data = prompts_response.json()
                        if "result" in prompts_data and "prompts" in prompts_data["result"]:
                            self.prompts = prompts_data["result"]["prompts"]
                            print(f"💡 Discovered {len(self.prompts)} prompts from MCP server")
                        else:
                            print("⚠️ No prompts found in MCP server response")
                    else:
                        print(f"⚠️ Failed to discover prompts: {prompts_response.status_code}")
                        
                except Exception as e:
                    print(f"⚠️ Prompt discovery failed: {e}")
            
            # Fallback to known capabilities if discovery fails
            if not self.tools:
                print("🔄 Using fallback tool definitions...")
                self.tools = [
                    {"name": "create_task", "description": "Create a new task"},
                    {"name": "list_tasks", "description": "List tasks"},
                    {"name": "complete_task", "description": "Mark a task as completed"},
                    {"name": "update_task", "description": "Update a task"},
                    {"name": "delete_task", "description": "Delete a task"},
                    {"name": "add_note", "description": "Add a note to a task"},
                    {"name": "get_task_details", "description": "Get task details"}
                ]
            
            print(f"🎉 FastMCP server ready: {len(self.tools)} tools, {len(self.resources)} resources, {len(self.prompts)} prompts")
            return True
                    
        except Exception as e:
            print(f"💥 FastMCP server connection error: {e}")
            return False
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool with given arguments."""
        try:
            # Use FastMCP JSON-RPC endpoint instead of a RESTful /tools path
            base_url = self.mcp_server_url.replace('/sse', '')
            payload = {
                "jsonrpc": "2.0",
                "id": 100,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {}
                }
            }
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{base_url}/mcp",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code != 200:
                    return {"error": f"Tool call HTTP {response.status_code}: {response.text}"}

                data = response.json()
                # Return the result section if present, else full payload
                if isinstance(data, dict) and "result" in data:
                    return data["result"]
                return data
        except Exception as e:
            return {"error": f"Failed to call tool: {e}"}

    def _build_openai_tools(self) -> List[Dict[str, Any]]:
        """Convert discovered MCP tools to OpenAI tools schema (for native tool calling)."""
        openai_tools: List[Dict[str, Any]] = []
        for t in self.tools:
            name = t.get("name")
            desc = t.get("description", "")
            schema = t.get("inputSchema", {"type": "object", "properties": {}})
            # Ensure schema has properties
            if "properties" not in schema:
                schema["properties"] = {}
            # Map to OpenAI tool format
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc,
                    "parameters": schema,
                },
            })
        return openai_tools
    
    def _format_system_prompt(self) -> str:
        """Create a system prompt that includes MCP tool information."""
        if not self.tools:
            return "You are a helpful AI assistant. Respond to user queries in a friendly and informative manner."
            
        system_prompt = """You are a helpful AI assistant with access to task management tools. 
You can help users create, update, delete, and manage their tasks efficiently.

🔧 AVAILABLE TOOLS:
"""
        
        for tool in self.tools:
            system_prompt += f"\n• **{tool['name']}**: {tool.get('description', 'No description')}"
            if 'inputSchema' in tool and 'properties' in tool['inputSchema']:
                params = list(tool['inputSchema']['properties'].keys())
                system_prompt += f"\n  Parameters: {', '.join(params)}"
        
        system_prompt += """

📋 TOOL USAGE INSTRUCTIONS:
When a user requests a task-related action, use this format:

**TOOL_CALL: tool_name**
- parameter1: value1
- parameter2: value2

For example:
**TOOL_CALL: create_task**
- title: Buy groceries
- description: Get milk, bread, and eggs
- priority: medium
- due_date: tomorrow

✨ GUIDELINES:
- Always provide helpful, natural responses
- Use tools when users ask for task management actions
- Ask for clarification if parameters are missing
- Explain what you're doing when using tools
- Be concise but informative
"""
        return system_prompt
    
    def _extract_tool_calls(self, text: str) -> List[Dict[str, Any]]:
        """Extract tool calls from LLM response text using the enhanced format."""
        tool_calls = []
        lines = text.split('\n')
        
        current_tool = None
        current_args = {}
        
        for line in lines:
            line = line.strip()
            
            # Look for enhanced tool call pattern: **TOOL_CALL: tool_name**
            if '**TOOL_CALL:' in line:
                # Save previous tool call if exists
                if current_tool:
                    tool_calls.append({"name": current_tool, "arguments": current_args})
                
                # Extract tool name from **TOOL_CALL: tool_name**
                try:
                    tool_part = line.split('**TOOL_CALL:')[1].split('**')[0].strip()
                    current_tool = tool_part
                    current_args = {}
                    print(f"🔧 Detected tool call: {current_tool}")
                except:
                    continue
            
            # Look for parameters in format: - parameter: value
            elif current_tool and line.startswith('-') and ':' in line:
                try:
                    param_line = line[1:].strip()  # Remove the '-'
                    if ':' in param_line:
                        key, value = param_line.split(':', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        if value:  # Only add non-empty values
                            current_args[key] = value
                            print(f"  📝 Parameter: {key} = {value}")
                except Exception as e:
                    print(f"  ⚠️ Failed to parse parameter: {line} - {e}")
                    continue
        
        # Add the last tool call if exists
        if current_tool:
            tool_calls.append({"name": current_tool, "arguments": current_args})
            print(f"✅ Final tool call: {current_tool} with args: {current_args}")
        
        return tool_calls

    async def generate_response_openai(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Generate a simple assistant response using AsyncOpenAI (no tools)."""
        if not OPENAI_AVAILABLE:
            yield "OpenAI client is not installed. Run: pip install openai"
            return
        print(f"self.generate_response_openai: ")
        # Try to fetch MCP tools (optional). Guard against connection issues.
        tools: List[Dict[str, Any]] = []
        try:
            if getattr(self, "mcp_client", None) is not None:
                tools = await self.mcp_client._async_get_mcp_tools()
                print(f"Fetched {len(tools)} MCP tools")
            else:
                print("MCP client not initialized; proceeding without tools")
        except Exception as e:
            print(f"Warning: failed to fetch MCP tools: {e}. Proceeding without tools.")
    
        # Construct a simple system prompt
        system_prompt = "You are a helpful AI assistant. Be concise and friendly."
        chat_messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for m in messages:
            chat_messages.append({"role": m["role"], "content": m["content"]})
        try:
            resp = await self.client.chat.completions.create(
                model=self.model_name,
                messages=chat_messages,
                temperature=0.7,
                # Only pass tools if available (some backends may not support it)
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
            )
            choice = resp.choices[0]
            msg = choice.message
            
            # Get tool calls from the message, not finish_reason
            tool_calls = getattr(msg, "tool_calls", None)

            # Case A: No tool calls -> just return assistant text
            if not tool_calls:
                yield msg.content

            # Case B: Tool calls -> execute each, append tool outputs, then ask model to finalize
            new_messages = messages + [dict(role="assistant", content=msg.content or "", tool_calls=[tc.dict() for tc in tool_calls])]

            for tc in tool_calls:
                if tc.type != "function":
                    continue
                try:
                    # Use the correct method name from MCPClient
                    result = await self.mcp_client.call_mcp_tool(
                        tc.function.name,
                        json.loads(tc.function.arguments or "{}")
                    )
                    # The result is already a string from call_mcp_tool
                    content = result if isinstance(result, str) else str(result)

                    new_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.function.name,
                        "content": content,
                    })
                except Exception as e:
                    new_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.function.name,
                        "content": f"Error: {str(e)}",
                    })

            # Ask the model to produce the final answer given tool results
            follow = await self.client.chat.completions.create(
                model=self.model_name,
                messages=new_messages,
                temperature=0.7,
            )
            final_msg = follow.choices[0].message

            if final_msg.content:
                yield final_msg.content
        except Exception as e:
            yield f"Error from OpenAI client: {e}"

    
    async def generate_response_ollama(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Generate response using Ollama (no tools)."""
        try:
            # Prepare a simple system prompt
            system_prompt = "You are a helpful AI assistant. Respond to user queries in a friendly and informative manner."
            
            # Format messages for Ollama
            prompt = f"System: {system_prompt}\n\n"
            for msg in messages:
                prompt += f"{msg['role'].title()}: {msg['content']}\n"
            prompt += "Assistant: "

            # Simple generation streaming
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                stream=True
            )
            for chunk in response:
                if 'response' in chunk:
                    yield chunk['response']
        
        except Exception as e:
            yield f"Error generating response: {e}"
    
    
    async def generate_response_transformers(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Generate response using Transformers (no tools)."""
        try:
            # Build a simple prompt
            if hasattr(self, 'is_seq2seq') and self.is_seq2seq:
                last = messages[-1]['content'] if messages else "Hello! How can I help you today?"
                prompt = f"Answer this question helpfully: {last}"
            else:
                system_prompt = "You are a helpful AI assistant. Respond to user queries in a friendly and informative manner."
                prompt = f"System: {system_prompt}\n\n"
                for msg in messages:
                    prompt += f"{msg['role'].title()}: {msg['content']}\n"
                prompt += "Assistant: "

            encoded = self.tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=512)
            inputs = encoded['input_ids']
            attention_mask = encoded['attention_mask']

            import torch
            with torch.no_grad():
                if hasattr(self, 'is_seq2seq') and self.is_seq2seq:
                    outputs = self.model.generate(inputs, attention_mask=attention_mask, max_new_tokens=256, temperature=0.7, do_sample=True, pad_token_id=self.tokenizer.pad_token_id)
                    text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                else:
                    outputs = self.model.generate(inputs, attention_mask=attention_mask, max_new_tokens=256, temperature=0.7, do_sample=True, pad_token_id=self.tokenizer.eos_token_id, eos_token_id=self.tokenizer.eos_token_id)
                    text = self.tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
            text = (text or "I'm here to help! What would you like to know?").strip()
            yield text
        except Exception as e:
            yield f"Error generating response: {e}"
    
    # Chat-only client: no MCP metadata
    def get_available_tools(self) -> List[Dict[str, Any]]:
        return []
    def get_available_resources(self) -> List[Dict[str, Any]]:
        return []
    def get_available_prompts(self) -> List[Dict[str, Any]]:
        return []
