from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class TaskType(str, Enum):
    PARSE_MEMBERS = "parse_members"
    PARSE_WRITERS = "parse_writers" 
    PARSE_COMMENTERS = "parse_commenters"
    INVITE_USERS = "invite_users"
    LIKE_COMMENTS = "like_comments"

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskCreate(BaseModel):
    user_id: int = Field(..., description="User ID who created this task")
    task_type: str = Field(..., description="Type of task")
    params: Dict[str, Any] = Field(..., description="Task parameters")

class TaskUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Task status")
    progress: Optional[int] = Field(None, description="Task progress (0-100)")
    total_items: Optional[int] = Field(None, description="Total items to process")
    error: Optional[str] = Field(None, description="Error message if task failed")
    logs: Optional[str] = Field(None, description="Task logs")

class TaskResponse(BaseModel):
    id: int
    user_id: int
    task_type: str
    params: Dict[str, Any]
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_file: Optional[str] = None
    progress: int
    total_items: int
    error: Optional[str] = None
    logs: Optional[str] = None
    
    class Config:
        orm_mode = True

class TaskResultResponse(BaseModel):
    id: int
    task_id: int
    result_type: str
    file_path: str
    items_count: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class ParsedDataResponse(BaseModel):
    id: int
    task_id: int
    data_type: str
    username: Optional[str] = None
    user_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    parsed_at: datetime
    source: Optional[str] = None
    
    class Config:
        orm_mode = True