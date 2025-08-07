"""
Streamlit Chat Client with Local GPT-OSS Model Integration.
Provides a web-based chat interface for interacting with MCP tools using local LLMs.
"""
import asyncio
import os
import streamlit as st
from typing import List, Dict, Any
from dotenv import load_dotenv
import json

from libs.local_llm_client import LocalLLMClient

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="MCP Chat with Local GPT-OSS",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "llm_client" not in st.session_state:
    st.session_state.llm_client = None
if "connected" not in st.session_state:
    st.session_state.connected = False

def initialize_llm_client():
    """Initialize the LLM client with configuration from environment."""
    try:
        provider = os.getenv("LLM_PROVIDER", "ollama")
        model_name = os.getenv("MODEL_NAME", "llama2:7b")
        mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
        
        client = LocalLLMClient(
            provider=provider,
            model_name=model_name,
            mcp_server_url=mcp_server_url
        )
        return client
    except Exception as e:
        st.error(f"Failed to initialize LLM client: {e}")
        return None

def connect_to_mcp():
    """Connect to MCP server and discover tools (optional)."""
    if st.session_state.llm_client:
        try:
            success = asyncio.run(st.session_state.llm_client.connect_to_mcp_server())
            st.session_state.connected = success
            return success
        except Exception as e:
            st.session_state.connected = False
            print(f"MCP connection failed (optional): {e}")
            return False
    return False

def display_sidebar():
    """Display sidebar with configuration and status."""
    with st.sidebar:
        st.title("🤖 MCP + Local GPT-OSS")
        
        # Configuration
        st.subheader("Configuration")
        provider = os.getenv("LLM_PROVIDER", "ollama")
        model_name = os.getenv("MODEL_NAME", "llama2:7b")
        mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
        
        st.info(f"**Provider:** {provider}")
        st.info(f"**Model:** {model_name}")
        st.info(f"**MCP Server:** {mcp_url}")
        
        # Connection status
        st.subheader("Status")
        if st.session_state.llm_client:
            st.success("✅ Local LLM Ready")
        else:
            st.error("❌ Local LLM Not Available")
            
        # MCP status (optional)
        st.subheader("MCP Integration")
        if st.session_state.connected:
            st.success("✅ Connected to MCP Server")
        else:
            st.warning("⚠️ MCP Server Not Connected (Optional)")
            if st.button("🔄 Try Connect to MCP"):
                with st.spinner("Connecting to MCP server..."):
                    connect_to_mcp()
                st.rerun()
        
        # Available tools
        if st.session_state.llm_client and st.session_state.connected:
            st.subheader("Available Tools")
            tools = st.session_state.llm_client.get_available_tools()
            if tools:
                for tool in tools:
                    with st.expander(f"🔧 {tool['name']}"):
                        st.write(tool.get('description', 'No description'))
                        if 'inputSchema' in tool:
                            st.json(tool['inputSchema'])
            else:
                st.write("No tools available")
        
        # Clear chat
        st.subheader("Actions")
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()

def display_chat_messages():
    """Display chat messages."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

async def generate_response(messages: List[Dict[str, str]]) -> str:
    """Generate response using the LLM client."""
    # if not st.session_state.llm_client or not st.session_state.connected:
    #     return "❌ Not connected to LLM or MCP server. Please check the connection."
    
    response_text = ""
    async for chunk in st.session_state.llm_client.generate_response(messages):
        response_text += chunk
    
    return response_text

def main():
    """Main Streamlit application."""
    st.title("🤖 MCP Chat with Local GPT-OSS")
    st.markdown("Chat with your local AI assistant that can manage tasks using MCP tools!")
    
    # Initialize LLM client if not already done
    if st.session_state.llm_client is None:
        with st.spinner("Initializing LLM client..."):
            st.session_state.llm_client = initialize_llm_client()
            if st.session_state.llm_client:
                # Try to connect to MCP server (optional)
                st.session_state.connected = connect_to_mcp()
    
    # Display sidebar
    display_sidebar()
    
    # Main chat interface
    if not st.session_state.llm_client:
        st.error("❌ Failed to initialize LLM client. Please check your configuration.")
        st.info("Make sure you have:")
        st.markdown("""
        - **Ollama**: Install Ollama and pull a model (e.g., `ollama pull llama2:7b`)
        - **Or Transformers**: Ensure you have sufficient RAM and disk space
        - **MCP Server**: Make sure the MCP server is running on the configured port
        """)
        return
    
    if not st.session_state.connected:
        st.info("💡 **MCP Server Optional**: You can chat with the local LLM without MCP. Start `python storage_mcp_server.py` for task management features.")
    
    # Display existing messages
    display_chat_messages()
    
    # Chat input
    if prompt := st.chat_input("Ask me anything about your tasks!"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate and display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = asyncio.run(generate_response(st.session_state.messages))
            
            # Stream the response
            message_placeholder = st.empty()
            full_response = ""
            
            # Simulate streaming by displaying the response progressively
            words = response.split()
            for i, word in enumerate(words):
                full_response += word + " "
                message_placeholder.markdown(full_response + "▌")
                # Small delay for streaming effect
                import time
                time.sleep(0.02)
            
            message_placeholder.markdown(full_response)
        
        # Add assistant response to session state
        st.session_state.messages.append({"role": "assistant", "content": response})

    # Example prompts
    st.subheader("💡 Try these examples:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📝 Create a task"):
            example_prompt = "Create a high priority task to finish the quarterly report by Friday"
            st.session_state.messages.append({"role": "user", "content": example_prompt})
            st.rerun()
    
    with col2:
        if st.button("📋 List my tasks"):
            example_prompt = "Show me all my pending tasks"
            st.session_state.messages.append({"role": "user", "content": example_prompt})
            st.rerun()
    
    with col3:
        if st.button("📊 Task summary"):
            example_prompt = "Give me a summary of all my tasks"
            st.session_state.messages.append({"role": "user", "content": example_prompt})
            st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>🚀 Powered by Local GPT-OSS + MCP | 🔒 Privacy-first, runs entirely locally</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
