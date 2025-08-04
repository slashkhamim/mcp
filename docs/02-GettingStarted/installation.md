---
title: Installation
sidebar_position: 2
---

# Installation Guide

This guide covers installing MCP SDKs, tools, and setting up your development environment.

## System Requirements

### Minimum Requirements
- **Node.js**: 18.0+ (for JavaScript/TypeScript implementations)
- **Python**: 3.8+ (for Python implementations)
- **Memory**: 512MB RAM minimum
- **Storage**: 100MB free space

### Recommended Requirements
- **Node.js**: 20.0+ LTS
- **Python**: 3.11+
- **Memory**: 2GB RAM
- **Storage**: 1GB free space

## JavaScript/TypeScript Installation

### Using npm

```bash
# Install the core MCP SDK
npm install @modelcontextprotocol/sdk

# Install additional utilities
npm install @modelcontextprotocol/server-stdio
npm install @modelcontextprotocol/client-stdio
```

### Using yarn

```bash
# Install the core MCP SDK
yarn add @modelcontextprotocol/sdk

# Install additional utilities
yarn add @modelcontextprotocol/server-stdio
yarn add @modelcontextprotocol/client-stdio
```

### Using pnpm

```bash
# Install the core MCP SDK
pnpm add @modelcontextprotocol/sdk

# Install additional utilities
pnpm add @modelcontextprotocol/server-stdio
pnpm add @modelcontextprotocol/client-stdio
```

### Development Dependencies

For development, you may also want:

```bash
npm install --save-dev @types/node typescript ts-node
```

## Python Installation

### Using pip

```bash
# Install the core MCP package
pip install mcp

# Install with optional dependencies
pip install mcp[server]
pip install mcp[client]
pip install mcp[all]
```

### Using conda

```bash
# Install from conda-forge
conda install -c conda-forge mcp
```

### Using Poetry

```bash
# Add to your project
poetry add mcp

# With optional dependencies
poetry add mcp[server,client]
```

### Virtual Environment Setup

```bash
# Create virtual environment
python -m venv mcp-env

# Activate (Linux/Mac)
source mcp-env/bin/activate

# Activate (Windows)
mcp-env\Scripts\activate

# Install MCP
pip install mcp
```

## Docker Installation

### Official Images

```bash
# Pull the latest MCP server image
docker pull mcpprotocol/server:latest

# Pull specific version
docker pull mcpprotocol/server:1.0.0

# Pull development image
docker pull mcpprotocol/server:dev
```

### Running with Docker

```bash
# Run a basic MCP server
docker run -p 3000:3000 mcpprotocol/server:latest

# Run with volume mounting
docker run -v /path/to/data:/app/data mcpprotocol/server:latest

# Run with environment variables
docker run -e MCP_PORT=3000 -e MCP_HOST=0.0.0.0 mcpprotocol/server:latest
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  mcp-server:
    image: mcpprotocol/server:latest
    ports:
      - "3000:3000"
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    environment:
      - MCP_PORT=3000
      - MCP_HOST=0.0.0.0
      - MCP_LOG_LEVEL=info
    restart: unless-stopped

  mcp-client:
    image: mcpprotocol/client:latest
    depends_on:
      - mcp-server
    environment:
      - MCP_SERVER_URL=http://mcp-server:3000
```

## Binary Releases

### Download Pre-built Binaries

