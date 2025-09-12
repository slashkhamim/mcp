#!/usr/bin/env python3
"""
Chatbot MCP Server

Provides AI chatbot capabilities through MCP protocol.
Includes tools for conversations, resources for chat history, and prompts for personality creation.
"""

import json
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from chatbot import ChatbotManager
from conversation import ConversationManager
from personality import PersonalityManager

# Create MCP server
mcp = FastMCP("Chatbot")

# Initialize components
chatbot_manager = ChatbotManager()
conversation_manager = ConversationManager()
personality_manager = PersonalityManager()

# Chatbot interaction tools
@mcp.tool()
def send_message(message: str, conversation_id: str = "default", personality: str = "assistant") -> str:
    """Send a message to the chatbot and get a response"""
    try:
        # Get or create conversation
        conversation = conversation_manager.get_conversation(conversation_id)
        
        # Add user message to conversation
        conversation_manager.add_message(conversation_id, "user", message)
        
        # Get chatbot response
        response = chatbot_manager.generate_response(
            message=message,
            conversation_history=conversation["messages"],
            personality=personality
        )
        
        # Add bot response to conversation
        conversation_manager.add_message(conversation_id, "assistant", response["content"])
        
        # Return response with metadata
        result = f"Chatbot Response:\n{response['content']}\n\n"
        result += f"Tokens used: {response.get('tokens_used', 'N/A')}\n"
        result += f"Model: {response.get('model', 'N/A')}\n"
        result += f"Cost estimate: ${response.get('cost_estimate', 0):.4f}"
        
        return result
    except Exception as e:
        return f"Error generating response: {str(e)}"

@mcp.tool()
def create_conversation(conversation_id: str, title: str = "", personality: str = "assistant") -> str:
    """Create a new conversation with specified settings"""
    try:
        conversation = conversation_manager.create_conversation(
            conversation_id=conversation_id,
            title=title,
            personality=personality
        )
        
        return f"Created conversation '{conversation_id}' with personality '{personality}'"
    except Exception as e:
        return f"Error creating conversation: {str(e)}"

@mcp.tool()
def list_conversations() -> str:
    """List all available conversations"""
    try:
        conversations = conversation_manager.list_conversations()
        
        if not conversations:
            return "No conversations found"
        
        result = f"Found {len(conversations)} conversation(s):\n"
        for conv in conversations:
            result += f"• {conv['id']}: {conv['title']} ({conv['message_count']} messages)\n"
            result += f"  Created: {conv['created_at']}, Last: {conv['last_message_at']}\n"
        
        return result
    except Exception as e:
        return f"Error listing conversations: {str(e)}"

@mcp.tool()
def delete_conversation(conversation_id: str) -> str:
    """Delete a conversation and its history"""
    try:
        conversation_manager.delete_conversation(conversation_id)
        return f"Deleted conversation '{conversation_id}'"
    except Exception as e:
        return f"Error deleting conversation: {str(e)}"

@mcp.tool()
def create_personality(name: str, description: str, system_prompt: str, temperature: float = 0.7) -> str:
    """Create a new chatbot personality"""
    try:
        personality = personality_manager.create_personality(
            name=name,
            description=description,
            system_prompt=system_prompt,
            temperature=temperature
        )
        
        return f"Created personality '{name}': {description}"
    except Exception as e:
        return f"Error creating personality: {str(e)}"

@mcp.tool()
def list_personalities() -> str:
    """List all available chatbot personalities"""
    try:
        personalities = personality_manager.list_personalities()
        
        result = f"Available personalities ({len(personalities)}):\n"
        for personality in personalities:
            result += f"• {personality['name']}: {personality['description']}\n"
            result += f"  Temperature: {personality['temperature']}\n"
        
        return result
    except Exception as e:
        return f"Error listing personalities: {str(e)}"

