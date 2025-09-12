#!/usr/bin/env python3
"""
API Integration MCP Server

Provides external API integration capabilities through MCP protocol.
Includes tools for API calls, resources for cached responses, and prompts for integration code.
"""

import json
import os
from typing import Optional, Dict, Any, List
from mcp.server.fastmcp import FastMCP
from api_client import APIClient
from auth_manager import AuthManager
from rate_limiter import RateLimiter

# Create MCP server
mcp = FastMCP("APIIntegration")

# Initialize components
api_client = APIClient()
auth_manager = AuthManager()
rate_limiter = RateLimiter()

# API integration tools
@mcp.tool()
def make_api_request(url: str, method: str = "GET", headers: str = "{}", data: str = "{}", auth_type: str = "none") -> str:
    """Make a generic API request"""
    try:
        # Parse headers and data
        headers_dict = json.loads(headers) if headers else {}
        data_dict = json.loads(data) if data else {}
        
        # Apply authentication
        if auth_type != "none":
            headers_dict = auth_manager.apply_auth(headers_dict, auth_type)
        
        # Check rate limits
        if not rate_limiter.can_make_request(url):
            return f"Rate limit exceeded for {url}. Please wait before making another request."
        
        response = api_client.request(
            method=method.upper(),
            url=url,
            headers=headers_dict,
            data=data_dict if method.upper() in ["POST", "PUT", "PATCH"] else None
        )
        
        return f"API Response from {url}:\nStatus: {response['status_code']}\nData: {json.dumps(response['data'], indent=2)}"
    
    except json.JSONDecodeError:
        return "Error: Headers and data must be valid JSON format"
    except Exception as e:
        return f"Error making API request: {str(e)}"

@mcp.tool()
def github_user_info(username: str) -> str:
    """Get GitHub user information"""
    try:
        url = f"https://api.github.com/users/{username}"
        
        if not rate_limiter.can_make_request(url):
            return "Rate limit exceeded for GitHub API. Please wait."
        
        response = api_client.request("GET", url)
        
        if response["status_code"] == 404:
            return f"GitHub user '{username}' not found"
        
        user_data = response["data"]
        result = f"GitHub User: {user_data.get('name', username)}\n"
        result += f"Bio: {user_data.get('bio', 'No bio available')}\n"
        result += f"Public Repos: {user_data.get('public_repos', 0)}\n"
        result += f"Followers: {user_data.get('followers', 0)}\n"
        result += f"Following: {user_data.get('following', 0)}\n"
        result += f"Profile: {user_data.get('html_url', '')}"
        
        return result
    except Exception as e:
        return f"Error fetching GitHub user info: {str(e)}"

@mcp.tool()
def github_repo_info(owner: str, repo: str) -> str:
    """Get GitHub repository information"""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}"
        
        if not rate_limiter.can_make_request(url):
            return "Rate limit exceeded for GitHub API. Please wait."
        
        response = api_client.request("GET", url)
        
        if response["status_code"] == 404:
            return f"GitHub repository '{owner}/{repo}' not found"
        
        repo_data = response["data"]
        result = f"Repository: {repo_data.get('full_name')}\n"
        result += f"Description: {repo_data.get('description', 'No description')}\n"
        result += f"Language: {repo_data.get('language', 'Unknown')}\n"
        result += f"Stars: {repo_data.get('stargazers_count', 0)}\n"
        result += f"Forks: {repo_data.get('forks_count', 0)}\n"
        result += f"Open Issues: {repo_data.get('open_issues_count', 0)}\n"
        result += f"URL: {repo_data.get('html_url', '')}"
        
        return result
    except Exception as e:
        return f"Error fetching GitHub repo info: {str(e)}"

