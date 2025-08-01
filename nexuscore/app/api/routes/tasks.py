from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
import logging
from datetime import datetime

from app.database.db_session import async_session_factory
from app.database.models import Task, TaskType, TaskStatus, User
from app.api.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    TaskResultResponse
)
from app.worker.task_queue import queue_task

router = APIRouter()
logger = logging.getLogger(__name__)

# Get database session dependency
async def get_db():
    db = async_session_factory()
    try:
        yield db
    finally:
        await db.close()

@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all tasks with optional filtering
    """
    query = select(Task)
    
    # Apply filters
    if status:
        try:
            task_status = TaskStatus(status)
            query = query.where(Task.status == task_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid task status: {status}"
            )
    
    if task_type:
        try:
            task_type_enum = TaskType(task_type)
            query = query.where(Task.task_type == task_type_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid task type: {task_type}"
            )
    
    if user_id:
        query = query.where(Task.user_id == user_id)
    
    # Execute query
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return tasks

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new task
    """
    try:
        # Check if user exists
        query = select(User).where(User.id == task_data.user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {task_data.user_id} not found"
            )
        
        # Validate task type
        try:
            task_type_enum = TaskType(task_data.task_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid task type: {task_data.task_type}"
            )
        
        # Create new task
        new_task = Task(
            user_id=task_data.user_id,
            task_type=task_type_enum,
            params=task_data.params,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            progress=0
        )
        
        db.add(new_task)
        await db.commit()
        await db.refresh(new_task)
        
        # Queue task for processing
        background_tasks.add_task(queue_task, new_task.id)
        
        return new_task
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating task: {str(e)}"
        )

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get task details by ID
    """
    try:
        query = select(Task).where(Task.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving task: {str(e)}"
        )

@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a running task
    """
    try:
        query = select(Task).where(Task.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        # Check if task can be cancelled
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Task with ID {task_id} cannot be cancelled (status: {task.status})"
            )
        
        # Update task status
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(task)
        
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error cancelling task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelling task: {str(e)}"
        )

@router.get("/{task_id}/results", response_model=List[TaskResultResponse])
async def get_task_results(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get results of a completed task
    """
    try:
        # Check if task exists
        task_query = select(Task).where(Task.id == task_id)
        result = await db.execute(task_query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        
        # Check if task is completed
        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Task with ID {task_id} is not completed (status: {task.status})"
            )
        
        # Get results
        from app.database.models import TaskResult
        results_query = select(TaskResult).where(TaskResult.task_id == task_id)
        results = await db.execute(results_query)
        task_results = results.scalars().all()
        
        return task_results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task results for task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving task results: {str(e)}"
        )