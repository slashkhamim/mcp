# Tutorial: Building a Web Scraper MCP Server

Learn how to create an MCP server that provides web scraping capabilities through tools and resources.

## What You'll Build

A web scraper MCP server that provides:
- **Tools**: Fetch web pages, extract data, parse HTML/JSON
- **Resources**: Access cached content and scraping results
- **Prompts**: Generate scraping scripts and data extraction patterns

## Prerequisites

- Python 3.10+
- `uv` package manager
- Basic understanding of HTML and web technologies

## Learning Objectives

By the end of this tutorial, you'll understand:
- How to implement safe web scraping with rate limiting
- HTML parsing and data extraction techniques
- Caching strategies for scraped content
- Error handling for network operations

## Project Structure

```
web-scraper-server/
├── server.py          # Main MCP server
├── scraper.py          # Web scraping utilities
├── parser.py           # HTML/data parsing
├── cache.py            # Caching system
├── test_server.py      # Tests
└── client.py           # Example client
```

## Step 1: Setup

Create a new project:

```bash
uv init web-scraper-server
cd web-scraper-server
uv add "mcp[cli]" "requests" "beautifulsoup4" "lxml" "aiohttp"
```

## Features

- **Rate-limited requests** to respect server resources
- **Multiple parsing strategies** (BeautifulSoup, regex, JSON)
- **Caching system** to avoid redundant requests
- **User-agent rotation** for better compatibility
- **Error handling** for network issues

## Safety Note

⚠️ **Important**: Always respect robots.txt and website terms of service. Implement appropriate delays and rate limiting.
