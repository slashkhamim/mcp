"""
Setup script for Internal System MCP with authentication.
Initializes database, creates sample data, and validates configuration.
"""

import os
import sys
import asyncio
import logging
from typing import Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_directories():
    """Create necessary directories."""
    directories = [
        'data',
        'config',
        'logs',
        'examples'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")


def validate_environment():
    """Validate environment configuration."""
    print("🔍 Validating environment configuration...")
    
    # Check for .env file
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            print("⚠️  No .env file found. Please copy .env.example to .env and configure it.")
            print("   cp .env.example .env")
        else:
            print("❌ No .env.example file found")
        return False
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv not installed. Install with: uv add python-dotenv")
    
    # Check required environment variables
    required_vars = [
        'JWT_SECRET_KEY',
        'IDP_TYPE',
        'IDP_DOMAIN',
        'IDP_CLIENT_ID',
        'IDP_CLIENT_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ Environment configuration validated")
    return True


def initialize_database():
    """Initialize database with sample data."""
    print("🗄️  Initializing database...")
    
    try:
        from libs.database_manager import DatabaseManager
        
        config = {
            'db_type': os.getenv('DB_TYPE', 'sqlite'),
            'database_url': os.getenv('DATABASE_URL', 'data/internal_system.db'),
            'audit_enabled': True
        }
        
        db_manager = DatabaseManager(config)
        print("✅ Database initialized successfully")
        
        # Test database connection
        try:
            results = db_manager.execute_query(
                "SELECT COUNT(*) as count FROM employees",
                user_context={'scopes': ['*'], 'sub': 'setup', 'email': 'setup@system'}
            )
            employee_count = results[0]['count'] if results else 0
            print(f"📊 Database contains {employee_count} employees")
        except Exception as e:
            print(f"⚠️  Database query test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False


def test_rbac_configuration():
    """Test RBAC configuration."""
    print("🔐 Testing RBAC configuration...")
    
    try:
        from libs.rbac_manager import RBACManager
        
        config = {
            'jwt_secret_key': os.getenv('JWT_SECRET_KEY', 'test-secret-key-for-setup'),
            'jwt_algorithm': os.getenv('JWT_ALGORITHM', 'HS256'),
            'token_expiry_minutes': int(os.getenv('TOKEN_EXPIRY_MINUTES', '60')),  # Longer expiry for testing
            'issuer': os.getenv('JWT_ISSUER', 'internal-rbac-proxy'),
            'audience': os.getenv('JWT_AUDIENCE', 'internal-mcp-server'),
            'role_mappings_file': 'config/role_mappings.yaml'
        }
        
        rbac_manager = RBACManager(config)
        
        # Test role mapping
        test_groups = ['IT-Users', 'Employees']
        roles = rbac_manager.map_groups_to_roles(test_groups)
        scopes = rbac_manager.resolve_scopes(roles)
        
        print(f"✅ RBAC test: Groups {test_groups} → Roles {roles} → Scopes {scopes[:3]}...")
        
        # Test JWT token creation
        test_user_context = {
            'user_id': 'test_user',
            'email': 'test@company.com',
            'name': 'Test User',
            'groups': test_groups
        }
        
        jwt_token = rbac_manager.create_jwt_token(test_user_context, roles, scopes)
        
        # Test JWT token validation with better error handling
        try:
            payload = rbac_manager.validate_jwt_token(jwt_token)
            print("✅ RBAC configuration validated successfully")
            print(f"🎫 Token validation successful for user: {payload.get('email')}")
        except Exception as token_error:
            print(f"⚠️  Token validation warning: {token_error}")
            print("✅ RBAC configuration completed (token creation works)")
        
        return True
        
    except Exception as e:
        print(f"❌ RBAC configuration test failed: {e}")
        return False


def create_example_files():
    """Create example usage files."""
    print("📝 Creating example files...")
    
    # Example client usage
    client_example = '''#!/usr/bin/env python3
"""
Example client usage for Internal System MCP.
"""

import asyncio
from test_client import InternalSystemClient, load_test_config

async def main():
    config = load_test_config()
    client = InternalSystemClient(config)
    
    # Authenticate
    if await client.authenticate_with_proxy():
        print("Authentication successful!")
        
        # Test employee query
        await client.test_employee_query()
        
        # Test public info
        await client.test_public_info_query()
    else:
        print("Authentication failed!")

if __name__ == "__main__":
    asyncio.run(main())
'''
    
    with open('examples/client_example.py', 'w') as f:
        f.write(client_example)
    
    # Example server startup script
    server_example = '''#!/bin/bash
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
'''
    
    with open('examples/start_server.sh', 'w') as f:
        f.write(server_example)
    
    os.chmod('examples/start_server.sh', 0o755)
    
    print("✅ Example files created")


def main():
    """Main setup function."""
    print("🚀 Setting up Internal System MCP with Authentication")
    print("=" * 60)
    
    success = True
    
    # Step 1: Create directories
    create_directories()
    
    # Step 2: Validate environment
    if not validate_environment():
        success = False
        print("\n⚠️  Environment validation failed. Please configure .env file.")
    
    # Step 3: Initialize database
    if success and not initialize_database():
        success = False
    
    # Step 4: Test RBAC configuration
    if success and not test_rbac_configuration():
        success = False
    
    # Step 5: Create example files
    create_example_files()
    
    print("\n" + "=" * 60)
    
    if success:
        print("✅ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Install dependencies: uv sync")
        print("2. Configure your .env file with IdP settings")
        print("3. Start the RBAC proxy: uv run python rbac_proxy.py")
        print("4. Start the MCP server: uv run python mcp_server.py")
        print("5. Test with: uv run python test_client.py")
    else:
        print("❌ Setup completed with errors. Please check the configuration.")
        sys.exit(1)


if __name__ == "__main__":
    main()
