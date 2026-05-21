import uuid
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel
from datetime import datetime


class TaskStatus(str, Enum):
    pending = "pending"
    claimed = "claimed"
    doing = "doing"
    review = "review"
    done = "done"
    failed = "failed"


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    phase: Optional[str] = None
    payload: dict[str, Any] | None = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    phase: Optional[str] = None
    result: dict[str, Any] | None = None
    error: Optional[str] = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskRead(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    status: TaskStatus
    phase: Optional[str] = None
    payload: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    last_retry_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    runner_id: str | None = None
    runtime_id: str | None = None
    claimed_at: datetime | None = None
    claim_state: str | None = None
    claim_attempts: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
