# Tutorial: MCP Server with Authentication

Learn how to build a secure MCP server with multiple authentication mechanisms and a client that demonstrates proper authentication handling.

## What You'll Build

A complete MCP system with authentication that includes:
- **Secure MCP Server**: Multi-layered authentication with API keys, JWT tokens, and OAuth2
- **Authentication Client**: Demonstrates various auth methods and secure credential management
- **Security Best Practices**: Token rotation, secure storage, and access control

## Prerequisites

- Python 3.10+
- `uv` package manager
- Basic understanding of MCP concepts
- Understanding of authentication concepts (API keys, JWT, OAuth2)

## Learning Objectives

By the end of this tutorial, you'll understand:
- How to implement multiple authentication mechanisms in MCP servers
- How to securely handle credentials in MCP clients
- Best practices for token management and rotation
- How to implement role-based access control (RBAC)
- How to audit and log authentication events

## Project Structure

```
09-authentication/
├── README.md                    # This tutorial guide
├── mcp_server.py               # Working MCP server with authentication
├── auth_client.py              # Client with authentication handling
├── test_client.py              # Test client for validation
├── setup.py                    # Database initialization script
├── .env.example                # Environment variables template
├── pyproject.toml              # Project configuration
├── auth.db                     # SQLite database for users/tokens
└── libs/                       # Supporting libraries
    ├── auth_manager.py         # Authentication logic
    ├── security_utils.py       # Security utilities
    └── audit_logger.py         # Security audit logging
```

## What Makes This Special

This tutorial demonstrates **enterprise-grade security** features:

✅ **Multiple Auth Methods** - API keys, JWT tokens, OAuth2 flows  
✅ **Role-Based Access Control** - Different permissions for different users  
✅ **Token Rotation** - Automatic token refresh and expiration handling  
✅ **Audit Logging** - Complete security event tracking  
✅ **Secure Storage** - Encrypted credential storage and transmission  
✅ **Rate Limiting** - Protection against brute force attacks  

## Quick Start

1. **Install dependencies**:
   ```bash
   cd 09-authentication
   uv sync
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your security settings
   ```

3. **Initialize the database**:
   ```bash
   uv run python setup.py
   ```

4. **Start the authenticated server**:
   ```bash
   uv run python mcp_server.py
   ```

5. **Test the authentication system**:
   ```bash
   # Demo mode (shows all features)
   uv run python auth_client.py
   
   # Interactive mode (manual testing)
   uv run python auth_client.py interactive
   
   # Automated test suite
   uv run python test_client.py
   ```

## Authentication Methods

### 1. API Key Authentication
- Simple bearer token authentication
- Suitable for service-to-service communication
- Easy to implement and manage

### 2. JWT Token Authentication
- Stateless authentication with claims
- Supports expiration and refresh tokens
- Ideal for user sessions

### 3. OAuth2 Flow
- Industry standard for delegated authorization
- Supports multiple grant types
- Perfect for third-party integrations

## Security Features

### Token Management
- Automatic token rotation
- Secure token storage
- Expiration handling
- Refresh token flow

### Access Control
- Role-based permissions
- Resource-level authorization
- Action-specific controls
- Audit trail for all access

### Security Hardening
- Rate limiting per user/IP
- Brute force protection
- Secure headers
- Input validation and sanitization

## Step-by-Step Implementation

### Step 1: Set Up the Project

Create the project structure and install dependencies.

### Step 2: Implement Authentication Manager

Core authentication logic with multiple auth methods.

### Step 3: Create Secure MCP Server

Server with authentication middleware and protected endpoints.

### Step 4: Build Authentication Client

Client that handles various auth flows and credential management.

### Step 5: Add Security Features

Rate limiting, audit logging, and security hardening.

## Example Interactions

### Using the Auth Client

**Demo Mode (Automatic):**
```bash
uv run python auth_client.py
```
Runs a complete demonstration showing:
- Admin login and profile access
- Secure note creation
- API key generation and usage
- Access control validation
- User role testing

**Interactive Mode (Manual):**
```bash
uv run python auth_client.py interactive
> login
Username: admin
Password: admin123
> profile
> note
Note title: My Secure Note
Note content: This is confidential
> apikey
API key name: automation_key
> quit
```

**Programmatic Usage:**
```python
from auth_client import AuthenticatedMCPClient

async def example():
    async with AuthenticatedMCPClient() as client:
        # Login with credentials
        await client.login_with_password("admin", "admin123")
        
        # Get user profile
        profile = await client.get_user_profile()
        
        # Create secure note
        note = await client.create_secure_note("Title", "Content")
        
        # Generate API key
        api_key = await client.create_api_key("my_key", ["read", "write"])
```

## Security Best Practices

1. **Never hardcode credentials** - Use environment variables and secure vaults
2. **Implement token rotation** - Regular refresh of authentication tokens
3. **Use HTTPS in production** - Encrypt all communication
4. **Audit everything** - Log all authentication and authorization events
5. **Rate limit requests** - Prevent abuse and brute force attacks
6. **Validate all inputs** - Sanitize and validate user inputs
7. **Use strong passwords** - Enforce password complexity requirements
8. **Implement session timeout** - Automatic logout after inactivity

## Available Tools and Features

### Authentication Tools
- `authenticate_user` - Login with username/password
- `authenticate_with_api_key` - Login with API key
- `logout` - End current session

### User Tools (Requires Authentication)
- `get_user_profile` - View current user information
- `create_secure_note` - Create authenticated notes
- `create_api_key` - Generate new API keys

### Admin Tools (Admin Role Required)
- `list_audit_events` - View security audit logs
- `get_security_summary` - Get security dashboard

### Resources
- `user://profile` - User profile resource
- `security://summary` - Security summary resource (admin only)

## Default Test Credentials

- **Admin**: `admin / admin123`
- **User**: `testuser / TestPass123!`
- **ReadOnly**: `readonly / ReadOnly123!`
- **Service**: `service_bot / ServiceBot123!`

## Troubleshooting

### Common Issues

1. **Bcrypt Version Warning**: You may see `(trapped) error reading bcrypt version` - this is harmless and doesn't affect functionality
2. **Authentication Failures**: Check credentials match the default test accounts
3. **Permission Denied**: Verify user roles - admin functions require admin role
4. **Connection Issues**: Ensure `mcp_server.py` is running before starting the client

### Testing the System

**Quick Test:**
```bash
# Terminal 1: Start server
uv run python mcp_server.py

# Terminal 2: Run demo
uv run python auth_client.py
```

**Validation Test:**
```bash
uv run python test_client.py
```

### Security Considerations

- Never log sensitive information (passwords, tokens)
- Use secure random generators for tokens
- Implement proper session management
- Regular security audits and updates
- The bcrypt warning is cosmetic and doesn't affect security

## Next Steps

After completing this tutorial, you can:

1. **Integrate with Identity Providers**: Connect to Active Directory, LDAP, or cloud identity services
2. **Add Multi-Factor Authentication**: Implement TOTP, SMS, or hardware tokens
3. **Implement Single Sign-On**: Add SAML or OpenID Connect support
4. **Enhanced Monitoring**: Set up security monitoring and alerting
5. **Compliance Features**: Add features for GDPR, SOX, or other compliance requirements

## Resources

- [MCP Security Best Practices](../../../04-BestPractices/security.md)
- [JWT.io](https://jwt.io/) - JWT token debugging
- [OAuth 2.0 RFC](https://tools.ietf.org/html/rfc6749)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)

---

🔐 **Congratulations!** You've built a secure MCP system with enterprise-grade authentication!
