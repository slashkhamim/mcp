#!/usr/bin/env python3
"""
Complete Task Management MCP Server

A comprehensive MCP server that provides task management capabilities.
Demonstrates tools, resources, and prompts working together in a real-world application.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from mcp.server.fastmcp import FastMCP
from libs.task_manager import TaskManager
from libs.storage import StorageManager

# Create MCP server
mcp = FastMCP("TaskManager")

# Initialize components
task_manager = TaskManager()
storage = StorageManager()

# Task management tools
@mcp.tool()
def create_task(title: str, description: str = "", priority: str = "medium", due_date: str = "", project: str = "") -> str:
    """Create a new task with specified details"""
    try:
        # Parse due date if provided
        due_datetime = None
        if due_date:
            if due_date.lower() == "today":
                due_datetime = datetime.now().date()
            elif due_date.lower() == "tomorrow":
                due_datetime = (datetime.now() + timedelta(days=1)).date()
            else:
                try:
                    due_datetime = datetime.strptime(due_date, "%Y-%m-%d").date()
                except ValueError:
                    return f"Invalid date format. Use YYYY-MM-DD, 'today', or 'tomorrow'"
        
        task = task_manager.create_task(
            title=title,
            description=description,
            priority=priority.lower(),
            due_date=due_datetime,
            project=project
        )
        
        due_str = f", Due: {task['due_date']}" if task['due_date'] else ""
        project_str = f", Project: {task['project']}" if task['project'] else ""
        
        return f"✅ Created task: \"{task['title']}\" (Priority: {task['priority'].title()}{due_str}{project_str})"
    
    except Exception as e:
        return f"❌ Error creating task: {str(e)}"

@mcp.tool()
def list_tasks(status: str = "all", priority: str = "all", project: str = "", limit: int = 10) -> str:
    """List tasks with optional filtering"""
    try:
        tasks = task_manager.get_tasks(
            status=status if status != "all" else None,
            priority=priority if priority != "all" else None,
            project=project if project else None,
            limit=limit
        )
        
        if not tasks:
            return "📝 No tasks found matching your criteria"
        
        result = f"📋 Found {len(tasks)} task(s):\n"
        
        for task in tasks:
            status_icon = "✅" if task['status'] == 'completed' else "⏳"
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task['priority'], "⚪")
            
            result += f"{status_icon} {priority_icon} {task['title']}"
            
            if task['due_date']:
                due_date = datetime.strptime(task['due_date'], "%Y-%m-%d").date()
                if due_date == datetime.now().date():
                    result += " (Due: Today)"
                elif due_date < datetime.now().date():
                    result += " (Overdue!)"
                else:
                    result += f" (Due: {task['due_date']})"
            
            if task['project']:
                result += f" [{task['project']}]"
            
            result += "\n"
            
            if task['description']:
                result += f"   📄 {task['description']}\n"
        
        return result
    
    except Exception as e:
        return f"❌ Error listing tasks: {str(e)}"

@mcp.tool()
def complete_task(task_id: int = None, title: str = "") -> str:
    """Mark a task as completed"""
    try:
        if task_id:
            task = task_manager.complete_task(task_id)
        elif title:
            # Find task by title
            tasks = task_manager.get_tasks()
            matching_tasks = [t for t in tasks if title.lower() in t['title'].lower()]
            
            if not matching_tasks:
                return f"❌ No task found with title containing: {title}"
            
            if len(matching_tasks) > 1:
                result = f"❌ Multiple tasks found with '{title}':\n"
                for t in matching_tasks:
                    result += f"• {t['id']}: {t['title']}\n"
                result += "Please specify the task ID or be more specific with the title."
                return result
            
            task = task_manager.complete_task(matching_tasks[0]['id'])
        else:
            return "❌ Please provide either task_id or title"
        
        return f"🎉 Completed task: \"{task['title']}\""
    
    except Exception as e:
        return f"❌ Error completing task: {str(e)}"

@mcp.tool()
def update_task(task_id: int, title: str = "", description: str = "", priority: str = "", due_date: str = "", project: str = "") -> str:
    """Update an existing task"""
    try:
        updates = {}
        
        if title:
            updates['title'] = title
        if description:
            updates['description'] = description
        if priority:
            updates['priority'] = priority.lower()
        if due_date:
            if due_date.lower() == "today":
                updates['due_date'] = datetime.now().date()
            elif due_date.lower() == "tomorrow":
                updates['due_date'] = (datetime.now() + timedelta(days=1)).date()
            else:
                try:
                    updates['due_date'] = datetime.strptime(due_date, "%Y-%m-%d").date()
                except ValueError:
                    return f"Invalid date format. Use YYYY-MM-DD, 'today', or 'tomorrow'"
        if project:
            updates['project'] = project
        
        if not updates:
            return "❌ No updates provided"
        
        task = task_manager.update_task(task_id, updates)
        return f"📝 Updated task: \"{task['title']}\""
    
    except Exception as e:
        return f"❌ Error updating task: {str(e)}"

@mcp.tool()
def delete_task(task_id: int) -> str:
    """Delete a task"""
    try:
        task = task_manager.delete_task(task_id)
        return f"🗑️ Deleted task: \"{task['title']}\""
    except Exception as e:
        return f"❌ Error deleting task: {str(e)}"

@mcp.tool()
def add_note(task_id: int, note: str) -> str:
    """Add a note to a task"""
    try:
        task = task_manager.add_note(task_id, note)
        return f"📝 Added note to task: \"{task['title']}\""
    except Exception as e:
        return f"❌ Error adding note: {str(e)}"

@mcp.tool()
def get_task_details(task_id: int) -> str:
    """Get detailed information about a specific task"""
    try:
        task = task_manager.get_task(task_id)
        
        result = f"📋 Task Details:\n"
        result += f"ID: {task['id']}\n"
        result += f"Title: {task['title']}\n"
        result += f"Status: {task['status'].title()}\n"
        result += f"Priority: {task['priority'].title()}\n"
        result += f"Created: {task['created_at']}\n"
        
        if task['description']:
            result += f"Description: {task['description']}\n"
        if task['due_date']:
            result += f"Due Date: {task['due_date']}\n"
        if task['project']:
            result += f"Project: {task['project']}\n"
        if task['completed_at']:
            result += f"Completed: {task['completed_at']}\n"
        
        if task['notes']:
            result += f"\nNotes:\n"
            for note in task['notes']:
                result += f"• {note['created_at']}: {note['content']}\n"
        
        return result
    except Exception as e:
        return f"❌ Error getting task details: {str(e)}"

# Task data resources
@mcp.resource("tasks://all")
def get_all_tasks() -> str:
    """Get all tasks in the system"""
    try:
        tasks = task_manager.get_tasks()
        return json.dumps({
            "total_tasks": len(tasks),
            "tasks": tasks
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource("tasks://pending")
def get_pending_tasks() -> str:
    """Get all pending tasks"""
    try:
        tasks = task_manager.get_tasks(status="pending")
        return json.dumps({
            "pending_tasks": len(tasks),
            "tasks": tasks
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource("tasks://completed")
def get_completed_tasks() -> str:
    """Get all completed tasks"""
    try:
        tasks = task_manager.get_tasks(status="completed")
        return json.dumps({
            "completed_tasks": len(tasks),
            "tasks": tasks
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource("tasks://priority/{priority}")
def get_tasks_by_priority(priority: str) -> str:
    """Get tasks filtered by priority level"""
    try:
        tasks = task_manager.get_tasks(priority=priority.lower())
        return json.dumps({
            "priority": priority,
            "task_count": len(tasks),
            "tasks": tasks
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.resource("tasks://project/{project}")
def get_tasks_by_project(project: str) -> str:
    """Get tasks filtered by project"""
    try:
        import urllib.parse
        decoded_project = urllib.parse.unquote(project)
        tasks = task_manager.get_tasks(project=decoded_project)
        return json.dumps({
            "project": decoded_project,
            "task_count": len(tasks),
            "tasks": tasks
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

# Task planning and productivity prompts
@mcp.prompt()
def task_breakdown(task_description: str, complexity: str = "medium") -> str:
    """Break down a complex task into manageable subtasks"""
    complexity_levels = ["simple", "medium", "complex"]
    
    if complexity not in complexity_levels:
        return f"Unknown complexity: {complexity}. Available: {', '.join(complexity_levels)}"
    
    return f"""Break down this task into smaller, manageable subtasks:

