---
title: Examples
sidebar_position: 2
---

# MCP Examples

This section provides practical examples of MCP server implementations for common use cases.

## File System Server

A complete file system server that provides read access to local files.

```javascript
// examples/filesystem-server.js
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  ListResourcesRequestSchema, 
  ReadResourceRequestSchema,
  ListToolsRequestSchema,
  CallToolRequestSchema 
} from '@modelcontextprotocol/sdk/types.js';
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
          tools: {}
        },
      }
    );

    this.setupHandlers();
  }

  setupHandlers() {
    // List available files as resources
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

    // Read file content
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

    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "search_files",
            description: "Search for text within files",
            inputSchema: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description: "Search query"
                },
                file_pattern: {
                  type: "string",
                  description: "File pattern to search (optional)",
                  default: "*"
                }
              },
              required: ["query"]
            }
          },
          {
            name: "create_file",
            description: "Create a new file",
            inputSchema: {
              type: "object",
              properties: {
                path: {
                  type: "string",
                  description: "File path relative to root"
                },
                content: {
                  type: "string",
                  description: "File content"
                }
              },
              required: ["path", "content"]
            }
          }
        ]
      };
    });

    // Execute tools
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      switch (name) {
        case "search_files":
          return await this.searchFiles(args.query, args.file_pattern);
        case "create_file":
          return await this.createFile(args.path, args.content);
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    });
  }

  async scanDirectory(dir) {
    const files = [];
    const entries = await fs.readdir(dir, { withFileTypes: true });
    
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isFile()) {
        files.push(fullPath);
      } else if (entry.isDirectory() && !entry.name.startsWith('.')) {
        files.push(...await this.scanDirectory(fullPath));
      }
    }
    
    return files;
  }

  async searchFiles(query, filePattern = "*") {
    const files = await this.scanDirectory(this.rootPath);
    const results = [];

    for (const file of files) {
      if (filePattern !== "*" && !file.includes(filePattern)) {
        continue;
      }

      try {
        const content = await fs.readFile(file, 'utf-8');
        const lines = content.split('\n');
        const matches = [];

        lines.forEach((line, index) => {
          if (line.toLowerCase().includes(query.toLowerCase())) {
            matches.push({
              line: index + 1,
              text: line.trim()
            });
          }
        });

        if (matches.length > 0) {
          results.push({
            file: path.relative(this.rootPath, file),
            matches
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

  async createFile(relativePath, content) {
    const fullPath = path.join(this.rootPath, relativePath);
    
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

  getMimeType(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    const mimeTypes = {
      '.txt': 'text/plain',
      '.md': 'text/markdown',
      '.js': 'text/javascript',
      '.ts': 'text/typescript',
      '.json': 'application/json',
      '.html': 'text/html',
      '.css': 'text/css',
      '.py': 'text/x-python',
      '.java': 'text/x-java',
      '.cpp': 'text/x-c++src',
      '.c': 'text/x-csrc'
    };
    return mimeTypes[ext] || 'text/plain';
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
  }
}

// Start the server
const rootPath = process.argv[2] || './';
const server = new FileSystemServer(rootPath);
server.run().catch(console.error);
```

## Database Server

An MCP server that provides access to a PostgreSQL database.

