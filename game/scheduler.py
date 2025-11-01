"""Centralized scheduler for game timers"""
import time
from dataclasses import dataclass, field
from typing import Dict, Callable, Optional
from game.state import GameState


@dataclass
class Task:
    """Represents a scheduled task"""
    id: str
    end_time: float  # Absolute timestamp when task completes
    callback: Callable
    label: str
    state: Optional[GameState] = None  # State snapshot when task was created (for persistence)


class Scheduler:
    """Manages scheduled tasks with persistence"""
    
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
    
    def register_task(self, task_id: str, duration_seconds: float, callback: Callable, 
                     label: str, state: Optional[GameState] = None) -> str:
        """
        Register a new task.
        
        Args:
            task_id: Unique identifier for the task
            duration_seconds: How long the task takes (from now)
            callback: Function to call when task completes
            label: Human-readable label for the task
            state: Optional state snapshot for persistence
            
        Returns:
            The task_id (same as input)
        """
        end_time = time.time() + duration_seconds
        self.tasks[task_id] = Task(
            id=task_id,
            end_time=end_time,
            callback=callback,
            label=label,
            state=state
        )
        return task_id
    
    def cancel_task(self, task_id: str):
        """Cancel a scheduled task"""
        if task_id in self.tasks:
            del self.tasks[task_id]
    
    def get_remaining_time(self, task_id: str) -> Optional[float]:
        """Get remaining time for a task in seconds, or None if not found/expired"""
        if task_id not in self.tasks:
            return None
        task = self.tasks[task_id]
        remaining = task.end_time - time.time()
        return max(0.0, remaining) if remaining > 0 else None
    
    def tick(self) -> list:
        """
        Check for completed tasks and call their callbacks.
        
        Returns:
            List of completed task IDs
        """
        completed = []
        now = time.time()
        
        for task_id, task in list(self.tasks.items()):
            if now >= task.end_time:
                completed.append(task_id)
                # Remove before calling callback (in case callback wants to register new task)
                del self.tasks[task_id]
                try:
                    task.callback()
                except Exception as e:
                    # Log error but don't crash
                    print(f"Error in scheduled task {task_id} callback: {e}")
        
        return completed
    
    def get_all_tasks(self) -> Dict[str, Dict]:
        """Get all active tasks for serialization"""
        return {
            task_id: {
                "end_time": task.end_time,
                "label": task.label
            }
            for task_id, task in self.tasks.items()
        }
    
    def restore_tasks(self, tasks_dict: Dict[str, Dict], callbacks: Dict[str, Callable]):
        """
        Restore tasks from serialized data.
        
        Args:
            tasks_dict: Dictionary of {task_id: {end_time, label}}
            callbacks: Dictionary of {task_id: callback_function}
        """
        now = time.time()
        for task_id, task_data in tasks_dict.items():
            end_time = task_data["end_time"]
            # Only restore if task hasn't expired
            if end_time > now and task_id in callbacks:
                self.tasks[task_id] = Task(
                    id=task_id,
                    end_time=end_time,
                    callback=callbacks[task_id],
                    label=task_data.get("label", "Unknown")
                )

