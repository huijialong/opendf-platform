from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DeviceIn(BaseModel):
    device_sn: str = Field(..., min_length=1, max_length=64)
    device_type: str
    name: str = Field(..., min_length=1, max_length=128)
    status: str = "ONLINE"
    meta_json: dict[str, Any] = Field(default_factory=dict)


class DeviceUpdate(BaseModel):
    device_type: str | None = None
    name: str | None = None
    status: str | None = None
    meta_json: dict[str, Any] | None = None


class TaskIn(BaseModel):
    task_code: str | None = None
    title: str = Field(..., min_length=1, max_length=128)
    scene_category: str | None = None
    priority: str = "MEDIUM"
    status: str = "PENDING"
    assignee: str | None = None
    sample_target: int = 50


class TaskUpdate(BaseModel):
    title: str | None = None
    scene_category: str | None = None
    priority: str | None = None
    status: str | None = None
    assignee: str | None = None
    sample_target: int | None = None
    completed_samples: int | None = None


class AssignIn(BaseModel):
    assignee: str = Field(..., min_length=1, max_length=64)
    task_ids: list[int] = Field(..., min_length=1)


class TaskOut(BaseModel):
    id: int
    task_code: str | None
    title: str
    scene_category: str | None
    priority: str | None
    status: str | None
    assignee: str | None
    sample_target: int | None
    completed_samples: int | None
    progress: float
    created_at: datetime | None

    model_config = {"from_attributes": True}