```javascript
// examples/database-server.js
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  ListResourcesRequestSchema, 
  ReadResourceRequestSchema,
  ListToolsRequestSchema,
  CallToolRequestSchema 
} from '@modelcontextprotocol/sdk/types.js';
import pg from 'pg';

class DatabaseServer {
  constructor(connectionString) {
    this.connectionString = connectionString;
    this.client = new pg.Client(connectionString);
    
    this.server = new Server(
      {
        name: "database-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          resources: {},
          tools: {}
        },
      }
    );

    this.setupHandlers();
  }

  async connect() {
    await this.client.connect();
  }

  setupHandlers() {
    // List database tables as resources
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => {
      const result = await this.client.query(`
        SELECT table_name, table_type 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
      `);

      return {
        resources: result.rows.map(row => ({
          uri: `db://table/${row.table_name}`,
          name: row.table_name,
          description: `Database table: ${row.table_name}`,
          mimeType: 'application/json'
        }))
      };
    });

    // Read table data
    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const url = new URL(request.params.uri);
      
      if (url.protocol !== 'db:' || !url.pathname.startsWith('/table/')) {
        throw new Error('Invalid database resource URI');
      }

      const tableName = url.pathname.split('/')[2];
      const limit = url.searchParams.get('limit') || '100';
      
      // Validate table name to prevent SQL injection
      if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(tableName)) {
        throw new Error('Invalid table name');
      }

      const result = await this.client.query(
        `SELECT * FROM ${tableName} LIMIT $1`,
        [parseInt(limit)]
      );

      return {
        contents: [{
          uri: request.params.uri,
          mimeType: 'application/json',
          text: JSON.stringify({
            table: tableName,
            rows: result.rows,
            rowCount: result.rowCount
          }, null, 2)
        }]
      };
    });

    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "query_database",
            description: "Execute a SELECT query on the database",
            inputSchema: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description: "SQL SELECT query to execute"
                },
                parameters: {
                  type: "array",
                  description: "Query parameters",
                  items: { type: "string" }
                }
              },
              required: ["query"]
            }
          },
          {
            name: "describe_table",
            description: "Get table schema information",
            inputSchema: {
              type: "object",
              properties: {
                table_name: {
                  type: "string",
                  description: "Name of the table to describe"
                }
              },
              required: ["table_name"]
            }
          }
        ]
      };
    });

    // Execute tools
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      switch (name) {
        case "query_database":
          return await this.queryDatabase(args.query, args.parameters);
        case "describe_table":
          return await this.describeTable(args.table_name);
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    });
  }

  async queryDatabase(query, parameters = []) {
    // Validate that it's a SELECT query
    if (!query.trim().toLowerCase().startsWith('select')) {
      throw new Error('Only SELECT queries are allowed');
    }

    try {
      const result = await this.client.query(query, parameters);
      
      return {
        content: [{
          type: "text",
          text: `Query executed successfully. Found ${result.rowCount} rows.\n\n` +
                JSON.stringify(result.rows, null, 2)
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Query failed: ${error.message}`
        }],
        isError: true
      };
    }
  }

  async describeTable(tableName) {
    // Validate table name
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(tableName)) {
      throw new Error('Invalid table name');
    }

    const result = await this.client.query(`
      SELECT 
        column_name,
        data_type,
        is_nullable,
        column_default,
        character_maximum_length
      FROM information_schema.columns 
      WHERE table_name = $1 
      ORDER BY ordinal_position
    `, [tableName]);

    return {
      content: [{
        type: "text",
        text: `Table: ${tableName}\n\n` +
              result.rows.map(row => 
                `${row.column_name}: ${row.data_type}${
                  row.character_maximum_length ? `(${row.character_maximum_length})` : ''
                }${row.is_nullable === 'NO' ? ' NOT NULL' : ''}${
                  row.column_default ? ` DEFAULT ${row.column_default}` : ''
                }`
              ).join('\n')
      }]
    };
  }

  async run() {
    await this.connect();
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
  }
}

// Start the server
const connectionString = process.env.DATABASE_URL || 'postgresql://localhost/mydb';
const server = new DatabaseServer(connectionString);
server.run().catch(console.error);
```

## Web API Server

An MCP server that provides access to external web APIs.

```javascript
// examples/web-api-server.js
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  ListResourcesRequestSchema, 
  ReadResourceRequestSchema,
  ListToolsRequestSchema,
  CallToolRequestSchema 
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';

class WebAPIServer {
  constructor(config) {
    this.config = config;
    this.apiClient = axios.create({
      baseURL: config.baseURL,
      headers: {
        'Authorization': `Bearer ${config.apiKey}`,
        'User-Agent': 'MCP-WebAPI-Server/1.0.0'
      },
      timeout: 30000
    });

    this.server = new Server(
      {
        name: "web-api-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          resources: {},
          tools: {}
        },
      }
    );

    this.setupHandlers();
  }

  setupHandlers() {
    // List API endpoints as resources
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => {
      const endpoints = this.config.endpoints || [];
      
      return {
        resources: endpoints.map(endpoint => ({
          uri: `api://${endpoint.path}`,
          name: endpoint.name,
          description: endpoint.description,
          mimeType: 'application/json'
        }))
      };
    });

    // Read API endpoint data
    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const url = new URL(request.params.uri);
      
      if (url.protocol !== 'api:') {
        throw new Error('Invalid API resource URI');
      }

      const path = url.pathname;
      const response = await this.apiClient.get(path);

      return {
        contents: [{
          uri: request.params.uri,
          mimeType: 'application/json',
          text: JSON.stringify(response.data, null, 2)
        }]
      };
    });

    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "api_get",
            description: "Make a GET request to the API",
            inputSchema: {
              type: "object",
              properties: {
                path: {
                  type: "string",
                  description: "API endpoint path"
                },
                params: {
                  type: "object",
                  description: "Query parameters"
                }
              },
              required: ["path"]
            }
          },
          {
            name: "api_post",
            description: "Make a POST request to the API",
            inputSchema: {
              type: "object",
              properties: {
                path: {
                  type: "string",
                  description: "API endpoint path"
                },
                data: {
                  type: "object",
                  description: "Request body data"
                }
              },
              required: ["path", "data"]
            }
          }
        ]
      };
    });

    // Execute tools
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      switch (name) {
        case "api_get":
          return await this.apiGet(args.path, args.params);
        case "api_post":
          return await this.apiPost(args.path, args.data);
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    });
  }

  async apiGet(path, params = {}) {
    try {
      const response = await this.apiClient.get(path, { params });
      
      return {
        content: [{
          type: "text",
          text: `GET ${path} - Status: ${response.status}\n\n` +
                JSON.stringify(response.data, null, 2)
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `API request failed: ${error.message}`
        }],
        isError: true
      };
    }
  }

  async apiPost(path, data) {
    try {
      const response = await this.apiClient.post(path, data);
      
      return {
        content: [{
          type: "text",
          text: `POST ${path} - Status: ${response.status}\n\n` +
                JSON.stringify(response.data, null, 2)
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `API request failed: ${error.message}`
        }],
        isError: true
      };
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
  }
}