@mcp.tool()
def weather_info(city: str, api_key: str = None) -> str:
    """Get weather information for a city"""
    try:
        # Use provided API key or environment variable
        key = api_key or os.getenv("OPENWEATHER_API_KEY")
        if not key:
            return "Error: OpenWeather API key required. Set OPENWEATHER_API_KEY environment variable or provide api_key parameter."
        
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric"
        
        if not rate_limiter.can_make_request(url):
            return "Rate limit exceeded for OpenWeather API. Please wait."
        
        response = api_client.request("GET", url)
        
        if response["status_code"] == 404:
            return f"City '{city}' not found"
        
        weather_data = response["data"]
        result = f"Weather in {weather_data.get('name', city)}:\n"
        result += f"Temperature: {weather_data['main']['temp']}°C\n"
        result += f"Feels like: {weather_data['main']['feels_like']}°C\n"
        result += f"Humidity: {weather_data['main']['humidity']}%\n"
        result += f"Description: {weather_data['weather'][0]['description']}\n"
        result += f"Wind Speed: {weather_data.get('wind', {}).get('speed', 'N/A')} m/s"
        
        return result
    except Exception as e:
        return f"Error fetching weather info: {str(e)}"

@mcp.tool()
def test_api_endpoint(url: str) -> str:
    """Test an API endpoint for connectivity and response"""
    try:
        response = api_client.request("GET", url, timeout=5)
        
        result = f"API Endpoint Test: {url}\n"
        result += f"Status Code: {response['status_code']}\n"
        result += f"Response Time: {response.get('response_time', 'N/A')}ms\n"
        result += f"Content Type: {response.get('content_type', 'N/A')}\n"
        
        if response["status_code"] == 200:
            result += "✅ Endpoint is accessible"
        else:
            result += "❌ Endpoint returned error status"
        
        return result
    except Exception as e:
        return f"Error testing API endpoint: {str(e)}"

# API response caching resources
@mcp.resource("api://cache/{encoded_url}")
def get_cached_response(encoded_url: str) -> str:
    """Get cached API response"""
    try:
        import urllib.parse
        url = urllib.parse.unquote(encoded_url)
        
        cached_response = api_client.get_cached_response(url)
        if not cached_response:
            return json.dumps({"error": "No cached response found"})
        
        return json.dumps({
            "url": url,
            "cached_at": cached_response.get("timestamp"),
            "status_code": cached_response.get("status_code"),
            "data": cached_response.get("data")
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource("api://rate-limits")
def get_rate_limit_status() -> str:
    """Get current rate limit status for all APIs"""
    try:
        status = rate_limiter.get_status()
        return json.dumps(status, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

# API integration prompts
@mcp.prompt()
def api_integration_code(api_name: str, endpoint: str, language: str = "python", auth_type: str = "api_key") -> str:
    """Generate API integration code"""
    languages = ["python", "javascript", "curl", "php", "java"]
    auth_types = ["api_key", "bearer_token", "oauth", "basic_auth", "none"]
    
    if language not in languages:
        return f"Unsupported language: {language}. Available: {', '.join(languages)}"
    
    if auth_type not in auth_types:
        return f"Unsupported auth type: {auth_type}. Available: {', '.join(auth_types)}"
    
    return f"""Generate {language} code to integrate with {api_name} API.

Endpoint: {endpoint}
Authentication: {auth_type}
Language: {language}

Please provide:
1. Complete code example with proper error handling
2. Authentication setup and configuration
3. Response parsing and data extraction
4. Rate limiting and retry logic
5. Environment variable usage for sensitive data
6. Unit tests for the integration
7. Documentation and usage examples

Make it production-ready with best practices."""

@mcp.prompt()
def api_documentation(api_responses: str, api_name: str) -> str:
    """Generate API documentation from responses"""
    return f"""Generate comprehensive API documentation for {api_name} based on these sample responses:

Sample Responses:
{api_responses}

Please create documentation including:
1. API overview and purpose
2. Authentication requirements
3. Endpoint descriptions and parameters
4. Request/response examples
5. Error codes and handling
6. Rate limiting information
7. SDK/client library examples
8. Best practices and common patterns

Format as markdown with clear sections and examples."""

@mcp.prompt()
def api_testing_strategy(api_spec: str) -> str:
    """Generate API testing strategy and test cases"""
    return f"""Create a comprehensive testing strategy for this API:

API Specification:
{api_spec}

Please provide:
1. Test case categories (unit, integration, end-to-end)
2. Specific test scenarios for each endpoint
3. Authentication and authorization tests
4. Error handling and edge case tests
5. Performance and load testing approach
6. Mock server setup for development
7. Continuous integration test pipeline
8. Test data management strategy

Include practical examples and tools recommendations."""

if __name__ == "__main__":
    # Run the server
    import asyncio
    mcp.run()
