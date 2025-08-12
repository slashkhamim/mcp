"""
Streamlit Chat Client with Local LLM Integration.
Provides a simple web-based chat interface for interacting with local LLMs.
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
    page_title="Local LLM Chat",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "llm_client" not in st.session_state:
    st.session_state.llm_client = None
 

def initialize_llm_client():
    """Initialize the LLM client with configuration from environment."""
    try:
        provider = os.getenv("LLM_PROVIDER", "openai")
        model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
        client = LocalLLMClient(provider=provider, model_name=model_name)
        return client
    except Exception as e:
        st.error(f"Failed to initialize LLM client: {e}")
        return None

 
def display_sidebar():
    """Display sidebar with configuration and actions."""
    with st.sidebar:
        st.title("🤖 Local LLM Chat")
        
        # Configuration
        st.subheader("Configuration")
        provider = os.getenv("LLM_PROVIDER", "openai")
        model_name = os.getenv("MODEL_NAME", "gpt-4o-mini")
        
        st.info(f"**Provider:** {provider}")
        st.info(f"**Model:** {model_name}")
        
        # Status
        st.subheader("Status")
        if st.session_state.llm_client:
            st.success("✅ Local LLM Ready")
        else:
            st.error("❌ Local LLM Not Available")
        
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
    response_text = ""
    async for chunk in st.session_state.llm_client.generate_response(messages):
        response_text += chunk
    
    return response_text

def main():
    """Main Streamlit application."""
    st.title("🤖 Local LLM Chat")
    st.markdown("Chat with your local AI assistant running on your machine.")
    
    # Initialize LLM client if not already done
    if st.session_state.llm_client is None:
        with st.spinner("Initializing LLM client..."):
            st.session_state.llm_client = initialize_llm_client()
    
    # Display sidebar
    display_sidebar()
    
    # Main chat interface
    if not st.session_state.llm_client:
        st.error("❌ Failed to initialize LLM client. Please check your configuration.")
        return
    
    # Display existing messages
    display_chat_messages()
    
    # Chat input
    if prompt := st.chat_input("Ask me anything!"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate and display assistant response with real-time streaming
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            response_text = ""
            
            # Stream the response in real-time
            async def stream_response():
                nonlocal response_text
                async for chunk in st.session_state.llm_client.generate_response(st.session_state.messages):
                    response_text += chunk
                    # Update the display in real-time with each chunk
                    message_placeholder.markdown(response_text + "▌")  # Add cursor for typing effect
                # Remove cursor when complete
                message_placeholder.markdown(response_text)
                return response_text
            
            response = asyncio.run(stream_response())
        
        # Add assistant response to session state
        st.session_state.messages.append({"role": "assistant", "content": response})

    # Example prompts
    st.subheader("💡 Try these examples:")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
         if st.button("💡 List tasks"):
            example_prompt = "List all my pending tasks, grouped by priority level"
            st.session_state.messages.append({"role": "user", "content": example_prompt})
            st.rerun()
       
    
    with col2:
        if st.button("💬 Create task"):
            example_prompt = "Create a high priority task to review the quarterly report with a due date of next Friday"
            st.session_state.messages.append({"role": "user", "content": example_prompt})
            st.rerun()
    
    with col3:
        if st.button("🛠️ Update task"):
            example_prompt = "Update the task 'quarterly report' to change its priority to urgent and extend the due date"
            st.session_state.messages.append({"role": "user", "content": example_prompt})
            st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>🚀 Powered by your Local LLM | 🔒 Privacy-first, runs on your machine</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