// Configuration
const config = {
  baseURL: process.env.API_BASE_URL || 'https://api.example.com',
  apiKey: process.env.API_KEY,
  endpoints: [
    {
      path: '/users',
      name: 'Users',
      description: 'User management endpoints'
    },
    {
      path: '/posts',
      name: 'Posts',
      description: 'Blog posts endpoints'
    }
  ]
};

const server = new WebAPIServer(config);
server.run().catch(console.error);
```

## Git Repository Server

An MCP server that provides access to Git repository information.

```javascript
// examples/git-server.js
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  ListResourcesRequestSchema, 
  ReadResourceRequestSchema,
  ListToolsRequestSchema,
  CallToolRequestSchema 
} from '@modelcontextprotocol/sdk/types.js';
import { execSync } from 'child_process';
import fs from 'fs/promises';
import path from 'path';

class GitServer {
  constructor(repoPath) {
    this.repoPath = path.resolve(repoPath);
    
    this.server = new Server(
      {
        name: "git-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          resources: {},
          tools: {}
        },
      }
    );

    this.setupHandlers();
  }

  setupHandlers() {
    // List Git resources
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => {
      return {
        resources: [
          {
            uri: "git://status",
            name: "Git Status",
            description: "Current repository status",
            mimeType: "text/plain"
          },
          {
            uri: "git://log",
            name: "Git Log",
            description: "Recent commit history",
            mimeType: "text/plain"
          },
          {
            uri: "git://branches",
            name: "Git Branches",
            description: "Repository branches",
            mimeType: "text/plain"
          }
        ]
      };
    });

    // Read Git information
    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const url = new URL(request.params.uri);
      
      if (url.protocol !== 'git:') {
        throw new Error('Invalid Git resource URI');
      }

      const resource = url.pathname.substring(2); // Remove leading //
      let content;

      switch (resource) {
        case 'status':
          content = this.execGit('status --porcelain');
          break;
        case 'log':
          content = this.execGit('log --oneline -10');
          break;
        case 'branches':
          content = this.execGit('branch -a');
          break;
        default:
          throw new Error(`Unknown Git resource: ${resource}`);
      }

      return {
        contents: [{
          uri: request.params.uri,
          mimeType: 'text/plain',
          text: content
        }]
      };
    });

    // List Git tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "git_diff",
            description: "Show differences between commits, branches, or files",
            inputSchema: {
              type: "object",
              properties: {
                target: {
                  type: "string",
                  description: "Target to diff (file, commit, branch)"
                },
                base: {
                  type: "string",
                  description: "Base to compare against (optional)"
                }
              },
              required: ["target"]
            }
          },
          {
            name: "git_show",
            description: "Show commit details",
            inputSchema: {
              type: "object",
              properties: {
                commit: {
                  type: "string",
                  description: "Commit hash or reference"
                }
              },
              required: ["commit"]
            }
          },
          {
            name: "git_blame",
            description: "Show line-by-line authorship of a file",
            inputSchema: {
              type: "object",
              properties: {
                file: {
                  type: "string",
                  description: "File path to blame"
                }
              },
              required: ["file"]
            }
          }
        ]
      };
    });

    // Execute Git tools
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      switch (name) {
        case "git_diff":
          return await this.gitDiff(args.target, args.base);
        case "git_show":
          return await this.gitShow(args.commit);
        case "git_blame":
          return await this.gitBlame(args.file);
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    });
  }

  execGit(command) {
    try {
      return execSync(`git ${command}`, {
        cwd: this.repoPath,
        encoding: 'utf8'
      }).trim();
    } catch (error) {
      throw new Error(`Git command failed: ${error.message}`);
    }
  }

  async gitDiff(target, base) {
    try {
      const command = base ? `diff ${base} ${target}` : `diff ${target}`;
      const output = this.execGit(command);
      
      return {
        content: [{
          type: "text",
          text: `Git diff ${base ? `${base}..${target}` : target}:\n\n${output}`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Git diff failed: ${error.message}`
        }],
        isError: true
      };
    }
  }

  async gitShow(commit) {
    try {
      const output = this.execGit(`show ${commit}`);
      
      return {
        content: [{
          type: "text",
          text: `Git show ${commit}:\n\n${output}`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Git show failed: ${error.message}`
        }],
        isError: true
      };
    }
  }

  async gitBlame(file) {
    try {
      const output = this.execGit(`blame ${file}`);
      
      return {
        content: [{
          type: "text",
          text: `Git blame ${file}:\n\n${output}`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: "text",
          text: `Git blame failed: ${error.message}`
        }],
        isError: true
      };
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
  }
}

