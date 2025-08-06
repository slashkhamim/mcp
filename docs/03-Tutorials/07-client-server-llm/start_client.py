import asyncio
import streamlit as st
import time
from libs.client import JiraMcpClient

def get_client():
    if "client" not in st.session_state:
        client = JiraMcpClient()
        client.connect_to_server()
        st.session_state["client"] = client
    return st.session_state["client"]

st.set_page_config(page_title="Chat", layout="centered")

st.markdown("""
    <style>
    .chat-container {
        max-width: 500px;
        margin: 0 auto;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
    }
    .chat-header {
        background-color: #075E54;
        color: white;
        padding: 1rem;
        font-weight: bold;
        font-size: 1.2rem;
    }
    .chat-header-divider {
        height: 30px;
    }
    </style>
""", unsafe_allow_html=True)

# --- App Layout ---
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
st.markdown('<div class="chat-header">Streamlit MCP Client Demo</div>', unsafe_allow_html=True)
st.markdown('<div class="chat-header-divider">', unsafe_allow_html=True)


startMessage = ''' 
The client provides natural language interaction:

- **"Create a task to..."** - Creates new tasks
- **"Show me..."** - Lists and filters tasks  
- **"Complete the..."** - Marks tasks as done
- **"Help me plan..."** - Uses prompts for planning
- **"What tasks are due today?"** - Smart filtering
- **"Break down this task..."** - Task decomposition
'''

# --- Chat Memory ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": startMessage}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Input ---
if prompt := st.chat_input("Type a message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        client = get_client()
        result = client.process_prompt(prompt)
        
        for chunk in result.split():
            full_response += chunk + " "
            time.sleep(0.05)
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})

st.markdown('</div></div>', unsafe_allow_html=True)