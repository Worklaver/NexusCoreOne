import logging
import asyncio
import json
import os
from datetime import datetime
import redis
from sqlalchemy import select, update
from app.database.models import Task, TaskStatus, Account, AccountStatus
from app.database.db_session import async_session_factory, get_sync_session

# Configure logging
logger = logging.getLogger(__name__)

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Queue names
TASK_QUEUE = "nexuscore:tasks"
TASK_PROCESSING = "nexuscore:processing"

async def queue_task(task_id):
    """
    Add a task to the processing queue
    
    Args:
        task_id (int): Task ID to queue
    """
    try:
        # Get task details
        async with async_session_factory() as db:
            query = select(Task).where(Task.id == task_id)
            result = await db.execute(query)
            task = result.scalar_one_or_none()
            
            if not task:
                logger.error(f"Task {task_id} not found")
                return False
            
            if task.status != TaskStatus.PENDING:
                logger.warning(f"Task {task_id} is not in PENDING status")
                return False
            
            # Add to Redis queue
            task_data = {
                "task_id": task.id,
                "task_type": task.task_type.value,
                "user_id": task.user_id,
                "params": task.params,
                "queued_at": datetime.utcnow().isoformat()
            }
            
            redis_client.rpush(TASK_QUEUE, json.dumps(task_data))
            logger.info(f"Task {task_id} queued for processing")
            return True
            
    except Exception as e:
        logger.error(f"Error queueing task {task_id}: {e}")
        return False

def get_next_task():
    """
    Get the next task from the queue
    
    Returns:
        dict: Task data or None if no tasks
    """
    try:
        # Move task from queue to processing list
        result = redis_client.blpop(TASK_QUEUE, timeout=1)
        if not result:
            return None
        
        _, task_json = result
        task_data = json.loads(task_json)
        
        # Mark as processing
        task_data["processing_started"] = datetime.utcnow().isoformat()
        redis_client.hset(TASK_PROCESSING, task_data["task_id"], json.dumps(task_data))
        
        return task_data
        
    except Exception as e:
        logger.error(f"Error getting next task: {e}")
        return None

def task_completed(task_id, success=True, error=None):
    """
    Mark a task as completed or failed
    
    Args:
        task_id (int): Task ID
        success (bool): Whether task completed successfully
        error (str): Error message if task failed
    """
    try:
        # Remove from processing list
        redis_client.hdel(TASK_PROCESSING, task_id)
        
        # Update task in database
        with get_sync_session() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            
            if task:
                task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                task.completed_at = datetime.utcnow()
                
                if not success and error:
                    task.error = error
                    
                db.commit()
                logger.info(f"Task {task_id} marked as {'completed' if success else 'failed'}")
                return True
            else:
                logger.error(f"Task {task_id} not found for completion update")
                return False
                
    except Exception as e:
        logger.error(f"Error marking task {task_id} as completed: {e}")
        return False

def update_task_progress(task_id, progress, total_items=None, log_entry=None):
    """
    Update task progress
    
    Args:
        task_id (int): Task ID
        progress (int): Progress percentage (0-100)
        total_items (int): Total items to process
        log_entry (str): Log entry to append
    """
    try:
        with get_sync_session() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            
            if task:
                task.progress = progress
                
                if total_items is not None:
                    task.total_items = total_items
                
                if log_entry:
                    if task.logs:
                        task.logs += f"\n{datetime.utcnow().isoformat()} - {log_entry}"
                    else:
                        task.logs = f"{datetime.utcnow().isoformat()} - {log_entry}"
                
                db.commit()
                logger.debug(f"Task {task_id} progress updated: {progress}%")
                return True
            else:
                logger.error(f"Task {task_id} not found for progress update")
                return False
                
    except Exception as e:
        logger.error(f"Error updating task {task_id} progress: {e}")
        return False

async def get_available_account_for_task(task_type, user_id):
    """
    Get an available account for a specific task type
    
    Args:
        task_type (str): Task type
        user_id (int): User ID
        
    Returns:
        Account: Available account or None
    """
    try:
        async with async_session_factory() as db:
            # Get all active accounts for this user
            query = select(Account).where(
                Account.user_id == user_id,
                Account.is_active == True,
                Account.status == AccountStatus.ACTIVE
            )
            
            # Filter by cooldown
            query = query.where(
                (Account.cooldown_until.is_(None)) | 
                (Account.cooldown_until < datetime.utcnow())
            )
            
            # Sort by usage count for this task type
            if task_type in [TaskType.PARSE_MEMBERS, TaskType.PARSE_WRITERS, TaskType.PARSE_COMMENTERS]:
                query = query.order_by(Account.daily_parse_count)
            elif task_type == TaskType.INVITE_USERS:
                query = query.order_by(Account.daily_invite_count)
            elif task_type == TaskType.LIKE_COMMENTS:
                query = query.order_by(Account.daily_like_count)
            
            # Also sort by last used
            query = query.order_by(Account.last_used.nullsfirst())
            
            # Get the first available account
            result = await db.execute(query)
            account = result.scalar_one_or_none()
            
            return account
    
    except Exception as e:
        logger.error(f"Error getting available account: {e}")
        return None