// Start the server
const repoPath = process.argv[2] || './';
const server = new GitServer(repoPath);
server.run().catch(console.error);
```

## Client Usage Examples

### Basic Client Implementation

```javascript
// examples/basic-client.js
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

class MCPClient {
  constructor() {
    this.client = new Client(
      {
        name: "example-client",
        version: "1.0.0"
      },
      {
        capabilities: {
          roots: {
            listChanged: true
          }
        }
      }
    );
  }

  async connect(serverCommand, serverArgs = []) {
    const transport = new StdioClientTransport({
      command: serverCommand,
      args: serverArgs
    });

    await this.client.connect(transport);
    console.log('Connected to MCP server');
  }

  async listResources() {
    const response = await this.client.request({
      method: "resources/list"
    });
    
    console.log('Available resources:');
    response.resources.forEach(resource => {
      console.log(`- ${resource.name}: ${resource.uri}`);
    });
    
    return response.resources;
  }

  async readResource(uri) {
    const response = await this.client.request({
      method: "resources/read",
      params: { uri }
    });
    
    return response.contents[0];
  }

  async listTools() {
    const response = await this.client.request({
      method: "tools/list"
    });
    
    console.log('Available tools:');
    response.tools.forEach(tool => {
      console.log(`- ${tool.name}: ${tool.description}`);
    });
    
    return response.tools;
  }

  async callTool(name, args = {}) {
    const response = await this.client.request({
      method: "tools/call",
      params: {
        name,
        arguments: args
      }
    });
    
    return response;
  }

  async close() {
    await this.client.close();
  }
}

// Usage example
async function main() {
  const client = new MCPClient();
  
  try {
    // Connect to filesystem server
    await client.connect('node', ['filesystem-server.js', './docs']);
    
    // List and read resources
    const resources = await client.listResources();
    if (resources.length > 0) {
      const content = await client.readResource(resources[0].uri);
      console.log('First resource content:', content.text.substring(0, 200));
    }
    
    // List and use tools
    const tools = await client.listTools();
    if (tools.some(t => t.name === 'search_files')) {
      const result = await client.callTool('search_files', {
        query: 'MCP',
        file_pattern: '*.md'
      });
      console.log('Search results:', result.content[0].text);
    }
    
  } catch (error) {
    console.error('Error:', error);
  } finally {
    await client.close();
  }
}

main().catch(console.error);
```

### Configuration Examples

#### Server Configuration

```json
{
  "name": "my-mcp-server",
  "version": "1.0.0",
  "capabilities": {
    "resources": {
      "subscribe": true,
      "listChanged": true
    },
    "tools": {
      "listChanged": true
    },
    "prompts": {
      "listChanged": true
    }
  },
  "security": {
    "authentication": {
      "type": "bearer",
      "required": true
    },
    "rateLimiting": {
      "enabled": true,
      "windowMs": 60000,
      "maxRequests": 100
    }
  },
  "logging": {
    "level": "info",
    "file": "./logs/server.log"
  }
}
```

#### Client Configuration

```json
{
  "servers": {
    "filesystem": {
      "command": "node",
      "args": ["servers/filesystem-server.js", "./data"],
      "env": {
        "LOG_LEVEL": "info"
      }
    },
    "database": {
      "command": "node",
      "args": ["servers/database-server.js"],
      "env": {
        "DATABASE_URL": "postgresql://localhost/mydb"
      }
    },
    "git": {
      "command": "node",
      "args": ["servers/git-server.js", "./"],
      "env": {
        "GIT_AUTHOR_NAME": "MCP Client"
      }
    }
  },
  "timeout": 30000,
  "retries": 3
}
```

These examples demonstrate common MCP server patterns and can be adapted for your specific use cases. Each server provides both resources (read-only data access) and tools (executable operations) following MCP best practices.
