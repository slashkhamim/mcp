#!/bin/bash
# Stop all running MCP services

echo "Stopping all MCP services..."

# Check if PID directory exists
if [ ! -d ".pid" ]; then
    echo "Error: PID directory not found. Services may not be running."
    exit 1
fi

# Function to stop a service
stop_service() {
    local pid_file=".pid/$1.pid"
    local service_name=$2
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null; then
            echo "Stopping $service_name (PID: $pid)..."
            kill "$pid"
            sleep 1
            # Check if process still exists
            if ps -p "$pid" > /dev/null; then
                echo "Process still running, forcing termination..."
                kill -9 "$pid" 2>/dev/null
            fi
            echo "$service_name stopped"
        else
            echo "$service_name (PID: $pid) is not running"
        fi
        rm -f "$pid_file"
    else
        echo "No PID file found for $service_name"
    fi
}

# Stop services in reverse order
stop_service "client" "MCP Client"
stop_service "server" "MCP Server"
stop_service "proxy" "RBAC Proxy"

echo "All services have been stopped"

# Clean up PID directory if empty
if [ -z "$(ls -A .pid 2>/dev/null)" ]; then
    rmdir .pid
fi
