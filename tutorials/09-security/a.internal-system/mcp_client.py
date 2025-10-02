#!/usr/bin/env python3
"""
MCP Client with Keycloak authentication - Streamlit Web Application
"""

import os
import json
import requests
from typing import Dict, Any
from dotenv import load_dotenv
import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta
import time
from libs.mcp_adapter import MCPAdapter

# Load environment variables
load_dotenv()

def get_cookie_manager():
    """Get the cookie manager instance."""
    return stx.CookieManager()

def get_adapter(token: str):
    if "adapter" not in st.session_state:
        adapter = MCPAdapter()
        adapter.connect_to_server(token)
        st.session_state["adapter"] = adapter
    return st.session_state["adapter"]

def generate_tool_parameters(tool_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Generate parameter inputs based on tool schema.
    
    Args:
        tool_schema: The schema definition of the tool
        
    Returns:
        Dict[str, Any]: Dictionary of parameter names and values
    """
    parameters = {}
    
    # Extract parameters from the tool's schema
    if "function" in tool_schema and "parameters" in tool_schema["function"]:
        param_schema = tool_schema["function"]["parameters"]
        if "properties" in param_schema:
            st.subheader("Parameters")
            for param_name, param_info in param_schema["properties"].items():
                param_type = param_info.get("type", "string")
                param_desc = param_info.get("description", "")
                param_required = param_name in param_schema.get("required", [])
                
                # Display parameter description if available
                if param_desc:
                    st.text(f"{param_desc}")
                
                # Label with required indication
                label = f"{param_name}{' *' if param_required else ''}"
                
                # Generate appropriate input element based on parameter type
                if param_type == "string":
                    parameters[param_name] = st.text_input(
                        label, 
                        help="Required" if param_required else "Optional"
                    )
                elif param_type == "number" or param_type == "integer":
                    parameters[param_name] = st.number_input(
                        label,
                        step=1 if param_type == "integer" else 0.1,
                        help="Required" if param_required else "Optional"
                    )
                elif param_type == "boolean":
                    parameters[param_name] = st.checkbox(
                        label, 
                        help="Required" if param_required else "Optional"
                    )
                elif param_type == "array":
                    # For arrays, provide a text input where items can be comma-separated
                    items = st.text_input(
                        f"{label} (comma-separated)", 
                        help="Required" if param_required else "Optional"
                    )
                    if items.strip():
                        parameters[param_name] = items.split(",")
                    else:
                        parameters[param_name] = []
                elif param_type == "object":
                    # For objects, provide a JSON input area
                    json_str = st.text_area(
                        f"{label} (JSON)", 
                        help="Required" if param_required else "Optional"
                    )
                    try:
                        if json_str.strip():
                            parameters[param_name] = json.loads(json_str)
                        else:
                            parameters[param_name] = {}
                    except json.JSONDecodeError:
                        st.error(f"Invalid JSON for parameter {param_name}")
                        parameters[param_name] = {}
                else:
                    # Default to string input for unknown types
                    parameters[param_name] = st.text_input(
                        label, 
                        help="Required" if param_required else "Optional"
                    )
    
    return parameters    


if 'auth_processed' not in st.session_state:
    st.session_state.auth_processed = False

# Set page config
st.set_page_config(
    page_title="MCP Client",
    page_icon="🔐",
    layout="wide"
)


# Initialize cookie manager
cookie_manager = get_cookie_manager()

class StreamlitMCPClient:
    """MCP Client for Keycloak authentication with Streamlit UI."""
    
    def __init__(self):
        """Initialize the MCP client with Keycloak configuration."""
        # Get Keycloak configuration from environment variables
        idp_domain = os.getenv("IDP_DOMAIN", "localhost:8080")
        if not idp_domain.startswith(('http://', 'https://')):
            self.keycloak_url = f"http://{idp_domain}"
        else:
            self.keycloak_url = idp_domain
            
        self.realm = os.getenv("KEYCLOAK_REALM", "internal-system")
        self.client_id = os.getenv("IDP_CLIENT_ID", "internal-system-client")
        self.client_secret = os.getenv("IDP_CLIENT_SECRET")
        self.rbac_proxy_url = os.getenv("RBAC_PROXY_URL", "http://localhost:8081")
        self.mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
        
    def get_oauth_url(self) -> str:
        """Get OAuth authorization URL from RBAC proxy."""
        response = requests.get(f"{self.rbac_proxy_url}/auth/login")
        response.raise_for_status()
        return response.json()["auth_url"]
    
    def decode_token(self, token: str):
        """Decode the Keycloak token to extract user info."""
        if not token:
            return {}
            
        try:
            # Decode token without verification (just to see the claims)
            import jwt
            payload = jwt.decode(token, options={"verify_signature": False})
            # Extract common user info
            return {
                "sub": payload.get("sub"),
                "email": payload.get("email", "Not provided"),
                "name": payload.get("name", payload.get("preferred_username", "Unknown")),
                "username": payload.get("preferred_username", "Unknown"),
                "groups": payload.get("groups", []),
                "realm_roles": payload.get("realm_access", {}).get("roles", []),
                "expires_at": payload.get("exp", 0)
            }
            
        except Exception as e:
           return {}

# Initialize client
client = StreamlitMCPClient()

# Check for OAuth callback
query_params = st.query_params
if "token" in query_params:
    with st.spinner("Processing OAuth callback..."):
        try:
            token = query_params.get("token")    
            user_info = client.decode_token(token)
                
            if user_info:
                st.session_state.auth_token = token
                st.session_state.user_info = user_info
                st.session_state.auth_processed = True
                
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Failed to decode user information from token")
                
        except Exception as e:
             st.error(f"OAuth callback failed: {str(e)}")

# Get token from cookie
token = st.session_state.get("auth_token") or cookie_manager.get("auth_token")
user_info = st.session_state.get("user_info") or client.decode_token(token)

if cookie_manager.get("auth_token") != token:
    expires_in = 900
    if "expires_at" in user_info and user_info["expires_at"] > 0:
        current_time = int(time.time())
        expires_in = max(60, user_info["expires_at"] - current_time)
    
    expiry = datetime.now() + timedelta(seconds=expires_in)
    cookie_manager.set("auth_token", token, expires_at=expiry, key="set_auth_token")
                
# Main content based on authentication state
if token and user_info:
    # User is authenticated
    st.title(f"Welcome, {user_info['name']}!")
    
    # Create tabs for Tools and Resources
    tab1, tab2 = st.tabs(["MCP Tools", "MCP Resources"])

    with tab1:
        # MCP Tool interaction
        st.header("Call MCP Tool")

        adapter = get_adapter(token)
        tools = adapter.list_tools()
        
        # Create a mapping of names to full tool objects
        tool_map = {tool["function"]["name"]: tool for tool in tools}
        tool_names = list(tool_map.keys())
        tool_name = st.selectbox("Select Tool", tool_names)

        # Get the selected tool's schema
        selected_tool = tool_map[tool_name]

        # Generate parameters for the selected tool
        parameters = generate_tool_parameters(selected_tool)
        
        if st.button("Execute"):
            with st.spinner("Calling MCP tool..."):
                try:
                    result = adapter.call_tool(tool_name, parameters)
                    st.success("Tool executed successfully!")
                    st.json(result)
                except Exception as e:
                    st.error(f"Tool call failed: {str(e)}")

    with tab2:
        # MCP Resource interaction
        st.header("Access MCP Resources")
        
        # Define available resources
        resources = [
            "internal://employees",
            "internal://financial",
        ]
        
        resource_uri = st.selectbox("Select Resource", resources)
        
        if st.button("Fetch Resource"):
            with st.spinner("Fetching resource data..."):
                try:
                    resource_data = adapter.read_resource(resource_uri)
                    st.success(f"Resource retrieved successfully: {resource_uri}")
                    st.json(resource_data)
                except Exception as e:
                    st.error(f"Resource fetch failed: {str(e)}")

else:
    # User is not authenticated - Simple and clean approach
    
    # Create a centered column layout
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col2:        
        # Use Streamlit container for card effect
        with st.container():
            st.markdown("<h1 style='text-align: center; font-size: 24px;'>MCP Client Authentication</h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #666; margin-bottom: 20px;'>Sign in securely to access the MCP client</p>", unsafe_allow_html=True)
            
            # Get OAuth URL for the popup
            oauth_url = client.get_oauth_url()
            
            st.markdown(
                f"""
                <div style='text-align: center; margin: 20px 0;'>
                    <a href='{oauth_url}' target='_self'
                    style='
                            background-color: #4CAF50;
                            color: white;
                            padding: 12px 24px;
                            text-align: center;
                            text-decoration: none;
                            display: inline-block;
                            font-size: 16px;
                            margin: 10px 2px;
                            cursor: pointer;
                            border-radius: 4px;
                            border: none;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                            transition: all 0.3s ease;'>
                        <span style="display: flex; align-items: center; justify-content: center; gap: 10px;">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="white">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
                            </svg>
                            Sign in with Keycloak
                        </span>
                    </a>
                </div>
                """,
                unsafe_allow_html=True
            )