@mcp.tool()
def get_usage_stats(conversation_id: str = None) -> str:
    """Get token usage and cost statistics"""
    try:
        stats = chatbot_manager.get_usage_stats(conversation_id)
        
        result = "Usage Statistics:\n"
        result += f"Total tokens: {stats['total_tokens']}\n"
        result += f"Total cost: ${stats['total_cost']:.4f}\n"
        result += f"Messages sent: {stats['message_count']}\n"
        result += f"Average tokens per message: {stats['avg_tokens_per_message']:.1f}\n"
        
        if conversation_id:
            result += f"\nFor conversation '{conversation_id}'"
        
        return result
    except Exception as e:
        return f"Error getting usage stats: {str(e)}"

# Conversation history resources
@mcp.resource("chat://conversation/{conversation_id}")
def get_conversation_history(conversation_id: str) -> str:
    """Get full conversation history"""
    try:
        conversation = conversation_manager.get_conversation(conversation_id)
        
        if not conversation:
            return json.dumps({"error": "Conversation not found"})
        
        return json.dumps({
            "conversation_id": conversation_id,
            "title": conversation["title"],
            "personality": conversation["personality"],
            "created_at": conversation["created_at"],
            "message_count": len(conversation["messages"]),
            "messages": conversation["messages"]
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource("chat://personalities")
def get_all_personalities() -> str:
    """Get all chatbot personalities with their configurations"""
    try:
        personalities = personality_manager.get_all_personalities()
        return json.dumps(personalities, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource("chat://stats")
def get_global_stats() -> str:
    """Get global chatbot usage statistics"""
    try:
        stats = chatbot_manager.get_global_stats()
        return json.dumps(stats, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

# Chatbot personality prompts
@mcp.prompt()
def create_personality_prompt(role: str, traits: str, expertise: str = "", style: str = "helpful") -> str:
    """Generate a system prompt for a chatbot personality"""
    styles = ["helpful", "creative", "analytical", "casual", "professional", "humorous"]
    
    if style not in styles:
        return f"Unknown style: {style}. Available: {', '.join(styles)}"
    
    return f"""Create a comprehensive system prompt for a chatbot with these characteristics:

Role: {role}
Personality Traits: {traits}
Expertise Areas: {expertise}
Communication Style: {style}

The system prompt should include:
1. Clear role definition and purpose
2. Personality traits and behavioral guidelines
3. Communication style and tone instructions
4. Areas of expertise and knowledge focus
5. Response format preferences
6. Interaction boundaries and limitations
7. Examples of appropriate responses

Make it detailed enough to create consistent, engaging interactions while maintaining the specified personality."""

@mcp.prompt()
def conversation_starter(topic: str, personality: str = "assistant", audience: str = "general") -> str:
    """Generate conversation starters for a specific topic"""
    return f"""Generate engaging conversation starters for the topic: {topic}

Personality: {personality}
Target Audience: {audience}

Please provide:
1. 5-7 different conversation starter options
2. Variety in approach (questions, statements, scenarios)
3. Appropriate tone for the personality and audience
4. Follow-up questions to keep conversation flowing
5. Context-setting information if needed

Topic: {topic}
Make them natural, engaging, and likely to lead to meaningful conversations."""

@mcp.prompt()
def improve_conversation(conversation_history: str, issue: str) -> str:
    """Generate suggestions to improve a conversation"""
    issues = [
        "repetitive_responses", "off_topic", "too_formal", "too_casual",
        "lack_of_engagement", "unclear_responses", "too_long", "too_short"
    ]
    
    return f"""Analyze this conversation and provide improvement suggestions:

Conversation History:
{conversation_history}

Identified Issue: {issue}

Please provide:
1. Analysis of the current conversation flow
2. Specific problems and their causes
3. Concrete improvement suggestions
4. Alternative response examples
5. Personality adjustments if needed
6. Conversation recovery strategies
7. Prevention tips for future interactions

Focus on actionable advice that will immediately improve the conversation quality."""

if __name__ == "__main__":
    # Run the server
    import asyncio
    mcp.run()
