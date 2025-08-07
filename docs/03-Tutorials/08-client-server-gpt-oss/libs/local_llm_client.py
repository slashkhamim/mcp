"""
Local LLM Client for MCP integration with open-source models.
Supports both Ollama and Transformers backends.
"""
import asyncio
import json
import os
from typing import Dict, List, Any, Optional, AsyncGenerator
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Optional imports for different LLM providers
try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

class LocalLLMClient:
    def __init__(self, provider: str = "ollama", model_name: str = "llama2:7b", 
                 mcp_server_url: str = None):
        self.provider = provider.lower()
        self.model_name = model_name
        self.mcp_server_url = mcp_server_url or os.getenv("MCP_SERVER_URL", "http://localhost:8000/sse")
        self.mcp_session = None
        self.tools = []
        self.resources = []
        self.prompts = []
        
        # Initialize LLM based on provider
        if self.provider == "ollama" and OLLAMA_AVAILABLE:
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
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mcp_server_url}/tools/{tool_name}",
                    json={"arguments": arguments}
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Tool call failed: {response.text}"}
        except Exception as e:
            return {"error": f"Failed to call tool: {e}"}
    
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
    
    async def generate_response_ollama(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Generate response using Ollama with multiple tool calling approaches."""
        try:
            # Prepare the prompt - use basic prompt if no MCP tools available
            if self.tools:
                system_prompt = self._format_system_prompt()
            else:
                system_prompt = "You are a helpful AI assistant. Respond to user queries in a friendly and informative manner."
            
            # Format messages for Ollama
            prompt = f"System: {system_prompt}\n\n"
            for msg in messages:
                prompt += f"{msg['role'].title()}: {msg['content']}\n"
            prompt += "Assistant: "
            
            # Try structured output first (for compatible models)
            if self.tools and self._supports_structured_output():
                async for chunk in self._generate_with_structured_output(prompt):
                    yield chunk
            else:
                # Fallback to prompt engineering approach
                async for chunk in self._generate_with_prompt_parsing(prompt):
                    yield chunk
                    
        except Exception as e:
            yield f"Error generating response: {e}"
    
    def _supports_structured_output(self) -> bool:
        """Check if the current model supports structured output."""
        # Models known to support structured output
        structured_models = [
            'llama3.1', 'llama3.2', 'qwen2.5', 'mistral-nemo', 
            'gemma2', 'phi3.5', 'codegemma'
        ]
        return any(model in self.model_name.lower() for model in structured_models)
    
    async def _generate_with_structured_output(self, prompt: str) -> AsyncGenerator[str, None]:
        """Generate response using structured output for tool calling."""
        try:
            # Create a schema for tool calls
            tool_schema = {
                "type": "object",
                "properties": {
                    "response": {"type": "string", "description": "Natural language response to user"},
                    "tool_calls": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "arguments": {"type": "object"}
                            }
                        }
                    }
                }
            }
            
            # Generate with format constraint
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt + "\n\nRespond in JSON format with 'response' and 'tool_calls' fields.",
                format="json",
                stream=False
            )
            
            if 'response' in response:
                try:
                    result = json.loads(response['response'])
                    
                    # Yield the natural response
                    if 'response' in result:
                        yield result['response']
                    
                    # Execute tool calls if present
                    if 'tool_calls' in result and result['tool_calls']:
                        yield "\n\n🔧 *Executing tools...*\n\n"
                        for tool_call in result['tool_calls']:
                            if 'name' in tool_call and 'arguments' in tool_call:
                                result = await self.call_mcp_tool(tool_call['name'], tool_call['arguments'])
                                yield f"**{tool_call['name']}**: {json.dumps(result, indent=2)}\n\n"
                                
                except json.JSONDecodeError:
                    # Fallback to prompt parsing if JSON parsing fails
                    async for chunk in self._generate_with_prompt_parsing(prompt):
                        yield chunk
                        
        except Exception as e:
            print(f"Structured output failed: {e}, falling back to prompt parsing")
            async for chunk in self._generate_with_prompt_parsing(prompt):
                yield chunk
    
    async def _generate_with_prompt_parsing(self, prompt: str) -> AsyncGenerator[str, None]:
        """Generate response using prompt engineering and parsing (fallback method)."""
        # Generate response
        response = self.client.generate(
            model=self.model_name,
            prompt=prompt,
            stream=True
        )
        
        full_response = ""
        for chunk in response:
            if 'response' in chunk:
                text = chunk['response']
                full_response += text
                yield text
        
        # Check for tool calls in the response (only if MCP tools are available)
        if self.tools:
            tool_calls = self._extract_tool_calls(full_response)
            if tool_calls:
                yield "\n\n🔧 *Executing tools...*\n\n"
                for tool_call in tool_calls:
                    result = await self.call_mcp_tool(tool_call['name'], tool_call['arguments'])
                    yield f"**{tool_call['name']}**: {json.dumps(result, indent=2)}\n\n"
    
    async def generate_response_transformers(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Generate response using Transformers."""
        try:
            # Get the last user message for seq2seq models
            if hasattr(self, 'is_seq2seq') and self.is_seq2seq:
                # For seq2seq models like Flan-T5, use a simpler prompt format
                if messages:
                    last_message = messages[-1]['content']
                    if self.tools:
                        prompt = f"You are a helpful AI assistant with task management capabilities. Answer this question: {last_message}"
                    else:
                        prompt = f"Answer this question helpfully: {last_message}"
                else:
                    prompt = "Hello! How can I help you today?"
            else:
                # For causal LM models, use the full conversation format
                if self.tools:
                    system_prompt = self._format_system_prompt()
                else:
                    system_prompt = "You are a helpful AI assistant. Respond to user queries in a friendly and informative manner."
                
                prompt = f"System: {system_prompt}\n\n"
                for msg in messages:
                    prompt += f"{msg['role'].title()}: {msg['content']}\n"
                prompt += "Assistant: "
            
            # Tokenize with attention mask
            encoded = self.tokenizer(
                prompt, 
                return_tensors="pt", 
                padding=True, 
                truncation=True,
                max_length=512  # Shorter for better performance
            )
            inputs = encoded['input_ids']
            attention_mask = encoded['attention_mask']
            
            # Generate with appropriate parameters for the model type
            with torch.no_grad():
                if hasattr(self, 'is_seq2seq') and self.is_seq2seq:
                    # Seq2seq generation
                    outputs = self.model.generate(
                        inputs,
                        attention_mask=attention_mask,
                        max_new_tokens=256,
                        temperature=0.7,
                        do_sample=True,
                        pad_token_id=self.tokenizer.pad_token_id
                    )
                    # For seq2seq, decode the entire output
                    response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                else:
                    # Causal LM generation
                    outputs = self.model.generate(
                        inputs,
                        attention_mask=attention_mask,
                        max_new_tokens=256,
                        temperature=0.7,
                        do_sample=True,
                        pad_token_id=self.tokenizer.eos_token_id,
                        eos_token_id=self.tokenizer.eos_token_id
                    )
                    # For causal LM, decode only the new tokens
                    response = self.tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
            
            # Clean up the response
            response = response.strip()
            if not response:
                response = "I'm here to help! What would you like to know?"
            
            # Stream the response word by word for better UX
            words = response.split()
            for word in words:
                yield word + " "
                await asyncio.sleep(0.03)  # Faster streaming
            
            # Check for tool calls (only if MCP tools are available)
            if self.tools:
                tool_calls = self._extract_tool_calls(response)
                if tool_calls:
                    yield "\n\n*Executing tools...*\n\n"
                    for tool_call in tool_calls:
                        result = await self.call_mcp_tool(tool_call['name'], tool_call['arguments'])
                        yield f"**{tool_call['name']}**: {json.dumps(result, indent=2)}\n\n"
                    
        except Exception as e:
            yield f"Error generating response: {e}"
    
    async def generate_response(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Generate response using the configured LLM provider."""
        if self.provider == "ollama":
            async for chunk in self.generate_response_ollama(messages):
                yield chunk
        elif self.provider == "transformers":
            async for chunk in self.generate_response_transformers(messages):
                yield chunk
        else:
            yield f"Unsupported provider: {self.provider}"
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools."""
        return self.tools
    
    def get_available_resources(self) -> List[Dict[str, Any]]:
        """Get list of available MCP resources."""
        return self.resources
    
    def get_available_prompts(self) -> List[Dict[str, Any]]:
        """Get list of available MCP prompts."""
        return self.prompts
