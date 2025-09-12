#!/usr/bin/env python3
"""
Setup script for MCP Authentication Tutorial
Initializes the database and creates default users for testing.
"""

import asyncio
import os
from dotenv import load_dotenv
from libs.auth_manager import AuthManager, UserRole
from libs.audit_logger import AuditLogger

# Load environment variables
load_dotenv()

async def setup_database():
    """Initialize database and create test users"""
    
    db_path = os.getenv("DATABASE_PATH", "./auth.db")
    secret_key = os.getenv("SECRET_KEY", "your-super-secret-key-change-this")
    
    print("🔧 Setting up MCP Authentication Tutorial...")
    print(f"📁 Database: {db_path}")
    
    # Initialize components
    auth_manager = AuthManager(db_path, secret_key)
    audit_logger = AuditLogger(db_path)
    
    # Initialize database
    print("📊 Initializing database...")
    await auth_manager.init_db()
    await audit_logger.init_db()
    
    # Create additional test users
    print("👥 Creating test users...")
    
    # Create regular user
    user = await auth_manager.create_user(
        username="testuser",
        email="test@example.com", 
        password="TestPass123!",
        role=UserRole.USER
    )
    if user:
        print(f"✅ Created user: testuser")
    
    # Create readonly user
    readonly_user = await auth_manager.create_user(
        username="readonly",
        email="readonly@example.com",
        password="ReadOnly123!",
        role=UserRole.READONLY
    )
    if readonly_user:
        print(f"✅ Created readonly user: readonly")
    
    # Create service account
    service_user = await auth_manager.create_user(
        username="service_bot",
        email="service@example.com",
        password="ServiceBot123!",
        role=UserRole.SERVICE
    )
    if service_user:
        print(f"✅ Created service user: service_bot")
        
        # Create API key for service account
        api_key = await auth_manager.create_api_key(
            user_id=service_user.id,
            name="default_service_key",
            permissions=["read", "write", "create"],
            expires_days=365
        )
        if api_key:
            print(f"🔑 Created service API key: {api_key}")
    
    print("\n🎉 Setup completed successfully!")
    print("\nDefault credentials:")
    print("  Admin: admin / admin123")
    print("  User: testuser / TestPass123!")
    print("  Readonly: readonly / ReadOnly123!")
    print("  Service: service_bot / ServiceBot123!")
    print(f"\n🚀 Start the server with: python auth_server.py")
    print(f"🧪 Run examples with: python example_usage.py")

if __name__ == "__main__":
    asyncio.run(setup_database())
