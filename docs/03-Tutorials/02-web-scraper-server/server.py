#!/usr/bin/env python3
"""
Web Scraper MCP Server

Provides web scraping capabilities through MCP protocol.
Includes tools for fetching/parsing, resources for cached content, and prompts for automation.
"""

import json
import time
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlparse
from mcp.server.fastmcp import FastMCP
from scraper import WebScraper
from parser import ContentParser
from cache import CacheManager

# Create MCP server
mcp = FastMCP("WebScraper")

# Initialize components
scraper = WebScraper()
parser = ContentParser()
cache = CacheManager()

# Web scraping tools
@mcp.tool()
def fetch_url(url: str, use_cache: bool = True, timeout: int = 10) -> str:
    """Fetch content from a URL"""
    try:
        if use_cache and cache.has_cached(url):
            return f"Cached content for {url}:\n{cache.get_cached(url)}"
        
        content = scraper.fetch(url, timeout=timeout)
        
        if use_cache:
            cache.store(url, content)
        
        return f"Fetched content from {url}:\n{content[:1000]}..."
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

@mcp.tool()
def extract_links(url: str, filter_domain: bool = True) -> str:
    """Extract all links from a webpage"""
    try:
        content = scraper.fetch(url)
        links = parser.extract_links(content, base_url=url)
        
        if filter_domain:
            domain = urlparse(url).netloc
            links = [link for link in links if urlparse(link).netloc == domain]
        
        result = f"Found {len(links)} links on {url}:\n"
        for i, link in enumerate(links[:20], 1):  # Limit to first 20
            result += f"{i}. {link}\n"
        
        if len(links) > 20:
            result += f"... and {len(links) - 20} more links"
        
        return result
    except Exception as e:
        return f"Error extracting links: {str(e)}"

@mcp.tool()
def extract_text(url: str, selector: str = None) -> str:
    """Extract text content from a webpage"""
    try:
        content = scraper.fetch(url)
        
        if selector:
            text = parser.extract_by_selector(content, selector)
        else:
            text = parser.extract_text(content)
        
        return f"Extracted text from {url}:\n{text[:2000]}..."
    except Exception as e:
        return f"Error extracting text: {str(e)}"

@mcp.tool()
def extract_data(url: str, selectors: str) -> str:
    """Extract structured data using CSS selectors (JSON format)"""
    try:
        # Parse selectors JSON
        selector_dict = json.loads(selectors)
        
        content = scraper.fetch(url)
        data = parser.extract_structured_data(content, selector_dict)
        
        return f"Extracted data from {url}:\n{json.dumps(data, indent=2)}"
    except json.JSONDecodeError:
        return "Error: selectors must be valid JSON format"
    except Exception as e:
        return f"Error extracting data: {str(e)}"

@mcp.tool()
def parse_table(url: str, table_index: int = 0) -> str:
    """Extract table data from a webpage"""
    try:
        content = scraper.fetch(url)
        tables = parser.extract_tables(content)
        
        if not tables:
            return f"No tables found on {url}"
        
        if table_index >= len(tables):
            return f"Table index {table_index} not found. Available tables: 0-{len(tables)-1}"
        
        table_data = tables[table_index]
        return f"Table {table_index} from {url}:\n{json.dumps(table_data, indent=2)}"
    except Exception as e:
        return f"Error parsing table: {str(e)}"

@mcp.tool()
def check_robots_txt(url: str) -> str:
    """Check robots.txt for a domain"""
    try:
        domain = urlparse(url).netloc
        robots_url = f"http://{domain}/robots.txt"
        
        robots_content = scraper.fetch(robots_url)
        return f"Robots.txt for {domain}:\n{robots_content}"
    except Exception as e:
        return f"Error checking robots.txt: {str(e)}"

# Cached content resources
@mcp.resource("cache://url/{encoded_url}")
def get_cached_content(encoded_url: str) -> str:
    """Get cached content for a URL"""
    try:
        import urllib.parse
        url = urllib.parse.unquote(encoded_url)
        
        if not cache.has_cached(url):
            return json.dumps({"error": "URL not in cache"})
        
        content = cache.get_cached(url)
        metadata = cache.get_metadata(url)
        
        return json.dumps({
            "url": url,
            "content": content,
            "cached_at": metadata.get("timestamp"),
            "size": len(content)
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource("cache://list")
def list_cached_urls() -> str:
    """List all cached URLs"""
    try:
        cached_urls = cache.list_cached()
        
        result = {
            "cached_urls": [],
            "total_count": len(cached_urls)
        }
        
        for url in cached_urls:
            metadata = cache.get_metadata(url)
            result["cached_urls"].append({
                "url": url,
                "cached_at": metadata.get("timestamp"),
                "size": metadata.get("size", 0)
            })
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

# Scraping automation prompts
@mcp.prompt()
def scraping_script(target_site: str, data_type: str, language: str = "python") -> str:
    """Generate a web scraping script"""
    data_types = {
        "product_listings": "product information (name, price, description)",
        "news_articles": "news articles (title, content, date, author)",
        "contact_info": "contact information (email, phone, address)",
        "social_media": "social media posts (content, author, date)",
        "job_listings": "job postings (title, company, description, requirements)"
    }
    
    if data_type not in data_types:
        available = ", ".join(data_types.keys())
        return f"Unknown data type: {data_type}. Available types: {available}"
    
    description = data_types[data_type]
    
    return f"""Generate a {language} web scraping script for {target_site} to extract {description}.

Requirements:
- Respect robots.txt and rate limits
- Include error handling and retries
- Use appropriate selectors for data extraction
- Implement caching to avoid redundant requests
- Add logging for monitoring
- Handle pagination if applicable
- Export data to JSON/CSV format

Target Site: {target_site}
Data Type: {data_type} ({description})
Language: {language}

Please provide a complete, production-ready script with comments."""

@mcp.prompt()
def data_extraction_pattern(html_sample: str, target_data: str) -> str:
    """Generate CSS selectors for data extraction"""
    return f"""Analyze this HTML sample and create CSS selectors to extract: {target_data}

HTML Sample:
{html_sample[:1000]}...

Please provide:
1. CSS selectors for each data field
2. Alternative selectors as fallbacks
3. Data cleaning/processing steps needed
4. Potential issues and solutions
5. JSON structure for the extracted data

Target Data: {target_data}

Format the response as a structured guide with examples."""

@mcp.prompt()
def scraping_ethics(website: str) -> str:
    """Generate ethical scraping guidelines for a website"""
    return f"""Create ethical web scraping guidelines for: {website}

Please research and provide:
1. robots.txt analysis and compliance
2. Terms of service considerations
3. Recommended request frequency and delays
4. Data usage and storage guidelines
5. Legal considerations and best practices
6. Alternative APIs or data sources if available

Website: {website}

Focus on responsible and legal data collection practices."""

if __name__ == "__main__":
    # Run the server
    import asyncio
    mcp.run()
