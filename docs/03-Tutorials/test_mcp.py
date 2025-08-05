"""
Tests for the MCP server demo.
"""

import pytest
from main import mcp  # Import the actual server instance

class TestMCPServerCalls:
    """Test actual MCP server method calls."""
    
    def test_call_add_tool_real(self):
        """Test calling the real add tool through MCP server."""
        # Call the actual MCP server's call_tool method with correct signature
        import asyncio
        result = asyncio.run(mcp.call_tool("add", {"a": 5, "b": 3}))
        
        # Check that we got a result - it's a tuple (content, metadata)
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2
        
        content, metadata = result
        assert len(content) > 0
        # The result should be "8" as text
        assert "8" in str(content[0].text)
        # Check metadata contains the actual result
        assert metadata['result'] == 8
    
    def test_list_tools_real(self):
        """Test listing tools from the real MCP server."""
        # List tools returns a list directly
        import asyncio
        result = asyncio.run(mcp.list_tools())
        
        # Check that we got tools back - it's a list, not an object with .tools
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Should have the "add" tool
        tool_names = [tool.name for tool in result]
        assert "add" in tool_names
    
    def test_read_resource_real(self):
        """Test reading a resource from the real MCP server."""
        # Read resource with correct signature
        import asyncio
        result = asyncio.run(mcp.read_resource("greeting://Alice"))
        
        # Check that we got a resource back - it's a list of contents
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Should contain the greeting
        content_text = result[0].content
        assert "Hello, Alice!" in content_text
    
    def test_list_resources_real(self):
        """Test listing resources from the real MCP server."""
        # List resources returns a list directly
        import asyncio
        result = asyncio.run(mcp.list_resources())
        
        # Check that we got resources back - it's a list, not an object with .resources
        assert result is not None
        assert isinstance(result, list)
        # Note: Resources might be empty for template-based resources
        # This is normal for dynamic resources like "greeting://{name}"
    
    def test_get_prompt_real(self):
        """Test getting a prompt from the real MCP server."""
        # Get prompt with correct signature
        import asyncio
        result = asyncio.run(mcp.get_prompt("greet_user", {"name": "Bob", "style": "friendly"}))
        
        # Check that we got a prompt back
        assert result is not None
        assert hasattr(result, 'messages')
        assert len(result.messages) > 0
        
        # Should contain the expected prompt text
        message = result.messages[0]
        message_text = message.content.text
        assert "warm, friendly greeting" in message_text
        assert "Bob" in message_text
    
    def test_list_prompts_real(self):
        """Test listing prompts from the real MCP server."""
        # List prompts returns a list directly
        import asyncio
        result = asyncio.run(mcp.list_prompts())
        
        # Check that we got prompts back - it's a list, not an object with .prompts
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Should have the "greet_user" prompt
        prompt_names = [prompt.name for prompt in result]
        assert "greet_user" in prompt_names

if __name__ == "__main__":
    pytest.main([__file__])