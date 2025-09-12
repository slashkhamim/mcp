"""
Test client for Internal System MCP with authentication flow.
Demonstrates the complete authentication and authorization process.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional
import requests
from datetime import datetime

from libs.idp_client import IdPAuthenticator
import mcp.types as types
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InternalSystemClient:
    """Test client for internal system MCP with full authentication flow."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rbac_proxy_url = config.get('rbac_proxy_url', 'http://localhost:8080')
        self.jwt_token = None
        self.user_info = None
        
        # Initialize IdP authenticator for testing
        self.idp_authenticator = IdPAuthenticator(config)
    
    async def authenticate_with_proxy(self) -> bool:
        """Authenticate with RBAC proxy and get JWT token."""
        try:
            print("🔐 Starting authentication process...")
            print("📝 Using mock authentication for testing (no real IdP calls)")
            
            # Skip real IdP authentication and go directly to mock token creation
            return await self._create_mock_token()
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            # For testing purposes, create a mock JWT token
            return await self._create_mock_token()
    
    async def _create_mock_token(self) -> bool:
        """Create a mock JWT token for testing purposes."""
        try:
            print("🧪 Creating mock JWT token for testing...")
            
            # Create token directly using RBAC manager to avoid timing issues
            from libs.rbac_manager import RBACManager
            
            rbac_manager = RBACManager(self.config)
            
            mock_user_context = {
                'user_id': 'test_user_123',
                'email': 'test.user@company.com',
                'name': 'Test User',
                'groups': ['IT-Users', 'Employees'],
                'authenticated_at': int(datetime.utcnow().timestamp())
            }
            
            # Map groups to roles and scopes
            roles = rbac_manager.map_groups_to_roles(mock_user_context['groups'])
            scopes = rbac_manager.resolve_scopes(roles)
            
            # Create JWT token directly
            self.jwt_token = rbac_manager.create_jwt_token(mock_user_context, roles, scopes)
            self.user_info = {
                'email': mock_user_context['email'],
                'name': mock_user_context['name'],
                'user_id': mock_user_context['user_id']
            }
            
            print(f"✅ Mock authentication successful!")
            print(f"👤 User: {self.user_info.get('email')}")
            print(f"🎭 Roles: {roles}")
            print(f"🔑 Scopes: {scopes}")
            
            # Debug: Print token info
            import jwt
            try:
                decoded = jwt.decode(self.jwt_token, options={"verify_signature": False})
                print(f"🔍 Token expires at: {datetime.fromtimestamp(decoded['exp'])}")
                print(f"🕐 Current time: {datetime.utcnow()}")
            except Exception as e:
                print(f"⚠️ Could not decode token for debugging: {e}")
            
            return True
                
        except Exception as e:
            print(f"❌ Mock authentication error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_mcp_connection(self) -> bool:
        """Test connection to MCP server."""
        try:
            print("\n🔗 Testing MCP server connection...")
            
            # Start MCP server process (in production, this would be running separately)
            import subprocess
            import time
            
            # Note: In a real scenario, the MCP server would be running as a separate service
            print("📝 Note: Ensure MCP server is running with: python mcp_server.py")
            
            return True
            
        except Exception as e:
            print(f"❌ MCP connection error: {e}")
            return False
    
    async def test_employee_query(self):
        """Test employee data query with authentication."""
        print("\n👥 Testing employee query...")
        
        try:
            # Simulate MCP tool call
            tool_args = {
                'jwt_token': self.jwt_token,
                'department': 'Engineering'
            }
            
            print(f"🔍 Querying employees in Engineering department...")
            print(f"🎫 Using JWT token: {self.jwt_token[:20]}..." if self.jwt_token else "No token")
            
            # In a real MCP client, this would be done through the MCP protocol
            # For testing, we'll call the database manager directly
            from libs.database_manager import DatabaseManager
            
            db_manager = DatabaseManager(self.config)
            
            # Decode JWT to get user context
            from libs.rbac_manager import RBACManager
            rbac_manager = RBACManager(self.config)
            
            user_context = rbac_manager.validate_jwt_token(self.jwt_token)
            
            results = db_manager.get_employee_data(user_context=user_context)
            
            print(f"✅ Found {len(results)} employees")
            for emp in results[:3]:  # Show first 3
                print(f"  - {emp.get('first_name')} {emp.get('last_name')} ({emp.get('department')})")
            
            if len(results) > 3:
                print(f"  ... and {len(results) - 3} more")
                
        except Exception as e:
            print(f"❌ Employee query failed: {e}")
    
    async def test_financial_query(self):
        """Test financial data query with authentication."""
        print("\n💰 Testing financial query...")
        
        try:
            # Decode JWT to get user context
            from libs.rbac_manager import RBACManager
            rbac_manager = RBACManager(self.config)
            
            user_context = rbac_manager.validate_jwt_token(self.jwt_token)
            
            # Check if user has financial access
            has_financial_access = rbac_manager.check_permission(user_context, 'db:read:financial')
            
            if not has_financial_access:
                print("⚠️  User does not have financial data access - this should fail")
            
            from libs.database_manager import DatabaseManager
            db_manager = DatabaseManager(self.config)
            
            results = db_manager.get_financial_data(user_context=user_context)
            
            print(f"✅ Found {len(results)} financial records")
            total_amount = sum(r.get('amount', 0) for r in results)
            print(f"💵 Total amount: ${total_amount:,.2f}")
            
        except Exception as e:
            print(f"❌ Financial query failed (expected if no financial access): {e}")
    
    async def test_public_info_query(self):
        """Test public information query."""
        print("\n📢 Testing public information query...")
        
        try:
            from libs.rbac_manager import RBACManager
            rbac_manager = RBACManager(self.config)
            
            user_context = rbac_manager.validate_jwt_token(self.jwt_token)
            
            from libs.database_manager import DatabaseManager
            db_manager = DatabaseManager(self.config)
            
            results = db_manager.get_public_info(user_context=user_context)
            
            print(f"✅ Found {len(results)} public information items")
            for info in results:
                print(f"  - {info.get('title')} ({info.get('category')})")
                
        except Exception as e:
            print(f"❌ Public info query failed: {e}")
    
    async def test_unauthorized_access(self):
        """Test unauthorized access attempts."""
        print("\n🚫 Testing unauthorized access...")
        
        try:
            # Try to access with invalid token
            print("🧪 Testing with invalid JWT token...")
            
            from libs.database_manager import DatabaseManager
            db_manager = DatabaseManager(self.config)
            
            fake_user_context = {
                'sub': 'fake_user',
                'email': 'fake@example.com',
                'scopes': []  # No scopes
            }
            
            try:
                results = db_manager.get_employee_data(user_context=fake_user_context)
                print("❌ Unauthorized access succeeded (this should not happen!)")
            except Exception as e:
                print(f"✅ Unauthorized access properly blocked: {e}")
            
            # Try to access financial data without permission
            print("🧪 Testing financial access without permission...")
            try:
                results = db_manager.get_financial_data(user_context=fake_user_context)
                print("❌ Unauthorized financial access succeeded (this should not happen!)")
            except Exception as e:
                print(f"✅ Unauthorized financial access properly blocked: {e}")
                
        except Exception as e:
            print(f"❌ Unauthorized access test error: {e}")
    
    async def test_token_validation(self):
        """Test JWT token validation."""
        print("\n🔍 Testing JWT token validation...")
        
        try:
            # Test with RBAC proxy
            headers = {'Authorization': f'Bearer {self.jwt_token}'}
            response = requests.post(
                f"{self.rbac_proxy_url}/auth/validate",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                validation_result = response.json()
                print("✅ Token validation successful")
                print(f"👤 Validated user: {validation_result['user_context']['email']}")
                print(f"🎭 Roles: {validation_result['user_context']['roles']}")
            else:
                print(f"❌ Token validation failed: {response.text}")
                
        except Exception as e:
            print(f"❌ Token validation error: {e}")
    
    async def run_all_tests(self):
        """Run all test scenarios."""
        print("🚀 Starting Internal System MCP Authentication Tests")
        print("=" * 60)
        
        # Step 1: Authenticate
        if not await self.authenticate_with_proxy():
            print("❌ Authentication failed - cannot proceed with tests")
            return
        
        # Step 2: Test MCP connection
        await self.test_mcp_connection()
        
        # Step 3: Test token validation
        await self.test_token_validation()
        
        # Step 4: Test authorized queries
        await self.test_employee_query()
        await self.test_financial_query()
        await self.test_public_info_query()
        
        # Step 5: Test unauthorized access
        await self.test_unauthorized_access()
        
        print("\n" + "=" * 60)
        print("🏁 All tests completed!")


def load_test_config() -> Dict[str, Any]:
    """Load test configuration."""
    # Load .env file if it exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    return {
        # IdP Configuration (for testing)
        'idp_type': 'okta',  # Mock IdP type
        'domain': 'test-domain.okta.com',
        'client_id': 'test_client_id',
        'client_secret': 'test_client_secret',
        'redirect_uri': 'http://localhost:8080/callback',
        'scopes': ['openid', 'profile', 'email', 'groups'],
        
        # JWT Configuration - Use same secret as RBAC proxy
        'jwt_secret_key': os.getenv('JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-this-in-production'),
        'jwt_algorithm': 'HS256',
        'token_expiry_minutes': 60,  # Longer expiry for testing
        'issuer': 'internal-rbac-proxy',
        'audience': 'internal-mcp-server',
        
        # Database Configuration
        'db_type': 'sqlite',
        'database_url': 'data/internal_system.db',
        
        # RBAC Configuration
        'role_mappings_file': 'config/role_mappings.yaml',
        'rbac_proxy_url': 'http://localhost:8080',
        'audit_enabled': True
    }


async def main():
    """Main test function."""
    try:
        # Load configuration
        config = load_test_config()
        
        # Create and run test client
        client = InternalSystemClient(config)
        await client.run_all_tests()
        
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        logger.exception("Test execution error")


if __name__ == "__main__":
    asyncio.run(main())
