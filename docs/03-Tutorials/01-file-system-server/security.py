"""
Security Module

Provides path validation and security checks for file operations.
"""

import os
from pathlib import Path
from typing import Set, List


class SecurityValidator:
    """Validates file paths and operations for security."""
    
    def __init__(self, allowed_dirs: List[str] = None, blocked_dirs: List[str] = None):
        """Initialize security validator.
        
        Args:
            allowed_dirs: List of allowed directory paths (if None, current dir and subdirs)
            blocked_dirs: List of blocked directory patterns
        """
        self.allowed_dirs = allowed_dirs or ["."]
        self.blocked_dirs = blocked_dirs or [
            "/etc", "/usr", "/var", "/sys", "/proc", "/dev",
            "C:\\Windows", "C:\\Program Files", "C:\\System32"
        ]
        
        # Convert to resolved paths
        self.allowed_paths = [Path(d).resolve() for d in self.allowed_dirs]
        self.blocked_paths = [Path(d).resolve() for d in self.blocked_dirs if Path(d).exists()]
    
    def validate_path(self, path_str: str) -> Path:
        """Validate and resolve a path for security.
        
        Args:
            path_str: Path string to validate
            
        Returns:
            Resolved Path object
            
        Raises:
            SecurityError: If path is not allowed
            ValueError: If path is invalid
        """
        if not path_str:
            raise ValueError("Path cannot be empty")
        
        # Basic path validation
        if any(dangerous in path_str for dangerous in ["../../../", "..\\..\\", "~/"]):
            raise SecurityError("Path traversal detected")
        
        # Resolve the path
        try:
            resolved_path = Path(path_str).resolve()
        except (OSError, ValueError) as e:
            raise ValueError(f"Invalid path: {e}")
        
        # Check if path is within allowed directories
        if not self._is_path_allowed(resolved_path):
            raise SecurityError(f"Access denied to path: {resolved_path}")
        
        # Check if path is in blocked directories
        if self._is_path_blocked(resolved_path):
            raise SecurityError(f"Access blocked to system path: {resolved_path}")
        
        return resolved_path
    
    def _is_path_allowed(self, path: Path) -> bool:
        """Check if path is within allowed directories."""
        for allowed_path in self.allowed_paths:
            try:
                # Check if path is within or equal to allowed path
                path.relative_to(allowed_path)
                return True
            except ValueError:
                continue
        return False
    
    def _is_path_blocked(self, path: Path) -> bool:
        """Check if path is in blocked directories."""
        for blocked_path in self.blocked_paths:
            try:
                # Check if path is within blocked path
                path.relative_to(blocked_path)
                return True
            except ValueError:
                continue
        return False
    
    def validate_filename(self, filename: str) -> bool:
        """Validate filename for security.
        
        Args:
            filename: Filename to validate
            
        Returns:
            True if filename is safe
        """
        if not filename:
            return False
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\0']
        if any(char in filename for char in dangerous_chars):
            return False
        
        # Check for reserved names (Windows)
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        if filename.upper() in reserved_names:
            return False
        
        # Check length
        if len(filename) > 255:
            return False
        
        return True
    
    def get_safe_filename(self, filename: str) -> str:
        """Convert filename to safe version.
        
        Args:
            filename: Original filename
            
        Returns:
            Safe filename
        """
        if self.validate_filename(filename):
            return filename
        
        # Replace dangerous characters
        safe_chars = {
            '<': '(', '>': ')', ':': '-', '"': "'", '|': '-',
            '?': '', '*': '', '\0': ''
        }
        
        safe_name = filename
        for dangerous, safe in safe_chars.items():
            safe_name = safe_name.replace(dangerous, safe)
        
        # Truncate if too long
        if len(safe_name) > 255:
            name, ext = os.path.splitext(safe_name)
            max_name_len = 255 - len(ext)
            safe_name = name[:max_name_len] + ext
        
        return safe_name or "unnamed_file"


class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass
