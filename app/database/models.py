from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SQLAEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class AccountStatus(str, Enum):
    ACTIVE = "active"
    COOLING_DOWN = "cooling_down"
    BANNED = "banned"
    NEEDS_VERIFICATION = "needs_verification"
    LIMITED = "limited"
    INACTIVE = "inactive"

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

class WorkerStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String(32), unique=True, nullable=False)
    username = Column(String(64), nullable=True)
    first_name = Column(String(64), nullable=True)
    last_name = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    role = Column(String(16), default="user")
    
    accounts = relationship("Account", back_populates="user")
    proxies = relationship("Proxy", back_populates="user")
    tasks = relationship("Task", back_populates="user")
    settings = relationship("Settings", back_populates="user", uselist=False)

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    phone = Column(String(32), nullable=False)
    api_id = Column(String(32), nullable=False)
    api_hash = Column(String(64), nullable=False)
    session_string = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime, nullable=True)
    cooldown_until = Column(DateTime, nullable=True)
    daily_parse_count = Column(Integer, default=0)
    daily_invite_count = Column(Integer, default=0)
    daily_like_count = Column(Integer, default=0)
    reset_counts_at = Column(DateTime, nullable=True)
    status = Column(SQLAEnum(AccountStatus), default=AccountStatus.ACTIVE)
    
    user = relationship("User", back_populates="accounts")
    proxy = relationship("AccountProxy", back_populates="account", uselist=False)

class Proxy(Base):
    __tablename__ = "proxies"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    proxy_string = Column(String(128), nullable=False)
    proxy_type = Column(String(16), nullable=False)
    is_active = Column(Boolean, default=True)
    last_checked = Column(DateTime, nullable=True)
    is_working = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="proxies")
    account_proxies = relationship("AccountProxy", back_populates="proxy")

class AccountProxy(Base):
    __tablename__ = "account_proxies"
    
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    proxy_id = Column(Integer, ForeignKey("proxies.id"), nullable=False)
    
    account = relationship("Account", back_populates="proxy")
    proxy = relationship("Proxy", back_populates="account_proxies")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_type = Column(SQLAEnum(TaskType), nullable=False)
    params = Column(JSON, nullable=False)
    status = Column(SQLAEnum(TaskStatus), default=TaskStatus.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    result_file = Column(String(256), nullable=True)
    progress = Column(Integer, default=0)
    total_items = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    logs = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="tasks")
    results = relationship("TaskResult", back_populates="task")
    parsed_data = relationship("ParsedData", back_populates="task")

class TaskWorker(Base):
    __tablename__ = "task_workers"
    
    id = Column(Integer, primary_key=True)
    worker_id = Column(String(64), nullable=False)
    status = Column(SQLAEnum(WorkerStatus), default=WorkerStatus.IDLE)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    current_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    processed_tasks = Column(Integer, default=0)

class TaskResult(Base):
    __tablename__ = "task_results"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    result_type = Column(String(32), nullable=False)
    file_path = Column(String(256), nullable=False)
    items_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    task = relationship("Task", back_populates="results")

class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    max_parse_per_account = Column(Integer, default=100)
    max_invite_per_account = Column(Integer, default=50)
    invite_delay_min = Column(Integer, default=30)  # seconds
    invite_delay_max = Column(Integer, default=60)  # seconds
    like_delay_min = Column(Integer, default=5)  # seconds
    like_delay_max = Column(Integer, default=15)  # seconds
    cooldown_hours = Column(Integer, default=4)
    auto_rotate_accounts = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="settings")

class RateLimiter(Base):
    __tablename__ = "rate_limiters"
    
    id = Column(Integer, primary_key=True)
    entity_type = Column(String(32), nullable=False)
    entity_id = Column(String(64), nullable=False)
    requests_count = Column(Integer, default=0)
    reset_at = Column(DateTime, nullable=False)
    max_requests = Column(Integer, nullable=False)

class ParsedData(Base):
    __tablename__ = "parsed_data"
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    data_type = Column(String(32), nullable=False)
    username = Column(String(64), nullable=True)
    user_id = Column(String(64), nullable=True)
    first_name = Column(String(64), nullable=True)
    last_name = Column(String(64), nullable=True)
    parsed_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(256), nullable=True)
    
    task = relationship("Task", back_populates="parsed_data")