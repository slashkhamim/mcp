---
title: Quick Start Guide
sidebar_position: 1
---

# Quick Start Guide

Get up and running with MCP in just a few minutes. This guide will walk you through setting up your first MCP connection and accessing external resources.

## Prerequisites

Before you begin, ensure you have:

- **Node.js 18+** or **Python 3.8+** (depending on your implementation)
- **Basic understanding** of JSON and REST APIs
- **Access to a data source** you want to connect (file system, database, etc.)

## Installation

### Using npm (Node.js)

```bash
npm install @modelcontextprotocol/sdk
```

### Using pip (Python)

```bash
pip install mcp
```

### Using Docker

```bash
docker pull mcpprotocol/server:latest
```

## Your First MCP Server

Let's create a simple file system server that exposes local files to AI assistants.

### Step 1: Create a Basic Server

```javascript
// server.js
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { ListResourcesRequestSchema, ReadResourceRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import fs from 'fs/promises';
import path from 'path';

class FileSystemServer {
  constructor(rootPath) {
    this.rootPath = path.resolve(rootPath);
    this.server = new Server(
      {
        name: "filesystem-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          resources: {},
        },
      }
    );

    this.setupHandlers();
  }

  setupHandlers() {
    // List available resources
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => {
      const files = await this.scanDirectory(this.rootPath);
      return {
        resources: files.map(file => ({
          uri: `file://${file}`,
          name: path.basename(file),
          description: `File: ${path.relative(this.rootPath, file)}`,
          mimeType: this.getMimeType(file)
        }))
      };
    });

    // Read resource content
    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const url = new URL(request.params.uri);
      const filePath = url.pathname;
      
      if (!filePath.startsWith(this.rootPath)) {
        throw new Error("Access denied: Path outside root directory");
      }

      const content = await fs.readFile(filePath, 'utf-8');
      return {
        contents: [{
          uri: request.params.uri,
          mimeType: this.getMimeType(filePath),
          text: content
        }]
      };
    });
  }

  async scanDirectory(dir) {
    const files = [];
    const entries = await fs.readdir(dir, { withFileTypes: true });
    
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isFile()) {
        files.push(fullPath);
      } else if (entry.isDirectory()) {
        files.push(...await this.scanDirectory(fullPath));
      }
    }
    
    return files;
  }

  getMimeType(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    const mimeTypes = {
      '.txt': 'text/plain',
      '.md': 'text/markdown',
      '.js': 'text/javascript',
      '.json': 'application/json',
      '.html': 'text/html',
      '.css': 'text/css'
    };
    return mimeTypes[ext] || 'text/plain';
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
  }
}

// Start the server
const server = new FileSystemServer(process.argv[2] || './docs');
server.run().catch(console.error);
```

### Step 2: Test Your Server

```bash
# Start the server
node server.js ./my-documents

# The server will start and wait for MCP client connections
```

## Connecting with an AI Assistant

### Using Claude Desktop

1. **Install Claude Desktop** from [claude.ai](https://claude.ai/download)

2. **Configure MCP Server** in Claude's settings:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "node",
      "args": ["path/to/your/server.js", "./my-documents"]
    }
  }
}
```

3. **Restart Claude Desktop** to load the new server

4. **Test the connection** by asking Claude:
   > "What files do you have access to?"

### Using the MCP Client SDK

```javascript
// client.js
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

async function connectToServer() {
  const transport = new StdioClientTransport({
    command: 'node',
    args: ['server.js', './my-documents']
  });

  const client = new Client(
    {
      name: "example-client",
      version: "1.0.0",
    },
    {
      capabilities: {}
    }
  );

  await client.connect(transport);

  // List available resources
  const resources = await client.request(
    { method: "resources/list" },
    ListResourcesRequestSchema
  );

  console.log("Available resources:", resources.resources);

  // Read a specific resource
  if (resources.resources.length > 0) {
    const content = await client.request(
      { 
        method: "resources/read",
        params: { uri: resources.resources[0].uri }
      },
      ReadResourceRequestSchema
    );

    console.log("Resource content:", content.contents[0].text);
  }

  await client.close();
}

connectToServer().catch(console.error);
```

