#!/usr/bin/env python3
"""
Test Configuration

Provides test-specific configurations for the MCP server.
"""

import tempfile
import os
from pathlib import Path
from security import SecurityValidator


class TestSecurityValidator(SecurityValidator):
    """Test-specific security validator that allows access to temp directories."""
    
    def __init__(self):
        # Get the system temp directory
        temp_dir = tempfile.gettempdir()
        
        # Allow access to current directory and temp directories
        allowed_dirs = [
            ".",  # Current directory
            temp_dir,  # System temp directory
            "/tmp",  # Unix temp directory
            os.path.expanduser("~/tmp"),  # User temp directory
        ]
        
        # Keep the same blocked directories but remove /var since temp is often in /var
        blocked_dirs = [
            "/etc", "/usr", "/sys", "/proc", "/dev",
            "C:\\Windows", "C:\\Program Files", "C:\\System32"
        ]
        
        super().__init__(allowed_dirs=allowed_dirs, blocked_dirs=blocked_dirs)
    
    def validate_path(self, path_str: str) -> Path:
        """Override to be more permissive for testing."""
        if not path_str:
            raise ValueError("Path cannot be empty")
        
        # Basic path validation (but more permissive for testing)
        if "../../.." in path_str:  # Only block extreme traversal
            from security import SecurityError
            raise SecurityError("Extreme path traversal detected")
        
        # Resolve the path
        try:
            resolved_path = Path(path_str).resolve()
        except (OSError, ValueError) as e:
            raise ValueError(f"Invalid path: {e}")
        
        # For testing, allow temp directories and current directory
        temp_dir = Path(tempfile.gettempdir()).resolve()
        current_dir = Path(".").resolve()
        
        # Check if it's in temp directory or current directory
        try:
            resolved_path.relative_to(temp_dir)
            return resolved_path
        except ValueError:
            pass
            
        try:
            resolved_path.relative_to(current_dir)
            return resolved_path
        except ValueError:
            pass
        
        # Fall back to original validation for other paths
        return super().validate_path(path_str)
