#!/bin/bash
# Start Internal System MCP Server

echo "Starting Internal System MCP Server..."

# Install dependencies with uv
echo "Installing dependencies..."
uv sync

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | xargs)
else
    echo "Warning: .env file not found"
fi

# Start RBAC Proxy in background
echo "Starting RBAC Proxy..."
uv run python rbac_proxy.py &
PROXY_PID=$!

# Wait for proxy to start
sleep 3

# Start MCP Server
echo "Starting MCP Server..."
uv run python mcp_server.py

# Cleanup
kill $PROXY_PID 2>/dev/null