Visit the [MCP Releases](https://github.com/modelcontextprotocol/mcp/releases) page to download pre-built binaries:

#### Linux
```bash
# Download and install
wget https://github.com/modelcontextprotocol/mcp/releases/latest/download/mcp-linux-amd64.tar.gz
tar -xzf mcp-linux-amd64.tar.gz
sudo mv mcp /usr/local/bin/
```

#### macOS
```bash
# Download and install
curl -L https://github.com/modelcontextprotocol/mcp/releases/latest/download/mcp-darwin-amd64.tar.gz | tar -xz
sudo mv mcp /usr/local/bin/
```

#### Windows
```powershell
# Download using PowerShell
Invoke-WebRequest -Uri "https://github.com/modelcontextprotocol/mcp/releases/latest/download/mcp-windows-amd64.zip" -OutFile "mcp.zip"
Expand-Archive -Path "mcp.zip" -DestinationPath "C:\Program Files\MCP"
```

## Package Managers

### Homebrew (macOS/Linux)

```bash
# Add the MCP tap
brew tap modelcontextprotocol/mcp

# Install MCP
brew install mcp

# Install specific components
brew install mcp-server
brew install mcp-client
```

### Chocolatey (Windows)

```powershell
# Install MCP
choco install mcp

# Install specific components
choco install mcp-server
choco install mcp-client
```

### Snap (Linux)

```bash
# Install from Snap Store
sudo snap install mcp

# Install with specific channel
sudo snap install mcp --channel=stable
sudo snap install mcp --channel=edge
```

## Development Setup

### Clone the Repository

```bash
# Clone the main repository
git clone https://github.com/modelcontextprotocol/mcp.git
cd mcp

# Install dependencies
npm install

# Build the project
npm run build
```

### Development Environment

```bash
# Install development tools
npm install -g typescript ts-node nodemon

# For Python development
pip install black flake8 mypy pytest
```

### IDE Setup

#### Visual Studio Code

Install recommended extensions:

```json
{
  "recommendations": [
    "ms-vscode.vscode-typescript-next",
    "ms-python.python",
    "ms-vscode.vscode-json",
    "redhat.vscode-yaml"
  ]
}
```

#### Settings

```json
{
  "typescript.preferences.importModuleSpecifier": "relative",
  "python.defaultInterpreterPath": "./venv/bin/python",
  "editor.formatOnSave": true
}
```

## Verification

### Test Installation

#### JavaScript/TypeScript

```javascript
// test-installation.js
import { Server } from '@modelcontextprotocol/sdk/server/index.js';

console.log('MCP SDK installed successfully!');
console.log('Server class:', Server.name);
```

```bash
node test-installation.js
```

#### Python

```python
# test_installation.py
import mcp

print("MCP installed successfully!")
print(f"MCP version: {mcp.__version__}")
```

```bash
python test_installation.py
```

### Version Check

```bash
# Check installed versions
npm list @modelcontextprotocol/sdk
pip show mcp

# Check binary version
mcp --version
```

## Troubleshooting

### Common Issues

#### Node.js Version Conflicts

```bash
# Use nvm to manage Node.js versions
nvm install 20
nvm use 20
npm install @modelcontextprotocol/sdk
```

#### Python Path Issues

```bash
# Verify Python installation
which python3
python3 --version

# Use specific Python version
python3.11 -m pip install mcp
```

#### Permission Errors

```bash
# Linux/Mac: Use sudo for global installation
sudo npm install -g @modelcontextprotocol/cli

# Or use user directory
npm install --prefix ~/.local @modelcontextprotocol/cli
```

#### Network Issues

```bash
# Configure npm registry
npm config set registry https://registry.npmjs.org/

# Configure pip index
pip install --index-url https://pypi.org/simple/ mcp
```

### Getting Help

If you encounter issues:

1. **Check the logs**: Enable debug logging
2. **Search issues**: Check [GitHub Issues](https://github.com/modelcontextprotocol/mcp/issues)
3. **Ask for help**: Join our [Discord community](https://discord.gg/mcp)
4. **Report bugs**: Create a new issue with reproduction steps

## Next Steps

After installation:

1. **[Quick Start](/docs/02-GettingStarted/quickstart)**: Create your first MCP server
2. **[Core Concepts](/docs/01-CoreConcepts/overview)**: Understand MCP architecture
3. **[Examples](/docs/Appendix/examples)**: Explore sample implementations

## Updates and Maintenance

### Staying Updated

```bash
# Check for updates
npm outdated @modelcontextprotocol/sdk
pip list --outdated | grep mcp

# Update to latest version
npm update @modelcontextprotocol/sdk
pip install --upgrade mcp
```

### Release Channels

- **Stable**: Production-ready releases
- **Beta**: Pre-release versions with new features
- **Nightly**: Daily builds with latest changes

```bash
# Install beta version
npm install @modelcontextprotocol/sdk@beta
pip install mcp --pre
```
