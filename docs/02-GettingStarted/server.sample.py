from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("MCP_Demo")

# Addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

# User profile resource
@mcp.resource("user://{user_id}")
def get_user_profile(user_id: str) -> str:
    """Get user profile information"""
    # Simulate user data
    users = {
        "alice": {"name": "Alice Johnson", "role": "Developer", "team": "Backend"},
        "bob": {"name": "Bob Smith", "role": "Designer", "team": "Frontend"},
        "charlie": {"name": "Charlie Brown", "role": "Manager", "team": "Product"}
    }
    
    user = users.get(user_id.lower(), {"name": "Unknown User", "role": "Guest", "team": "None"})
    return f"**{user['name']}**\nRole: {user['role']}\nTeam: {user['team']}"

# Code review prompt
@mcp.prompt()
def code_review(language: str, code_type: str = "function") -> str:
    """Generate a code review prompt"""
    return f"Please review this {language} {code_type} and provide feedback on:\n\n1. Code quality and readability\n2. Performance considerations\n3. Security best practices\n4. Potential bugs or issues\n5. Suggestions for improvement\n\nFocus on constructive feedback that helps improve the code."

# Email composition prompt
@mcp.prompt()
def compose_email(purpose: str, tone: str = "professional") -> str:
    """Generate an email composition prompt"""
    tone_styles = {
        "professional": "formal and business-appropriate",
        "friendly": "warm and approachable",
        "urgent": "direct and action-oriented",
        "apologetic": "sincere and understanding"
    }
    
    selected_tone = tone_styles.get(tone, tone_styles["professional"])
    return f"Please help me compose an email for: {purpose}\n\nThe tone should be {selected_tone}. Include:\n- Clear subject line\n- Appropriate greeting\n- Well-structured body\n- Professional closing\n\nMake it concise but complete."