"""
File Operations Module

Provides safe file system operations for the MCP server.
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class FileManager:
    """Handles file system operations with safety checks."""
    
    def __init__(self, base_path: str = "."):
        """Initialize with a base working directory."""
        self.base_path = Path(base_path).resolve()
    
    def read_file(self, path: Path) -> str:
        """Read file contents."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try reading as binary and return hex representation
            with open(path, 'rb') as f:
                content = f.read()
                return f"Binary file ({len(content)} bytes): {content[:100].hex()}..."
    
    def write_file(self, path: Path, content: str, create_dirs: bool = False) -> None:
        """Write content to file."""
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)
        
        if not path.parent.exists():
            raise FileNotFoundError(f"Directory does not exist: {path.parent}")
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def create_directory(self, path: Path) -> None:
        """Create a directory."""
        if path.exists():
            raise FileExistsError(f"Path already exists: {path}")
        
        path.mkdir(parents=True, exist_ok=False)
    
    def delete_file(self, path: Path) -> None:
        """Delete a file."""
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        else:
            raise ValueError(f"Unknown file type: {path}")
    
    def list_directory(self, path: Path, show_hidden: bool = False) -> List[Dict[str, Any]]:
        """List directory contents."""
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        
        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")
        
        items = []
        for item in path.iterdir():
            # Skip hidden files unless requested
            if not show_hidden and item.name.startswith('.'):
                continue
            
            try:
                stat = item.stat()
                items.append({
                    'name': item.name,
                    'is_dir': item.is_dir(),
                    'size': stat.st_size if item.is_file() else 0,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'permissions': oct(stat.st_mode)[-3:]
                })
            except (OSError, PermissionError):
                # Skip items we can't access
                items.append({
                    'name': item.name,
                    'is_dir': item.is_dir(),
                    'size': 0,
                    'modified': 'unknown',
                    'permissions': 'unknown'
                })
        
        return sorted(items, key=lambda x: (not x['is_dir'], x['name'].lower()))
    
    def get_file_info(self, path: Path) -> Dict[str, Any]:
        """Get detailed file information."""
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        
        stat = path.stat()
        
        return {
            'name': path.name,
            'path': str(path),
            'is_dir': path.is_dir(),
            'size': stat.st_size,
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
            'permissions': oct(stat.st_mode)[-3:],
            'owner_readable': os.access(path, os.R_OK),
            'owner_writable': os.access(path, os.W_OK),
            'owner_executable': os.access(path, os.X_OK)
        }
    
    def copy_file(self, source: Path, destination: Path) -> None:
        """Copy a file or directory."""
        if not source.exists():
            raise FileNotFoundError(f"Source not found: {source}")
        
        if source.is_file():
            shutil.copy2(source, destination)
        elif source.is_dir():
            shutil.copytree(source, destination)
        else:
            raise ValueError(f"Unknown file type: {source}")
    
    def move_file(self, source: Path, destination: Path) -> None:
        """Move a file or directory."""
        if not source.exists():
            raise FileNotFoundError(f"Source not found: {source}")
        
        shutil.move(source, destination)
    
    def get_disk_usage(self, path: Path) -> Dict[str, int]:
        """Get disk usage information."""
        if not path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        
        usage = shutil.disk_usage(path)
        return {
            'total': usage.total,
            'used': usage.used,
            'free': usage.free
        }
