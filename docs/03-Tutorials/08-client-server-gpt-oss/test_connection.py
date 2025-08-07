#!/usr/bin/env python3
"""
Simple test script to verify MCP server connection.
"""
import asyncio
import os
from dotenv import load_dotenv
from libs.local_llm_client import LocalLLMClient

load_dotenv()

async def test_connection():
    """Test connection to MCP server."""
    print("Testing MCP server connection...")
    
    # Initialize client
    provider = os.getenv("LLM_PROVIDER", "ollama")
    model_name = os.getenv("MODEL_NAME", "llama2:7b")
    mcp_server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
    
    print(f"Provider: {provider}")
    print(f"Model: {model_name}")
    print(f"MCP Server URL: {mcp_server_url}")
    
    try:
        client = LocalLLMClient(
            provider=provider,
            model_name=model_name,
            mcp_server_url=mcp_server_url
        )
        
        # Test connection
        success = await client.connect_to_mcp_server()
        
        if success:
            print("\n✅ Connection successful!")
            print(f"Tools discovered: {len(client.get_available_tools())}")
            print(f"Resources discovered: {len(client.get_available_resources())}")
            print(f"Prompts discovered: {len(client.get_available_prompts())}")
            
            # List tools
            print("\nAvailable tools:")
            for tool in client.get_available_tools():
                print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
                
        else:
            print("\n❌ Connection failed!")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
