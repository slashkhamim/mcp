"""
Storage Manager Module

Handles data persistence using SQLite database.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path


class StorageManager:
    """Manages data persistence for tasks and notes."""
    
    def __init__(self, db_path: str = "tasks.db"):
        """Initialize storage manager with database."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'pending',
                    due_date TEXT,
                    project TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_notes_task_id ON task_notes(task_id)")
            
            conn.commit()
    
    def create_task(self, task_data: Dict[str, Any]) -> int:
        """Create a new task and return its ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO tasks (title, description, priority, status, due_date, project, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_data["title"],
                task_data["description"],
                task_data["priority"],
                task_data["status"],
                task_data["due_date"],
                task_data["project"],
                task_data["created_at"],
                task_data["completed_at"]
            ))
            
            return cursor.lastrowid
    
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def get_tasks(self, status: str = None, priority: str = None, 
                  project: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """Get tasks with optional filtering."""
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        
        if project:
            query += " AND project = ?"
            params.append(project)
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def update_task(self, task_id: int, updates: Dict[str, Any]):
        """Update an existing task."""
        if not updates:
            return
        
        # Build dynamic update query
        set_clauses = []
        params = []
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            params.append(value)
        
        params.append(task_id)
        
        query = f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = ?"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query, params)
    
    def delete_task(self, task_id: int):
        """Delete a task and its notes."""
        with sqlite3.connect(self.db_path) as conn:
            # Delete notes first (foreign key constraint)
            conn.execute("DELETE FROM task_notes WHERE task_id = ?", (task_id,))
            # Delete task
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    
    def add_task_note(self, note_data: Dict[str, Any]) -> int:
        """Add a note to a task."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO task_notes (task_id, content, created_at)
                VALUES (?, ?, ?)
            """, (
                note_data["task_id"],
                note_data["content"],
                note_data["created_at"]
            ))
            
            return cursor.lastrowid
    
    def get_task_notes(self, task_id: int) -> List[Dict[str, Any]]:
        """Get all notes for a specific task."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM task_notes 
                WHERE task_id = ? 
                ORDER BY created_at ASC
            """, (task_id,))
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            stats = {}
            
            # Task counts
            cursor = conn.execute("SELECT COUNT(*) FROM tasks")
            stats["total_tasks"] = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
            stats["pending_tasks"] = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
            stats["completed_tasks"] = cursor.fetchone()[0]
            
            # Note counts
            cursor = conn.execute("SELECT COUNT(*) FROM task_notes")
            stats["total_notes"] = cursor.fetchone()[0]
            
            # Database size
            db_path = Path(self.db_path)
            if db_path.exists():
                stats["database_size_bytes"] = db_path.stat().st_size
            else:
                stats["database_size_bytes"] = 0
            
            return stats
    
    def backup_database(self, backup_path: str = None) -> str:
        """Create a backup of the database."""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"tasks_backup_{timestamp}.db"
        
        # Simple file copy for SQLite
        import shutil
        shutil.copy2(self.db_path, backup_path)
        
        return backup_path
    
    def restore_database(self, backup_path: str):
        """Restore database from backup."""
        import shutil
        shutil.copy2(backup_path, self.db_path)
        
        # Reinitialize to ensure schema is up to date
        self.init_database()
    
    def search_tasks(self, query: str) -> List[Dict[str, Any]]:
        """Search tasks by title, description, or project."""
        search_query = f"%{query}%"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM tasks 
                WHERE title LIKE ? OR description LIKE ? OR project LIKE ?
                ORDER BY created_at DESC
            """, (search_query, search_query, search_query))
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def cleanup_completed_tasks(self, days_old: int = 30):
        """Remove completed tasks older than specified days."""
        cutoff_date = (datetime.now() - datetime.timedelta(days=days_old)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Get tasks to be deleted for logging
            cursor = conn.execute("""
                SELECT id, title FROM tasks 
                WHERE status = 'completed' AND completed_at < ?
            """, (cutoff_date,))
            tasks_to_delete = cursor.fetchall()
            
            # Delete the tasks (notes will be deleted by foreign key constraint)
            conn.execute("""
                DELETE FROM tasks 
                WHERE status = 'completed' AND completed_at < ?
            """, (cutoff_date,))
            
            return len(tasks_to_delete)