Task: {task_description}
Complexity Level: {complexity}

Please provide:
1. 3-7 specific subtasks that are actionable
2. Estimated time for each subtask
3. Dependencies between subtasks
4. Priority order for completion
5. Any resources or tools needed
6. Potential challenges and solutions

Make each subtask:
- Specific and measurable
- Achievable in 1-4 hours
- Clear about what "done" looks like
- Independent when possible

Format as a numbered list with details."""

@mcp.prompt()
def project_plan(project_description: str, timeline: str = "1 month", team_size: str = "1") -> str:
    """Generate a comprehensive project plan"""
    return f"""Create a detailed project plan for:

Project: {project_description}
Timeline: {timeline}
Team Size: {team_size}

Please provide:
1. Project overview and objectives
2. Major milestones and deliverables
3. Task breakdown with time estimates
4. Resource requirements
5. Risk assessment and mitigation
6. Success criteria and metrics
7. Communication and review schedule

Structure the plan with:
- Clear phases and dependencies
- Realistic time estimates
- Buffer time for unexpected issues
- Regular checkpoints and reviews
- Deliverable specifications

Make it actionable and trackable."""

@mcp.prompt()
def daily_summary(date: str = "today") -> str:
    """Generate a daily task summary and planning prompt"""
    return f"""Create a daily summary and plan for {date}.

Based on current tasks, please provide:
1. Tasks completed today (achievements)
2. Tasks due today (priorities)
3. Overdue tasks (urgent items)
4. Tomorrow's focus areas
5. Weekly progress assessment
6. Productivity insights and suggestions
7. Time management recommendations

Include:
- Celebration of accomplishments
- Realistic planning for tomorrow
- Identification of blockers or challenges
- Suggestions for improvement
- Work-life balance considerations

Make it motivating and actionable."""

@mcp.prompt()
def productivity_tips(current_tasks: str, work_style: str = "focused") -> str:
    """Get personalized productivity suggestions"""
    work_styles = ["focused", "collaborative", "creative", "analytical", "flexible"]
    
    if work_style not in work_styles:
        return f"Unknown work style: {work_style}. Available: {', '.join(work_styles)}"
    
    return f"""Provide personalized productivity tips based on:

Current Tasks: {current_tasks}
Work Style: {work_style}

Please suggest:
1. Task prioritization strategies
2. Time management techniques
3. Focus and concentration methods
4. Tools and apps that might help
5. Workflow optimization ideas
6. Break and recovery strategies
7. Long-term productivity habits

Tailor suggestions to:
- The specific types of tasks
- The preferred work style
- Sustainable practices
- Measurable improvements

Make recommendations practical and immediately actionable."""

if __name__ == "__main__":
    # Run the server
    import asyncio
    mcp.run()
