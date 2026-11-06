from typing import Any

from pydantic import BaseModel, Field


class PipelineStep(BaseModel):
    step: int
    name: str
    desc: str


class DashboardStats(BaseModel):
    device_count: int
    storage_bytes: int
    storage_formatted: str
    active_tasks: int
    dataset_count: int
    pipeline_steps: list[PipelineStep]
    recent_tasks: list[dict[str, Any]] = Field(default_factory=list)
    recent_sessions: list[dict[str, Any]] = Field(default_factory=list)
    activities: list[dict[str, Any]] = Field(default_factory=list)


class ApiEnvelope(BaseModel):
    code: int = 200
    message: str = "ok"
    data: Any = None
