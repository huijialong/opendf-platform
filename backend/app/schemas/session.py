from pydantic import BaseModel, Field


class MockSampleIn(BaseModel):
    task_id: int | None = None
    device_sn: str | None = None
    duration_sec: float = Field(default=10.0, ge=2.0, le=30.0)
