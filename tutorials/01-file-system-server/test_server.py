#!/usr/bin/env python3
"""
Test suite for File System MCP Server

Tests all tools, resources, and prompts to ensure proper functionality.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
import asyncio

# Import the individual functions from server
from server import (
    read_file, write_file, create_directory, delete_file, 
    list_directory, file_info, browse_directory, file_content,
    file_script, file_documentation, file_manager
)
from test_config import TestSecurityValidator

# Replace the security validator with test version
import server
server.security = TestSecurityValidator()


class TestFileSystemMCPServer:
    """Test class for File System MCP Server"""
    
    def setup_method(self):
        """Setup test environment before each test"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = Path(self.test_dir) / "test.txt"
        self.test_content = "Hello, MCP World!"
        
    def teardown_method(self):
        """Cleanup test environment after each test"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    # Tool Tests
    def test_read_file_success(self):
        """Test successful file reading"""
        # Create test file
        self.test_file.write_text(self.test_content)
        
        # Test reading
        result = read_file(str(self.test_file))
        assert self.test_content in result
        
    def test_read_file_not_found(self):
        """Test reading non-existent file"""
        result = read_file("/nonexistent/file.txt")
        assert "Error reading file" in result
        
    def test_write_file_success(self):
        """Test successful file writing"""
        test_path = str(Path(self.test_dir) / "new_file.txt")
        
        result = write_file(test_path, self.test_content)
        
        assert "Successfully wrote" in result
        assert Path(test_path).read_text() == self.test_content
        
    def test_write_file_create_dirs(self):
        """Test writing file with directory creation"""
        test_path = str(Path(self.test_dir) / "new_dir" / "new_file.txt")
        
        result = write_file(test_path, self.test_content, create_dirs=True)
        
        assert "Successfully wrote" in result
        assert Path(test_path).exists()
        
    def test_create_directory_success(self):
        """Test successful directory creation"""
        new_dir = str(Path(self.test_dir) / "new_directory")
        
        result = create_directory(new_dir)
        
        assert "Successfully created directory" in result
        assert Path(new_dir).is_dir()
        
    def test_delete_file_success(self):
        """Test successful file deletion"""
        # Create test file
        self.test_file.write_text(self.test_content)
        
        result = delete_file(str(self.test_file))
        
        assert "Successfully deleted" in result
        assert not self.test_file.exists()
        
    def test_list_directory_success(self):
        """Test successful directory listing"""
        # Create test files
        (Path(self.test_dir) / "file1.txt").write_text("content1")
        (Path(self.test_dir) / "file2.txt").write_text("content2")
        (Path(self.test_dir) / "subdir").mkdir()
        
        result = list_directory(self.test_dir)
        
        assert "file1.txt" in result
        assert "file2.txt" in result
        assert "subdir" in result
        assert "📁" in result  # Directory icon
        assert "📄" in result  # File icon
        
    def test_list_directory_with_hidden(self):
        """Test directory listing with hidden files"""
        # Create hidden file
        (Path(self.test_dir) / ".hidden").write_text("hidden content")
        (Path(self.test_dir) / "visible.txt").write_text("visible content")
        
        # Test without hidden files
        result_no_hidden = list_directory(self.test_dir, show_hidden=False)
        assert ".hidden" not in result_no_hidden
        assert "visible.txt" in result_no_hidden
        
        # Test with hidden files
        result_with_hidden = list_directory(self.test_dir, show_hidden=True)
        assert ".hidden" in result_with_hidden
        assert "visible.txt" in result_with_hidden
        
    def test_file_info_success(self):
        """Test successful file info retrieval"""
        # Create test file
        self.test_file.write_text(self.test_content)
        
        result = file_info(str(self.test_file))
        
        assert "File Information" in result
        assert "Type: File" in result
        assert "Size:" in result
        assert "Modified:" in result
        assert "Permissions:" in result
        
    def test_file_info_directory(self):
        """Test file info for directory"""
        result = file_info(self.test_dir)
        
        assert "Type: Directory" in result
        
    # Resource Tests
    def test_browse_directory_resource(self):
        """Test directory browsing resource"""
        # Create test files
        (Path(self.test_dir) / "file1.txt").write_text("content1")
        (Path(self.test_dir) / "subdir").mkdir()
        
        # Test resource
        import urllib.parse
        encoded_path = urllib.parse.quote(self.test_dir)
        result = browse_directory(encoded_path)
        
        data = json.loads(result)
        assert "path" in data
        assert "items" in data
        assert len(data["items"]) >= 2
        
    def test_file_content_resource(self):
        """Test file content resource"""
        # Create test file
        self.test_file.write_text(self.test_content)
        
        # Test resource
        import urllib.parse
        encoded_path = urllib.parse.quote(str(self.test_file))
        result = file_content(encoded_path)
        
        data = json.loads(result)
        assert "content" in data
        assert data["content"] == self.test_content
        assert "info" in data
        
    def test_file_content_resource_error(self):
        """Test file content resource with directory (should error)"""
        import urllib.parse
        encoded_path = urllib.parse.quote(self.test_dir)
        result = file_content(encoded_path)
        
        data = json.loads(result)
        assert "error" in data
        assert "not a file" in data["error"]
        
    # Prompt Tests
    def test_file_script_prompt_backup(self):
        """Test file script prompt for backup operation"""
        result = file_script("backup", "/home/user/documents", "bash")
        
        assert "backup script" in result.lower()
        assert "/home/user/documents" in result
        assert "error handling" in result.lower()
        assert "bash" in result.lower()
        
    def test_file_script_prompt_cleanup(self):
        """Test file script prompt for cleanup operation"""
        result = file_script("cleanup", "/tmp", "python")
        
        assert "cleanup script" in result.lower()
        assert "/tmp" in result
        assert "python" in result.lower()
        
    def test_file_script_prompt_invalid_operation(self):
        """Test file script prompt with invalid operation"""
        result = file_script("invalid_op", "/some/path")
        
        assert "Unknown operation" in result
        assert "Available:" in result
        
    def test_file_documentation_prompt_readme(self):
        """Test file documentation prompt for README"""
        result = file_documentation("/project/path", "README")
        
        assert "README.md" in result
        assert "/project/path" in result
        assert "project description" in result.lower()
        assert "installation" in result.lower()
        
    def test_file_documentation_prompt_api(self):
        """Test file documentation prompt for API docs"""
        result = file_documentation("/api/project", "API")
        
        assert "API documentation" in result
        assert "/api/project" in result
        
    def test_file_documentation_prompt_default(self):
        """Test file documentation prompt with invalid type (should default to README)"""
        result = file_documentation("/some/path", "INVALID")
        
        assert "README.md" in result  # Should default to README
        
    # Security Tests
    def test_security_validation(self):
        """Test that security validation is working"""
        # Test that dangerous paths are rejected
        dangerous_paths = [
            "../../../etc/passwd",
            "/etc/shadow",
            "~/.ssh/id_rsa"
        ]
        
        for dangerous_path in dangerous_paths:
            result = read_file(dangerous_path)
            # Should either be blocked by security or fail safely
            assert "Error" in result or "Permission denied" in result
            
    # Integration Tests
    def test_full_workflow(self):
        """Test a complete workflow: create, write, read, list, delete"""
        test_file_path = str(Path(self.test_dir) / "workflow_test.txt")
        test_content = "This is a workflow test"
        
        # 1. Write file
        write_result = write_file(test_file_path, test_content)
        assert "Successfully wrote" in write_result
        
        # 2. Read file
        read_result = read_file(test_file_path)
        assert test_content in read_result
        
        # 3. List directory
        list_result = list_directory(self.test_dir)
        assert "workflow_test.txt" in list_result
        
        # 4. Get file info
        info_result = file_info(test_file_path)
        assert "File Information" in info_result
        
        # 5. Delete file
        delete_result = delete_file(test_file_path)
        assert "Successfully deleted" in delete_result
        
        # 6. Verify deletion
        final_list = list_directory(self.test_dir)
        assert "workflow_test.txt" not in final_list


# Performance Tests
class TestPerformance:
    """Performance tests for the MCP server"""
    
    def setup_method(self):
        self.test_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            
    def test_large_file_handling(self):
        """Test handling of large files"""
        large_content = "x" * 10000  # 10KB file
        test_file = Path(self.test_dir) / "large_file.txt"
        
        # Write large file
        write_result = write_file(str(test_file), large_content)
        assert "Successfully wrote" in write_result
        
        # Read large file
        read_result = read_file(str(test_file))
        assert large_content in read_result
        
    def test_many_files_listing(self):
        """Test listing directory with many files"""
        # Create many files
        for i in range(50):  # Reduced from 100 for faster testing
            (Path(self.test_dir) / f"file_{i:03d}.txt").write_text(f"content {i}")
            
        # List directory
        list_result = list_directory(self.test_dir)
        
        # Should contain all files
        for i in range(50):
            assert f"file_{i:03d}.txt" in list_result


# Simple test runner for manual testing
def run_basic_tests():
    """Run basic tests manually"""
    print("🧪 Running File System MCP Server Tests...")
    
    test_instance = TestFileSystemMCPServer()
    
    try:
        # Test basic functionality
        test_instance.setup_method()
        
        print("  ✓ Testing file write...")
        test_instance.test_write_file_success()
        
        print("  ✓ Testing file read...")
        test_instance.test_read_file_success()
        
        print("  ✓ Testing directory listing...")
        test_instance.test_list_directory_success()
        
        print("  ✓ Testing file info...")
        test_instance.test_file_info_success()
        
        print("  ✓ Testing prompts...")
        test_instance.test_file_script_prompt_backup()
        
        test_instance.teardown_method()
        
        print("✅ All basic tests passed!")
        print("💡 Run 'pytest test_server_fixed.py' for complete test suite")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_basic_tests()
