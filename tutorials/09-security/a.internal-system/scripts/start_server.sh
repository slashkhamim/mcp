#!/bin/bash
# Start Internal System MCP Server

echo "Starting Internal System MCP Server..."

# Create process ID directory if it doesn't exist
mkdir -p .pid

# Create logs directory if it doesn't exist
mkdir -p logs

# Install dependencies with uv
echo "Installing dependencies..."
uv sync

# Check environment variables
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found"
fi

# Start RBAC Proxy in background with nohup
echo "Starting RBAC Proxy..."
nohup uv run python rbac_proxy.py > logs/proxy.log 2>&1 &
PROXY_PID=$!
echo $PROXY_PID > .pid/proxy.pid
echo "RBAC Proxy started with PID: $PROXY_PID (logs: logs/proxy.log)"

# Wait for proxy to start
sleep 3

# Start MCP Server in background with nohup
echo "Starting MCP Server..."
nohup uv run python mcp_server.py > logs/server.log 2>&1 &
SERVER_PID=$!
echo $SERVER_PID > .pid/server.pid
echo "MCP Server started with PID: $SERVER_PID (logs: logs/server.log)"

# Wait for server to initialize
sleep 3

# Start MCP Client in background with nohup
echo "Starting MCP Client..."
nohup uv run streamlit run mcp_client.py > logs/client.log 2>&1 &
CLIENT_PID=$!
echo $CLIENT_PID > .pid/client.pid
echo "MCP Client started with PID: $CLIENT_PID (logs: logs/client.log)"

# Disown all background jobs to detach from shell
disown -a

echo ""
echo "All services started successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Process IDs:"
echo "  - RBAC Proxy: $PROXY_PID"
echo "  - MCP Server: $SERVER_PID"
echo "  - MCP Client: $CLIENT_PID"
echo ""
echo "Log files:"
echo "  - RBAC Proxy: logs/proxy.log"
echo "  - MCP Server: logs/server.log"
echo "  - MCP Client: logs/client.log"
echo ""
echo "To stop all services, run ./scripts/stop_server.sh"
echo "To view logs: tail -f logs/*.log"