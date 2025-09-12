"""
Authentication Manager for MCP Server
Handles user authentication, authorization, and session management.
"""

import asyncio
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

import aiosqlite
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel


class UserRole(str, Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"
    SERVICE = "service"


class AuthMethod(str, Enum):
    """Supported authentication methods"""
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH2 = "oauth2"


@dataclass
class User:
    """User data model"""
    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


@dataclass
class APIKey:
    """API Key data model"""
    id: int
    user_id: int
    key_hash: str
    name: str
    permissions: List[str]
    expires_at: Optional[datetime]
    created_at: datetime
    last_used: Optional[datetime] = None


class TokenData(BaseModel):
    """JWT token payload"""
    username: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None
    permissions: List[str] = []


class AuthManager:
    """Manages authentication and authorization"""
    
    def __init__(self, db_path: str = "./auth.db", secret_key: str = "secret"):
        self.db_path = db_path
        self.secret_key = secret_key
        self.algorithm = "HS256"
        # Suppress bcrypt version warnings
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._db_initialized = False
    
    async def init_db(self):
        """Initialize the authentication database"""
        async with aiosqlite.connect(self.db_path) as db:
            # Users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            
            # API Keys table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    key_hash TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    permissions TEXT NOT NULL DEFAULT '[]',
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Sessions table (for JWT refresh tokens)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    refresh_token_hash TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Audit log table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    resource TEXT,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.commit()
            
        # Create default admin user if none exists
        await self._create_default_admin()
        self._db_initialized = True
    
    async def _create_default_admin(self):
        """Create default admin user if no users exist"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            count = (await cursor.fetchone())[0]
            
            if count == 0:
                admin_password = "admin123"  # Change in production!
                password_hash = self.pwd_context.hash(admin_password)
                
                await db.execute("""
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (?, ?, ?, ?)
                """, ("admin", "admin@example.com", password_hash, UserRole.ADMIN))
                
                await db.commit()
                print(f"Created default admin user: admin / {admin_password}")
    
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def generate_api_key(self) -> str:
        """Generate a new API key"""
        return secrets.token_urlsafe(32)
    
    def hash_api_key(self, api_key: str) -> str:
        """Hash an API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    async def create_user(self, username: str, email: str, password: str, 
                         role: UserRole = UserRole.USER) -> Optional[User]:
        """Create a new user"""
        if not self._db_initialized:
            await self.init_db()
            
        password_hash = self.hash_password(password)
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO users (username, email, password_hash, role)
                    VALUES (?, ?, ?, ?)
                """, (username, email, password_hash, role.value))
                
                user_id = cursor.lastrowid
                await db.commit()
                
                return User(
                    id=user_id,
                    username=username,
                    email=email,
                    role=role,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
        except sqlite3.IntegrityError:
            return None  # User already exists
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username/password"""
        if not self._db_initialized:
            await self.init_db()
            
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, username, email, password_hash, role, is_active, created_at, last_login
                FROM users WHERE username = ? AND is_active = 1
            """, (username,))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            if not self.verify_password(password, row[3]):
                return None
            
            # Update last login
            await db.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            """, (row[0],))
            await db.commit()
            
            return User(
                id=row[0],
                username=row[1],
                email=row[2],
                role=UserRole(row[4]),
                is_active=bool(row[5]),
                created_at=datetime.fromisoformat(row[6]),
                last_login=datetime.utcnow()
            )
    
    async def authenticate_api_key(self, api_key: str) -> Optional[User]:
        """Authenticate user with API key"""
        if not self._db_initialized:
            await self.init_db()
            
        key_hash = self.hash_api_key(api_key)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT u.id, u.username, u.email, u.role, u.is_active, u.created_at,
                       ak.id, ak.permissions, ak.expires_at
                FROM users u
                JOIN api_keys ak ON u.id = ak.user_id
                WHERE ak.key_hash = ? AND u.is_active = 1
                AND (ak.expires_at IS NULL OR ak.expires_at > CURRENT_TIMESTAMP)
            """, (key_hash,))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            # Update last used timestamp
            await db.execute("""
                UPDATE api_keys SET last_used = CURRENT_TIMESTAMP WHERE id = ?
            """, (row[6],))
            await db.commit()
            
            return User(
                id=row[0],
                username=row[1],
                email=row[2],
                role=UserRole(row[3]),
                is_active=bool(row[4]),
                created_at=datetime.fromisoformat(row[5])
            )
    
    async def create_api_key(self, user_id: int, name: str, 
                           permissions: List[str] = None,
                           expires_days: Optional[int] = None) -> Optional[str]:
        """Create a new API key for a user"""
        if not self._db_initialized:
            await self.init_db()
            
        api_key = self.generate_api_key()
        key_hash = self.hash_api_key(api_key)
        permissions = permissions or []
        expires_at = None
        
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO api_keys (user_id, key_hash, name, permissions, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, key_hash, name, str(permissions), expires_at))
                
                await db.commit()
                return api_key
        except sqlite3.IntegrityError:
            return None
    
    def create_access_token(self, user: User, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        
        to_encode = {
            "sub": user.username,
            "user_id": user.id,
            "role": user.role.value,
            "exp": expire
        }
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    async def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            user_id: int = payload.get("user_id")
            role: str = payload.get("role")
            
            if username is None or user_id is None:
                return None
                
            return TokenData(
                username=username,
                user_id=user_id,
                role=role,
                permissions=[]  # Load from database if needed
            )
        except JWTError:
            return None
    
    async def has_permission(self, user: User, resource: str, action: str) -> bool:
        """Check if user has permission for resource/action"""
        # Admin has all permissions
        if user.role == UserRole.ADMIN:
            return True
        
        # Basic role-based permissions
        if user.role == UserRole.READONLY and action in ["read", "list"]:
            return True
        
        if user.role == UserRole.USER and action in ["read", "list", "create", "update"]:
            return True
        
        if user.role == UserRole.SERVICE:
            # Service accounts have specific permissions
            return True
        
        return False
    
    async def log_audit_event(self, user_id: Optional[int], action: str, 
                            resource: Optional[str] = None, 
                            details: Optional[str] = None,
                            ip_address: Optional[str] = None,
                            user_agent: Optional[str] = None,
                            success: bool = True):
        """Log an audit event"""
        if not self._db_initialized:
            await self.init_db()
            
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO audit_log (user_id, action, resource, details, ip_address, user_agent, success)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, action, resource, details, ip_address, user_agent, success))
            
            await db.commit()
