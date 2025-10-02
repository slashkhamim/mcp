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
    Path('data').mkdir(exist_ok=True)
    print(f"✅ Created directory: data")


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
    
    if success:
        print("✅ Setup completed successfully!")
        print("\nNext steps:")
        print("1. Install dependencies: uv sync")
        print("2. Configure your .env file with IdP settings")
        print("3. Start the RBAC proxy: uv run python rbac_proxy.py")
        print("4. Start the MCP server: uv run python mcp_server.py")
    else:
        print("❌ Setup completed with errors. Please check the configuration.")
        sys.exit(1)


if __name__ == "__main__":
    main()
