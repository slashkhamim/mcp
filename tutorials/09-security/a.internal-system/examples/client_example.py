#!/usr/bin/env python3
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
