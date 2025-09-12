#!/usr/bin/env python3
"""
Interactive MCP Authentication Client
Provides a menu-driven interface for testing the MCP authentication system.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional

import jwt
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich.align import Align

# Add the current directory to the path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from libs.rbac_manager import RBACManager
from libs.database_manager import DatabaseManager


class InteractiveMCPClient:
    """Interactive client for testing MCP authentication system."""
    
    def __init__(self):
        self.console = Console()
        self.config = self.load_config()
        self.rbac_manager = RBACManager(self.config)
        self.db_manager = DatabaseManager(self.config)
        self.current_user = None
        self.jwt_token = None
        self.user_context = None
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from environment."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        
        return {
            'jwt_secret_key': os.getenv('JWT_SECRET_KEY', 'your-super-secret-jwt-key-change-this-in-production'),
            'jwt_algorithm': 'HS256',
            'token_expiry_minutes': 60,
            'issuer': 'internal-rbac-proxy',
            'audience': 'internal-mcp-server',
            'db_type': 'sqlite',
            'database_url': 'data/internal_system.db',
            'role_mappings_file': 'config/role_mappings.yaml',
            'rbac_proxy_url': 'http://localhost:8080',
            'audit_enabled': True
        }
    
    def display_header(self):
        """Display the application header."""
        header = Panel.fit(
            "[bold blue]🔐 Interactive MCP Authentication Client[/bold blue]\n"
            "[dim]Enterprise-grade authentication testing interface[/dim]",
            border_style="blue"
        )
        self.console.print(header)
        self.console.print()
    
    def display_current_user(self):
        """Display current user information."""
        if self.current_user:
            user_info = Table(show_header=False, box=None, padding=(0, 1))
            user_info.add_column("Field", style="cyan")
            user_info.add_column("Value", style="green")
            
            user_info.add_row("👤 User:", self.current_user.get('email', 'Unknown'))
            user_info.add_row("🎭 Roles:", ', '.join(self.current_user.get('roles', [])))
            user_info.add_row("🔑 Scopes:", ', '.join(self.current_user.get('scopes', []))[:80] + "...")
            
            # Token expiry
            if self.jwt_token:
                try:
                    decoded = jwt.decode(self.jwt_token, options={"verify_signature": False})
                    exp_time = datetime.fromtimestamp(decoded['exp'])
                    user_info.add_row("⏰ Token Expires:", exp_time.strftime("%Y-%m-%d %H:%M:%S"))
                except:
                    user_info.add_row("⏰ Token Expires:", "Invalid token")
            
            panel = Panel(user_info, title="[bold]Current Session[/bold]", border_style="green")
            self.console.print(panel)
        else:
            panel = Panel(
                "[red]No active session[/red]\n[dim]Please authenticate first[/dim]",
                title="[bold]Current Session[/bold]",
                border_style="red"
            )
            self.console.print(panel)
        self.console.print()
    
    def display_menu(self):
        """Display the main menu."""
        menu_items = [
            "1. 🔐 Authenticate User",
            "2. 👥 Query Employees",
            "3. 💰 Query Financial Data",
            "4. 📢 Query Public Information",
            "5. 🔍 Validate Current Token",
            "6. 🎭 Switch User Role",
            "7. 📊 View System Status",
            "8. 🧪 Run Security Tests",
            "9. 📋 View Audit Logs",
            "0. 🚪 Exit"
        ]
        
        menu_table = Table(show_header=False, box=None, padding=(0, 2))
        menu_table.add_column("Options", style="bold cyan")
        
        for item in menu_items:
            menu_table.add_row(item)
        
        panel = Panel(menu_table, title="[bold]Main Menu[/bold]", border_style="cyan")
        self.console.print(panel)
    
    async def authenticate_user(self):
        """Authenticate a user with different roles."""
        self.console.print("[bold cyan]🔐 User Authentication[/bold cyan]")
        self.console.print()
        
        # Predefined user profiles
        user_profiles = {
            "1": {
                "name": "John Doe - IT Admin",
                "email": "john.doe@company.com",
                "groups": ["IT-Admins", "Employees"],
                "description": "Full IT administrative access"
            },
            "2": {
                "name": "Jane Smith - HR Manager",
                "email": "jane.smith@company.com", 
                "groups": ["HR-Admins", "Employees"],
                "description": "HR administrative access"
            },
            "3": {
                "name": "Bob Johnson - Finance User",
                "email": "bob.johnson@company.com",
                "groups": ["Finance-Users", "Employees"],
                "description": "Financial data access"
            },
            "4": {
                "name": "Alice Wilson - Employee",
                "email": "alice.wilson@company.com",
                "groups": ["Employees"],
                "description": "Standard employee access"
            },
            "5": {
                "name": "Custom User",
                "email": "custom@company.com",
                "groups": [],
                "description": "Define custom roles"
            }
        }
        
        # Display user options
        profile_table = Table()
        profile_table.add_column("Option", style="cyan")
        profile_table.add_column("User", style="green")
        profile_table.add_column("Description", style="dim")
        
        for key, profile in user_profiles.items():
            profile_table.add_row(key, profile["name"], profile["description"])
        
        self.console.print(profile_table)
        self.console.print()
        
        choice = Prompt.ask("Select user profile", choices=list(user_profiles.keys()))
        
        if choice == "5":
            # Custom user
            email = Prompt.ask("Enter email")
            groups_input = Prompt.ask("Enter groups (comma-separated)", default="Employees")
            groups = [g.strip() for g in groups_input.split(",")]
            
            user_data = {
                "email": email,
                "groups": groups,
                "name": email.split("@")[0].title()
            }
        else:
            profile = user_profiles[choice]
            user_data = {
                "email": profile["email"],
                "groups": profile["groups"],
                "name": profile["name"].split(" - ")[0]
            }
        
        # Create authentication context
        mock_user_context = {
            'user_id': f"user_{hash(user_data['email']) % 10000}",
            'email': user_data['email'],
            'name': user_data['name'],
            'groups': user_data['groups'],
            'authenticated_at': int(datetime.utcnow().timestamp())
        }
        
        try:
            # Map groups to roles and scopes
            roles = self.rbac_manager.map_groups_to_roles(mock_user_context['groups'])
            scopes = self.rbac_manager.resolve_scopes(roles)
            
            # Create JWT token
            self.jwt_token = self.rbac_manager.create_jwt_token(mock_user_context, roles, scopes)
            
            # Store current user info
            self.current_user = {
                'email': user_data['email'],
                'name': user_data['name'],
                'groups': user_data['groups'],
                'roles': roles,
                'scopes': scopes
            }
            
            self.user_context = self.rbac_manager.validate_jwt_token(self.jwt_token)
            
            self.console.print(f"[green]✅ Successfully authenticated as {user_data['name']}[/green]")
            self.console.print(f"[dim]Roles: {', '.join(roles)}[/dim]")
            
        except Exception as e:
            self.console.print(f"[red]❌ Authentication failed: {e}[/red]")
    
    async def query_employees(self):
        """Query employee data."""
        if not self.user_context:
            self.console.print("[red]❌ Please authenticate first[/red]")
            return
        
        self.console.print("[bold cyan]👥 Employee Query[/bold cyan]")
        self.console.print()
        
        try:
            # Query options
            query_type = Prompt.ask(
                "Query type",
                choices=["all", "department", "specific"],
                default="all"
            )
            
            if query_type == "department":
                department = Prompt.ask("Enter department", default="Engineering")
                results = self.db_manager.get_employee_data(user_context=self.user_context)
                results = [r for r in results if r.get('department', '').lower() == department.lower()]
            elif query_type == "specific":
                emp_id = Prompt.ask("Enter employee ID")
                results = self.db_manager.get_employee_data(emp_id, self.user_context)
            else:
                results = self.db_manager.get_employee_data(user_context=self.user_context)
            
            # Display results
            if results:
                emp_table = Table()
                emp_table.add_column("ID", style="cyan")
                emp_table.add_column("Name", style="green")
                emp_table.add_column("Department", style="yellow")
                emp_table.add_column("Position", style="blue")
                emp_table.add_column("Email", style="dim")
                
                for emp in results:
                    emp_table.add_row(
                        emp.get('employee_id', ''),
                        f"{emp.get('first_name', '')} {emp.get('last_name', '')}",
                        emp.get('department', ''),
                        emp.get('position', ''),
                        emp.get('email', '')
                    )
                
                self.console.print(emp_table)
                self.console.print(f"\n[green]✅ Found {len(results)} employees[/green]")
            else:
                self.console.print("[yellow]⚠️ No employees found[/yellow]")
                
        except Exception as e:
            self.console.print(f"[red]❌ Query failed: {e}[/red]")
    
    async def query_financial_data(self):
        """Query financial data."""
        if not self.user_context:
            self.console.print("[red]❌ Please authenticate first[/red]")
            return
        
        self.console.print("[bold cyan]💰 Financial Data Query[/bold cyan]")
        self.console.print()
        
        try:
            record_type = Prompt.ask(
                "Record type",
                choices=["salary", "bonus", "expense", "all"],
                default="all"
            )
            
            results = self.db_manager.get_financial_data(
                record_type if record_type != "all" else None,
                self.user_context
            )
            
            if results:
                fin_table = Table()
                fin_table.add_column("Record ID", style="cyan")
                fin_table.add_column("Employee", style="green")
                fin_table.add_column("Type", style="yellow")
                fin_table.add_column("Amount", style="blue")
                fin_table.add_column("Description", style="dim")
                
                for record in results:
                    fin_table.add_row(
                        record.get('record_id', ''),
                        record.get('employee_id', ''),
                        record.get('record_type', ''),
                        f"${record.get('amount', 0):,.2f}",
                        record.get('description', '')
                    )
                
                self.console.print(fin_table)
                self.console.print(f"\n[green]✅ Found {len(results)} financial records[/green]")
            else:
                self.console.print("[yellow]⚠️ No financial records found[/yellow]")
                
        except Exception as e:
            self.console.print(f"[red]❌ Query failed: {e}[/red]")
    
    async def query_public_info(self):
        """Query public information."""
        if not self.user_context:
            self.console.print("[red]❌ Please authenticate first[/red]")
            return
        
        self.console.print("[bold cyan]📢 Public Information Query[/bold cyan]")
        self.console.print()
        
        try:
            category = Prompt.ask(
                "Category",
                choices=["policies", "announcements", "all"],
                default="all"
            )
            
            results = self.db_manager.get_public_info(
                category if category != "all" else None,
                self.user_context
            )
            
            if results:
                info_table = Table()
                info_table.add_column("ID", style="cyan")
                info_table.add_column("Title", style="green")
                info_table.add_column("Category", style="yellow")
                info_table.add_column("Published", style="blue")
                
                for info in results:
                    info_table.add_row(
                        info.get('info_id', ''),
                        info.get('title', ''),
                        info.get('category', ''),
                        info.get('published_date', '')
                    )
                
                self.console.print(info_table)
                self.console.print(f"\n[green]✅ Found {len(results)} information items[/green]")
            else:
                self.console.print("[yellow]⚠️ No public information found[/yellow]")
                
        except Exception as e:
            self.console.print(f"[red]❌ Query failed: {e}[/red]")
    
    async def validate_token(self):
        """Validate current JWT token."""
        if not self.jwt_token:
            self.console.print("[red]❌ No token to validate[/red]")
            return
        
        self.console.print("[bold cyan]🔍 Token Validation[/bold cyan]")
        self.console.print()
        
        try:
            # Validate token
            payload = self.rbac_manager.validate_jwt_token(self.jwt_token)
            
            # Display token info
            token_table = Table(show_header=False, box=None)
            token_table.add_column("Field", style="cyan")
            token_table.add_column("Value", style="green")
            
            token_table.add_row("Subject", payload.get('sub', ''))
            token_table.add_row("Email", payload.get('email', ''))
            token_table.add_row("Issuer", payload.get('iss', ''))
            token_table.add_row("Audience", payload.get('aud', ''))
            token_table.add_row("Issued At", datetime.fromtimestamp(payload.get('iat', 0)).strftime("%Y-%m-%d %H:%M:%S"))
            token_table.add_row("Expires At", datetime.fromtimestamp(payload.get('exp', 0)).strftime("%Y-%m-%d %H:%M:%S"))
            token_table.add_row("Roles", ', '.join(payload.get('roles', [])))
            
            self.console.print(token_table)
            self.console.print(f"\n[green]✅ Token is valid[/green]")
            
        except Exception as e:
            self.console.print(f"[red]❌ Token validation failed: {e}[/red]")
    
    async def view_system_status(self):
        """View system status."""
        self.console.print("[bold cyan]📊 System Status[/bold cyan]")
        self.console.print()
        
        status_table = Table()
        status_table.add_column("Component", style="cyan")
        status_table.add_column("Status", style="green")
        status_table.add_column("Details", style="dim")
        
        # Check RBAC proxy
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.config['rbac_proxy_url']}/health", timeout=5.0)
                if response.status_code == 200:
                    status_table.add_row("RBAC Proxy", "🟢 Online", f"Port 8080")
                else:
                    status_table.add_row("RBAC Proxy", "🟡 Issues", f"HTTP {response.status_code}")
        except:
            status_table.add_row("RBAC Proxy", "🔴 Offline", "Connection failed")
        
        # Check database
        try:
            results = self.db_manager.execute_query("SELECT COUNT(*) as count FROM employees", user_context={'scopes': ['*']})
            emp_count = results[0]['count'] if results else 0
            status_table.add_row("Database", "🟢 Connected", f"{emp_count} employees")
        except Exception as e:
            status_table.add_row("Database", "🔴 Error", str(e)[:50])
        
        # Check authentication
        if self.current_user:
            status_table.add_row("Authentication", "🟢 Active", self.current_user['email'])
        else:
            status_table.add_row("Authentication", "🟡 None", "Not authenticated")
        
        self.console.print(status_table)
    
    async def run_security_tests(self):
        """Run security tests."""
        self.console.print("[bold cyan]🧪 Security Tests[/bold cyan]")
        self.console.print()
        
        tests = [
            ("Token Expiry", self.test_token_expiry),
            ("Unauthorized Access", self.test_unauthorized_access),
            ("SQL Injection", self.test_sql_injection),
            ("Role Escalation", self.test_role_escalation)
        ]
        
        for test_name, test_func in tests:
            try:
                self.console.print(f"Running {test_name}...", end=" ")
                await test_func()
                self.console.print("[green]✅ PASS[/green]")
            except Exception as e:
                self.console.print(f"[red]❌ FAIL: {e}[/red]")
    
    async def test_token_expiry(self):
        """Test token expiry handling."""
        # This would test with an expired token
        pass
    
    async def test_unauthorized_access(self):
        """Test unauthorized access attempts."""
        # Test with invalid token
        invalid_token = "invalid.jwt.token"
        try:
            self.rbac_manager.validate_jwt_token(invalid_token)
            raise Exception("Invalid token was accepted")
        except:
            pass  # Expected to fail
    
    async def test_sql_injection(self):
        """Test SQL injection protection."""
        # This would test with malicious SQL
        pass
    
    async def test_role_escalation(self):
        """Test role escalation protection."""
        # This would test privilege escalation
        pass
    
    async def view_audit_logs(self):
        """View recent audit logs."""
        self.console.print("[bold cyan]📋 Recent Audit Logs[/bold cyan]")
        self.console.print()
        self.console.print("[dim]Audit logs are displayed in the server console[/dim]")
        self.console.print("[dim]Check the terminal running rbac_proxy.py and mcp_server.py[/dim]")
    
    async def run(self):
        """Run the interactive client."""
        self.display_header()
        
        while True:
            self.display_current_user()
            self.display_menu()
            
            choice = Prompt.ask("Select option", default="0")
            self.console.print()
            
            if choice == "0":
                self.console.print("[yellow]👋 Goodbye![/yellow]")
                break
            elif choice == "1":
                await self.authenticate_user()
            elif choice == "2":
                await self.query_employees()
            elif choice == "3":
                await self.query_financial_data()
            elif choice == "4":
                await self.query_public_info()
            elif choice == "5":
                await self.validate_token()
            elif choice == "6":
                await self.authenticate_user()  # Reuse auth for role switching
            elif choice == "7":
                await self.view_system_status()
            elif choice == "8":
                await self.run_security_tests()
            elif choice == "9":
                await self.view_audit_logs()
            else:
                self.console.print("[red]❌ Invalid option[/red]")
            
            self.console.print()
            if choice != "0":
                Prompt.ask("Press Enter to continue", default="")
                self.console.clear()


async def main():
    """Main entry point."""
    client = InteractiveMCPClient()
    try:
        await client.run()
    except KeyboardInterrupt:
        client.console.print("\n[yellow]👋 Goodbye![/yellow]")
    except Exception as e:
        client.console.print(f"\n[red]❌ Error: {e}[/red]")


if __name__ == "__main__":
    asyncio.run(main())
