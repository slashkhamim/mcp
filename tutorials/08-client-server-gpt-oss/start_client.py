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
import time
import re

from libs.local_llm_client import LocalLLMClient

# Load environment variables
load_dotenv()

def render_math_content(content: str) -> str:
    """Process content to convert LaTeX expressions to more readable format."""
    # Convert common LaTeX expressions to more readable format
    
    # Replace \text{...} with regular text
    content = re.sub(r'\\text\{([^}]+)\}', r'\1', content)
    
    # Replace \times with ×
    content = content.replace(r'\times', '×')
    
    # Replace \frac{a}{b} with a/b for simple fractions
    content = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', content)
    
    # Replace common math symbols
    content = content.replace(r'\cdot', '·')
    content = content.replace(r'\div', '÷')
    content = content.replace(r'\pm', '±')
    content = content.replace(r'\approx', '≈')
    content = content.replace(r'\neq', '≠')
    content = content.replace(r'\leq', '≤')
    content = content.replace(r'\geq', '≥')
    
    return content

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
            rendered_content = render_math_content(message["content"])
            st.markdown(rendered_content, unsafe_allow_html=True)

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
            # Create separate containers for content and timer
            content_container = st.empty()
            timer_container = st.empty()
            response_text = ""
            
            # Start timing the response
            start_time = time.time()
            
            # Show initial thinking message
            content_container.markdown("🤔 *Thinking...*")
            
            # Stream the response in real-time
            async def stream_response():
                nonlocal response_text
                first_chunk = True
                
                # Start timer display
                async def update_timer():
                    while True:
                        current_time = time.time()
                        elapsed_time = current_time - start_time
                        timer_container.markdown(f"*⏱️ {elapsed_time:.1f}s*")
                        await asyncio.sleep(0.5)  # Update timer every 500ms
                
                timer_task = asyncio.create_task(update_timer())
                
                try:
                    async for chunk in st.session_state.llm_client.generate_response(st.session_state.messages):
                        if first_chunk:
                            # Clear the thinking message when first chunk arrives
                            first_chunk = False
                        
                        response_text += chunk
                        
                        # Update only the content, timer updates separately
                        content_with_cursor = f"{response_text}▌"
                        rendered_content = render_math_content(content_with_cursor)
                        content_container.markdown(rendered_content, unsafe_allow_html=True)
                    
                    # Stop the timer
                    timer_task.cancel()
                    
                    # Calculate final response time
                    end_time = time.time()
                    response_time = end_time - start_time
                    
                    # Show final content without cursor
                    final_content = render_math_content(response_text)
                    content_container.markdown(final_content, unsafe_allow_html=True)
                    
                    # Show final timing info in timer container
                    timer_container.markdown(f"*⏱️ Response completed in {response_time:.2f} seconds*")
                    
                    # Create final content with timing for storage
                    final_content_with_timing = f"{response_text}\n\n---\n*⏱️ Response completed in {response_time:.2f} seconds*"
                    
                    return response_text, final_content_with_timing
                    
                except asyncio.CancelledError:
                    timer_task.cancel()
                    raise
            
            response_data = asyncio.run(stream_response())
            response_text, final_content_with_timing = response_data
        
        # Add assistant response to session state with timing information
        st.session_state.messages.append({"role": "assistant", "content": final_content_with_timing})

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
