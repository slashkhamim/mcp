"""
Security utilities for MCP authentication
Provides rate limiting, input validation, and security headers.
"""

import asyncio
import time
from typing import Dict, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
import html
import ipaddress

from fastapi import Request, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_window: int = 100
    window_seconds: int = 60
    burst_requests: int = 10
    burst_window_seconds: int = 1


class SecurityHeaders:
    """Security headers for HTTP responses"""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get standard security headers"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }


class InputValidator:
    """Input validation and sanitization"""
    
    # Common validation patterns
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,50}$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    API_KEY_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{32,}$')
    
    @classmethod
    def validate_username(cls, username: str) -> bool:
        """Validate username format"""
        if not username or not isinstance(username, str):
            return False
        return bool(cls.USERNAME_PATTERN.match(username))
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email format"""
        if not email or not isinstance(email, str):
            return False
        return bool(cls.EMAIL_PATTERN.match(email))
    
    @classmethod
    def validate_password(cls, password: str) -> tuple[bool, str]:
        """Validate password strength"""
        if not password or not isinstance(password, str):
            return False, "Password is required"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 128:
            return False, "Password must be less than 128 characters"
        
        # Check for at least one uppercase, lowercase, digit, and special char
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        if not (has_upper and has_lower and has_digit and has_special):
            return False, "Password must contain uppercase, lowercase, digit, and special character"
        
        return True, "Password is valid"
    
    @classmethod
    def validate_api_key(cls, api_key: str) -> bool:
        """Validate API key format"""
        if not api_key or not isinstance(api_key, str):
            return False
        return bool(cls.API_KEY_PATTERN.match(api_key))
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 255) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return ""
        
        # HTML escape
        value = html.escape(value)
        
        # Trim whitespace
        value = value.strip()
        
        # Limit length
        if len(value) > max_length:
            value = value[:max_length]
        
        return value
    
    @classmethod
    def validate_ip_address(cls, ip: str) -> bool:
        """Validate IP address format"""
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False


class BruteForceProtection:
    """Protection against brute force attacks"""
    
    def __init__(self, max_attempts: int = 5, lockout_duration: int = 300):
        self.max_attempts = max_attempts
        self.lockout_duration = lockout_duration  # seconds
        self.failed_attempts: Dict[str, deque] = defaultdict(deque)
        self.lockouts: Dict[str, datetime] = {}
    
    def is_locked_out(self, identifier: str) -> bool:
        """Check if identifier is currently locked out"""
        if identifier in self.lockouts:
            if datetime.utcnow() < self.lockouts[identifier]:
                return True
            else:
                # Lockout expired
                del self.lockouts[identifier]
                if identifier in self.failed_attempts:
                    self.failed_attempts[identifier].clear()
        
        return False
    
    def record_failed_attempt(self, identifier: str) -> bool:
        """Record a failed attempt and return True if should be locked out"""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=15)  # 15-minute window
        
        # Clean old attempts
        attempts = self.failed_attempts[identifier]
        while attempts and attempts[0] < window_start:
            attempts.popleft()
        
        # Add new attempt
        attempts.append(now)
        
        # Check if should be locked out
        if len(attempts) >= self.max_attempts:
            self.lockouts[identifier] = now + timedelta(seconds=self.lockout_duration)
            return True
        
        return False
    
    def reset_attempts(self, identifier: str):
        """Reset failed attempts for identifier (on successful auth)"""
        if identifier in self.failed_attempts:
            self.failed_attempts[identifier].clear()
        if identifier in self.lockouts:
            del self.lockouts[identifier]


class RateLimiter:
    """Advanced rate limiter with multiple windows"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, identifier: str) -> tuple[bool, Optional[int]]:
        """Check if request is allowed, return (allowed, retry_after_seconds)"""
        now = time.time()
        requests = self.requests[identifier]
        
        # Clean old requests outside the window
        window_start = now - self.config.window_seconds
        while requests and requests[0] < window_start:
            requests.popleft()
        
        # Check burst limit (short window)
        burst_window_start = now - self.config.burst_window_seconds
        burst_count = sum(1 for req_time in requests if req_time >= burst_window_start)
        
        if burst_count >= self.config.burst_requests:
            return False, self.config.burst_window_seconds
        
        # Check main rate limit
        if len(requests) >= self.config.requests_per_window:
            # Calculate retry after based on oldest request
            oldest_request = requests[0]
            retry_after = int(oldest_request + self.config.window_seconds - now)
            return False, max(1, retry_after)
        
        # Allow request
        requests.append(now)
        return True, None


class SecurityAuditor:
    """Security event auditing"""
    
    @staticmethod
    def extract_client_info(request: Request) -> Dict[str, Any]:
        """Extract client information from request"""
        return {
            "ip_address": get_remote_address(request),
            "user_agent": request.headers.get("user-agent", ""),
            "referer": request.headers.get("referer", ""),
            "x_forwarded_for": request.headers.get("x-forwarded-for", ""),
            "x_real_ip": request.headers.get("x-real-ip", ""),
        }
    
    @staticmethod
    def is_suspicious_request(request: Request) -> tuple[bool, str]:
        """Check if request looks suspicious"""
        user_agent = request.headers.get("user-agent", "").lower()
        
        # Check for common attack patterns
        suspicious_patterns = [
            "sqlmap", "nikto", "nmap", "masscan", "zap",
            "burp", "dirb", "gobuster", "ffuf", "wfuzz"
        ]
        
        for pattern in suspicious_patterns:
            if pattern in user_agent:
                return True, f"Suspicious user agent: {pattern}"
        
        # Check for missing user agent
        if not user_agent or user_agent == "-":
            return True, "Missing or empty user agent"
        
        # Check for unusual request patterns
        path = str(request.url.path).lower()
        suspicious_paths = [
            "/.env", "/admin", "/wp-admin", "/phpmyadmin",
            "/config", "/backup", "/.git", "/debug"
        ]
        
        for sus_path in suspicious_paths:
            if sus_path in path:
                return True, f"Suspicious path: {sus_path}"
        
        return False, ""


class CryptoUtils:
    """Cryptographic utilities"""
    
    @staticmethod
    def constant_time_compare(a: str, b: str) -> bool:
        """Constant-time string comparison to prevent timing attacks"""
        if len(a) != len(b):
            return False
        
        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)
        
        return result == 0
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a cryptographically secure random token"""
        import secrets
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_with_salt(value: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash a value with salt"""
        import hashlib
        import secrets
        
        if salt is None:
            salt = secrets.token_hex(16)
        
        hash_obj = hashlib.pbkdf2_hmac('sha256', value.encode(), salt.encode(), 100000)
        return hash_obj.hex(), salt
