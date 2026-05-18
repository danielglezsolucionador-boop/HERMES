new_content = '''import uuid
from enum import Enum
from typing import Any
from pydantic import BaseModel
from datetime import datetime


class TaskStatus(str, Enum):
    pending = "pending"
    doing = "doing"
    review = "review"
    done = "done"
    failed = "failed"


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    phase: str | None = None
    payload: dict[str, Any] | None = None


class TaskRead(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    phase: str | None
    payload: dict[str, Any] | None
    result: dict[str, Any] | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
'''

open('app/schemas/task.py', 'w', encoding='utf-8').write(new_content)
print('OK - schemas/task.py actualizado')