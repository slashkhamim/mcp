"""
Database manager for internal systems with secure access controls.
Handles database connections, query execution, and audit logging.
"""

import os
import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from contextlib import contextmanager
import psycopg2
from psycopg2.extras import RealDictCursor
import pymongo
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Secure database manager with RBAC integration."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_type = config.get('db_type', 'sqlite').lower()
        self.connection_string = config.get('database_url')
        
        # Initialize database connection
        self._init_connection()
        
        # Audit logging
        self.audit_enabled = config.get('audit_enabled', True)
    
    def _init_connection(self):
        """Initialize database connection based on type."""
        if self.db_type == 'sqlite':
            self._init_sqlite()
        elif self.db_type == 'postgresql':
            self._init_postgresql()
        elif self.db_type == 'mongodb':
            self._init_mongodb()
        else:
            raise ValueError(f"Unsupported database type: {self.db_type}")
    
    def _init_sqlite(self):
        """Initialize SQLite connection."""
        db_path = self.connection_string or 'data/internal_system.db'
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.engine = create_engine(f'sqlite:///{db_path}')
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create sample tables
        self._create_sample_tables()
    
    def _init_postgresql(self):
        """Initialize PostgreSQL connection."""
        if not self.connection_string:
            raise ValueError("PostgreSQL connection string required")
        
        self.engine = create_engine(self.connection_string)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def _init_mongodb(self):
        """Initialize MongoDB connection."""
        if not self.connection_string:
            self.connection_string = 'mongodb://localhost:27017/internal_system'
        
        self.mongo_client = pymongo.MongoClient(self.connection_string)
        self.db = self.mongo_client.get_default_database()
    
    def _create_sample_tables(self):
        """Create sample tables for demonstration."""
        with self.engine.connect() as conn:
            # Employees table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id VARCHAR(50) UNIQUE NOT NULL,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    department VARCHAR(100),
                    position VARCHAR(100),
                    salary DECIMAL(10,2),
                    hire_date DATE,
                    status VARCHAR(20) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Financial records table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS financial_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id VARCHAR(50) UNIQUE NOT NULL,
                    employee_id VARCHAR(50),
                    record_type VARCHAR(50) NOT NULL,
                    amount DECIMAL(15,2) NOT NULL,
                    currency VARCHAR(3) DEFAULT 'USD',
                    description TEXT,
                    fiscal_year INTEGER,
                    quarter INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
                )
            """))
            
            # System logs table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    log_id VARCHAR(50) UNIQUE NOT NULL,
                    log_level VARCHAR(20) NOT NULL,
                    component VARCHAR(100),
                    message TEXT NOT NULL,
                    metadata TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Public information table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS public_info (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    info_id VARCHAR(50) UNIQUE NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    content TEXT,
                    category VARCHAR(100),
                    published_date DATE,
                    status VARCHAR(20) DEFAULT 'published',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            conn.commit()
        
        # Insert sample data
        self._insert_sample_data()
    
    def _insert_sample_data(self):
        """Insert sample data for testing."""
        with self.engine.connect() as conn:
            # Sample employees data with status
            employees_data = [
                ('EMP001', 'John', 'Doe', 'john.doe@company.com', 'Engineering', 'Senior Developer', 95000, '2020-01-15', 'active'),
                ('EMP002', 'Jane', 'Smith', 'jane.smith@company.com', 'HR', 'HR Manager', 85000, '2019-03-20', 'active'),
                ('EMP003', 'Bob', 'Johnson', 'bob.johnson@company.com', 'Finance', 'Financial Analyst', 75000, '2021-06-10', 'active'),
                ('EMP004', 'Alice', 'Wilson', 'alice.wilson@company.com', 'IT', 'System Administrator', 80000, '2020-09-05', 'active')
            ]
            
            for emp in employees_data:
                try:
                    conn.execute(text("""
                        INSERT OR IGNORE INTO employees 
                        (employee_id, first_name, last_name, email, department, position, salary, hire_date, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """), emp)
                except:
                    pass  # Ignore duplicates
            
            # Sample financial records
            financial_data = [
                ('FIN001', 'EMP001', 'salary', 95000, 'USD', 'Annual salary', 2023, 4),
                ('FIN002', 'EMP002', 'bonus', 10000, 'USD', 'Performance bonus', 2023, 4),
                ('FIN003', 'EMP003', 'expense', 2500, 'USD', 'Travel expenses', 2023, 3)
            ]
            
            for fin in financial_data:
                try:
                    conn.execute(text("""
                        INSERT OR IGNORE INTO financial_records 
                        (record_id, employee_id, record_type, amount, currency, description, fiscal_year, quarter)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """), fin)
                except:
                    pass
            
            # Sample public info with status
            public_data = [
                ('PUB001', 'Company Policies', 'Updated company policies for 2024', 'policies', '2024-01-01', 'published'),
                ('PUB002', 'Holiday Schedule', '2024 company holiday schedule', 'announcements', '2023-12-15', 'published')
            ]
            
            for pub in public_data:
                try:
                    conn.execute(text("""
                        INSERT OR IGNORE INTO public_info 
                        (info_id, title, content, category, published_date, status)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """), pub)
                except:
                    pass
            
            conn.commit()
    
    @contextmanager
    def get_session(self):
        """Get database session with proper cleanup."""
        if self.db_type == 'mongodb':
            yield self.db
        else:
            session = self.SessionLocal()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
    
    def execute_query(self, query: str, params: Dict[str, Any] = None, user_context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a database query with security checks."""
        # Audit log the query
        if self.audit_enabled and user_context:
            self._audit_query(query, params, user_context)
        
        # Security validation
        self._validate_query_security(query, user_context)
        
        if self.db_type == 'mongodb':
            return self._execute_mongo_query(query, params)
        else:
            return self._execute_sql_query(query, params)
    
    def _execute_sql_query(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute SQL query."""
        with self.engine.connect() as conn:
            if params:
                result = conn.execute(text(query), params)
            else:
                result = conn.execute(text(query))
            
            # Convert to list of dictionaries
            columns = result.keys()
            rows = result.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
    
    def _execute_mongo_query(self, collection: str, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute MongoDB query."""
        coll = self.db[collection]
        cursor = coll.find(query)
        
        results = []
        for doc in cursor:
            # Convert ObjectId to string
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            results.append(doc)
        
        return results
    
    def _validate_query_security(self, query: str, user_context: Dict[str, Any] = None):
        """Validate query for security issues."""
        if not user_context:
            raise Exception("User context required for database access")
        
        # Check for dangerous SQL patterns
        dangerous_patterns = [
            'DROP TABLE', 'DELETE FROM', 'TRUNCATE', 'ALTER TABLE',
            'CREATE TABLE', 'INSERT INTO', 'UPDATE SET'
        ]
        
        query_upper = query.upper()
        for pattern in dangerous_patterns:
            if pattern in query_upper:
                # Check if user has write permissions
                user_scopes = user_context.get('scopes', [])
                has_write_permission = any(
                    scope.startswith('db:write') or scope == '*' 
                    for scope in user_scopes
                )
                
                if not has_write_permission:
                    raise Exception(f"Insufficient permissions for query: {pattern}")
        
        # Prevent SQL injection patterns
        injection_patterns = [
            ';--', '/*', '*/', 'xp_', 'sp_', 'EXEC', 'EXECUTE'
        ]
        
        for pattern in injection_patterns:
            if pattern in query_upper:
                raise Exception(f"Potentially dangerous query pattern detected: {pattern}")
    
    def _audit_query(self, query: str, params: Dict[str, Any], user_context: Dict[str, Any]):
        """Log database query for audit purposes."""
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_context.get('sub'),
            'user_email': user_context.get('email'),
            'query': query[:500],  # Truncate long queries
            'params': json.dumps(params) if params else None,
            'user_scopes': user_context.get('scopes', [])
        }
        
        logger.info(f"DB_AUDIT: {json.dumps(audit_entry)}")
    
    def get_employee_data(self, employee_id: str = None, user_context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get employee data with scope-based filtering."""
        user_scopes = user_context.get('scopes', []) if user_context else []
        
        # Check read permission - allow both HR access and employee self-service
        has_employee_read = any(
            scope in ['db:read:employee', 'api:hr:read', 'api:hr:*', 'api:employee:read', '*']
            for scope in user_scopes
        )
        
        if not has_employee_read:
            raise Exception("Insufficient permissions to read employee data")
        
        # Build query based on permissions
        if employee_id:
            query = "SELECT * FROM employees WHERE employee_id = :employee_id"
            params = {'employee_id': employee_id}
        else:
            query = "SELECT * FROM employees WHERE status = 'active'"
            params = {}
        
        # Filter sensitive fields based on permissions
        results = self.execute_query(query, params, user_context)
        
        # Remove salary information unless user has HR admin access
        has_hr_admin = any(
            scope in ['db:write:employee', 'api:hr:*', '*']
            for scope in user_scopes
        )
        
        if not has_hr_admin:
            for result in results:
                result.pop('salary', None)
        
        return results
    
    def get_financial_data(self, record_type: str = None, user_context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get financial data with strict access controls."""
        user_scopes = user_context.get('scopes', []) if user_context else []
        
        # Check financial read permission
        has_financial_read = any(
            scope in ['db:read:financial', 'api:finance:read', 'api:finance:*', '*']
            for scope in user_scopes
        )
        
        if not has_financial_read:
            raise Exception("Insufficient permissions to read financial data")
        
        # Build query
        if record_type:
            query = "SELECT * FROM financial_records WHERE record_type = :record_type"
            params = {'record_type': record_type}
        else:
            query = "SELECT * FROM financial_records"
            params = {}
        
        return self.execute_query(query, params, user_context)
    
    def get_public_info(self, category: str = None, user_context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get public information (minimal permissions required)."""
        user_scopes = user_context.get('scopes', []) if user_context else []
        
        # Check basic read permission
        has_read_access = any(
            scope in ['db:read:public', 'api:employee:read', '*']
            for scope in user_scopes
        )
        
        if not has_read_access:
            raise Exception("Insufficient permissions to read public information")
        
        # Build query
        if category:
            query = "SELECT * FROM public_info WHERE category = :category AND status = 'published'"
            params = {'category': category}
        else:
            query = "SELECT * FROM public_info WHERE status = 'published'"
            params = {}
        
        return self.execute_query(query, params, user_context)
    
    def get_system_logs(self, log_level: str = None, user_context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get system logs (admin access required)."""
        user_scopes = user_context.get('scopes', []) if user_context else []
        
        # Check system read permission
        has_system_read = any(
            scope in ['db:read:system', 'api:system:read', 'api:system:*', '*']
            for scope in user_scopes
        )
        
        if not has_system_read:
            raise Exception("Insufficient permissions to read system logs")
        
        # Build query
        if log_level:
            query = "SELECT * FROM system_logs WHERE log_level = :log_level ORDER BY timestamp DESC LIMIT 100"
            params = {'log_level': log_level}
        else:
            query = "SELECT * FROM system_logs ORDER BY timestamp DESC LIMIT 100"
            params = {}
        
        return self.execute_query(query, params, user_context)
    
    def create_employee(self, employee_data: Dict[str, Any], user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create new employee record (HR admin access required)."""
        user_scopes = user_context.get('scopes', []) if user_context else []
        
        # Check write permission
        has_employee_write = any(
            scope in ['db:write:employee', 'api:hr:*', '*']
            for scope in user_scopes
        )
        
        if not has_employee_write:
            raise Exception("Insufficient permissions to create employee records")
        
        # Validate required fields
        required_fields = ['employee_id', 'first_name', 'last_name', 'email', 'department']
        for field in required_fields:
            if field not in employee_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Insert employee
        query = """
            INSERT INTO employees 
            (employee_id, first_name, last_name, email, department, position, salary, hire_date)
            VALUES (:employee_id, :first_name, :last_name, :email, :department, :position, :salary, :hire_date)
        """
        
        params = {
            'employee_id': employee_data['employee_id'],
            'first_name': employee_data['first_name'],
            'last_name': employee_data['last_name'],
            'email': employee_data['email'],
            'department': employee_data['department'],
            'position': employee_data.get('position'),
            'salary': employee_data.get('salary'),
            'hire_date': employee_data.get('hire_date')
        }
        
        self.execute_query(query, params, user_context)
        
        return {"success": True, "employee_id": employee_data['employee_id']}
    
    def close(self):
        """Close database connections."""
        if hasattr(self, 'mongo_client'):
            self.mongo_client.close()
        if hasattr(self, 'engine'):
            self.engine.dispose()