## Adding Tools

Let's extend our server to include executable tools:

```javascript
// Add to your server class
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

setupToolHandlers() {
  // List available tools
  this.server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
      tools: [
        {
          name: "create_file",
          description: "Create a new file with specified content",
          inputSchema: {
            type: "object",
            properties: {
              path: {
                type: "string",
                description: "File path relative to root directory"
              },
              content: {
                type: "string",
                description: "File content"
              }
            },
            required: ["path", "content"]
          }
        },
        {
          name: "search_files",
          description: "Search for text within files",
          inputSchema: {
            type: "object",
            properties: {
              query: {
                type: "string",
                description: "Search query"
              }
            },
            required: ["query"]
          }
        }
      ]
    };
  });

  // Execute tools
  this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    switch (name) {
      case "create_file":
        return await this.createFile(args.path, args.content);
      
      case "search_files":
        return await this.searchFiles(args.query);
      
      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  });
}

async createFile(relativePath, content) {
  const fullPath = path.join(this.rootPath, relativePath);
  
  // Security check
  if (!fullPath.startsWith(this.rootPath)) {
    throw new Error("Access denied: Path outside root directory");
  }

  await fs.mkdir(path.dirname(fullPath), { recursive: true });
  await fs.writeFile(fullPath, content, 'utf-8');

  return {
    content: [{
      type: "text",
      text: `File created successfully: ${relativePath}`
    }]
  };
}

async searchFiles(query) {
  const files = await this.scanDirectory(this.rootPath);
  const results = [];

  for (const file of files) {
    try {
      const content = await fs.readFile(file, 'utf-8');
      if (content.toLowerCase().includes(query.toLowerCase())) {
        results.push({
          file: path.relative(this.rootPath, file),
          matches: content.split('\n')
            .map((line, index) => ({ line: index + 1, text: line }))
            .filter(item => item.text.toLowerCase().includes(query.toLowerCase()))
        });
      }
    } catch (error) {
      // Skip files that can't be read
    }
  }

  return {
    content: [{
      type: "text",
      text: `Found ${results.length} files containing "${query}":\n\n` +
             results.map(result => 
               `**${result.file}**\n` +
               result.matches.map(match => 
                 `  Line ${match.line}: ${match.text}`
               ).join('\n')
             ).join('\n\n')
    }]
  };
}
```

## Testing Your Setup

### 1. Verify Server Functionality

```bash
# Test resource listing
echo '{"jsonrpc":"2.0","id":1,"method":"resources/list","params":{}}' | node server.js

# Test tool listing
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | node server.js
```

### 2. Test with AI Assistant

Ask your AI assistant to:

1. **List available files**: "What files can you access?"
2. **Read a file**: "Show me the contents of README.md"
3. **Search files**: "Search for the word 'installation' in all files"
4. **Create a file**: "Create a new file called 'notes.txt' with some sample content"

## Common Issues and Solutions

### Server Not Starting
- **Check Node.js version**: Ensure you're using Node.js 18+
- **Verify file paths**: Make sure the root directory exists
- **Check permissions**: Ensure the server has read/write access

### AI Assistant Can't Connect
- **Restart the AI assistant** after adding MCP configuration
- **Check configuration syntax**: Ensure JSON is valid
- **Verify server path**: Make sure the server script path is correct

### Permission Errors
- **Check file permissions**: Ensure proper read/write access
- **Verify security boundaries**: Make sure paths don't escape the root directory

## Next Steps

Now that you have a basic MCP server running:

1. **[Learn Advanced Topics](/docs/03-AdvancedTopics/custom-servers)**: Build more sophisticated servers
2. **[Explore Security](/docs/05-Security/authentication)**: Implement authentication and authorization
3. **[See Examples](/docs/Appendix/examples)**: Check out more server implementations

## Resources

- **[API Reference](/docs/Appendix/api-reference)**: Complete protocol documentation
- **[GitHub Examples](https://github.com/modelcontextprotocol/servers)**: Sample server implementations
- **[Community Discord](https://discord.gg/mcp)**: Get help and share your projects
