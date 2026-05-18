import uuid
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    payload: dict[str, Any] | None = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    phase: Optional[str] = None
    result: dict[str, Any] | None = None
    error: Optional[str] = None


class TaskRead(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    status: TaskStatus
    phase: Optional[str] = None
    payload: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}