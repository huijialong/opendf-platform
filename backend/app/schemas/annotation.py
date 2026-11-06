from pydantic import BaseModel, Field


class SegmentIn(BaseModel):
    action_label: str
    start_time: float = Field(..., ge=0)
    end_time: float = Field(..., ge=0)
    quality_score: int = Field(default=5, ge=1, le=5)
    notes: str | None = None


class SegmentBatchIn(BaseModel):
    session_id: int
    segments: list[SegmentIn]


class ReviewDecisionIn(BaseModel):
    segment_id: int
    decision: str
    reason: str | None = None


class ExportIn(BaseModel):
    task_id: int
    format: str = "lerobot"
