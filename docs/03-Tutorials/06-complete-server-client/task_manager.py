"""
Task Manager Module

Handles all task-related business logic and operations.
"""

from datetime import datetime, date
from typing import Optional, Dict, Any, List
from storage import StorageManager


class TaskManager:
    """Manages task operations and business logic."""
    
    def __init__(self):
        """Initialize task manager with storage."""
        self.storage = StorageManager()
    
    def create_task(self, title: str, description: str = "", priority: str = "medium", 
                   due_date: date = None, project: str = "") -> Dict[str, Any]:
        """Create a new task."""
        if priority not in ["low", "medium", "high"]:
            raise ValueError("Priority must be 'low', 'medium', or 'high'")
        
        task_data = {
            "title": title,
            "description": description,
            "priority": priority,
            "due_date": due_date.isoformat() if due_date else None,
            "project": project,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "completed_at": None
        }
        
        task_id = self.storage.create_task(task_data)
        task_data["id"] = task_id
        
        return task_data
    
    def get_task(self, task_id: int) -> Dict[str, Any]:
        """Get a specific task by ID."""
        task = self.storage.get_task(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")
        
        # Add notes to task
        task["notes"] = self.storage.get_task_notes(task_id)
        
        return task
    
    def get_tasks(self, status: str = None, priority: str = None, 
                  project: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """Get tasks with optional filtering."""
        return self.storage.get_tasks(
            status=status,
            priority=priority,
            project=project,
            limit=limit
        )
    
    def update_task(self, task_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing task."""
        # Validate task exists
        existing_task = self.get_task(task_id)
        
        # Validate priority if being updated
        if "priority" in updates and updates["priority"] not in ["low", "medium", "high"]:
            raise ValueError("Priority must be 'low', 'medium', or 'high'")
        
        # Convert date objects to strings for storage
        if "due_date" in updates and isinstance(updates["due_date"], date):
            updates["due_date"] = updates["due_date"].isoformat()
        
        self.storage.update_task(task_id, updates)
        
        # Return updated task
        return self.get_task(task_id)
    
    def complete_task(self, task_id: int) -> Dict[str, Any]:
        """Mark a task as completed."""
        updates = {
            "status": "completed",
            "completed_at": datetime.now().isoformat()
        }
        
        return self.update_task(task_id, updates)
    
    def delete_task(self, task_id: int) -> Dict[str, Any]:
        """Delete a task."""
        # Get task before deletion for return value
        task = self.get_task(task_id)
        
        self.storage.delete_task(task_id)
        
        return task
    
    def add_note(self, task_id: int, note: str) -> Dict[str, Any]:
        """Add a note to a task."""
        # Validate task exists
        task = self.get_task(task_id)
        
        note_data = {
            "task_id": task_id,
            "content": note,
            "created_at": datetime.now().isoformat()
        }
        
        self.storage.add_task_note(note_data)
        
        return task
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """Get task statistics and analytics."""
        all_tasks = self.get_tasks()
        
        stats = {
            "total_tasks": len(all_tasks),
            "pending_tasks": len([t for t in all_tasks if t["status"] == "pending"]),
            "completed_tasks": len([t for t in all_tasks if t["status"] == "completed"]),
            "high_priority": len([t for t in all_tasks if t["priority"] == "high"]),
            "medium_priority": len([t for t in all_tasks if t["priority"] == "medium"]),
            "low_priority": len([t for t in all_tasks if t["priority"] == "low"]),
            "overdue_tasks": 0,
            "due_today": 0,
            "projects": set()
        }
        
        today = date.today()
        
        for task in all_tasks:
            if task["project"]:
                stats["projects"].add(task["project"])
            
            if task["due_date"] and task["status"] == "pending":
                task_due_date = datetime.strptime(task["due_date"], "%Y-%m-%d").date()
                if task_due_date < today:
                    stats["overdue_tasks"] += 1
                elif task_due_date == today:
                    stats["due_today"] += 1
        
        stats["projects"] = list(stats["projects"])
        stats["project_count"] = len(stats["projects"])
        
        return stats
    
    def get_tasks_due_soon(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get tasks due within specified number of days."""
        all_tasks = self.get_tasks(status="pending")
        due_soon = []
        
        cutoff_date = date.today() + datetime.timedelta(days=days)
        
        for task in all_tasks:
            if task["due_date"]:
                task_due_date = datetime.strptime(task["due_date"], "%Y-%m-%d").date()
                if task_due_date <= cutoff_date:
                    due_soon.append(task)
        
        # Sort by due date
        due_soon.sort(key=lambda t: t["due_date"])
        
        return due_soon
    
    def search_tasks(self, query: str) -> List[Dict[str, Any]]:
        """Search tasks by title, description, or project."""
        all_tasks = self.get_tasks()
        query_lower = query.lower()
        
        matching_tasks = []
        
        for task in all_tasks:
            if (query_lower in task["title"].lower() or
                query_lower in task.get("description", "").lower() or
                query_lower in task.get("project", "").lower()):
                matching_tasks.append(task)
        
        return matching_tasks
