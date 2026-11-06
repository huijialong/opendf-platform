import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import ACTION_LABELS, RAW_DIR
from app.db.database import get_db
from app.db.models import AnnotationSegment, CaptureSession
from app.schemas.annotation import SegmentBatchIn
from app.services.present import ok, segment_dict, session_dict

router = APIRouter(prefix="/annotation", tags=["annotation"])


def _load_session(db: Session, session_id: int) -> CaptureSession:
    row = db.query(CaptureSession).filter(CaptureSession.id == session_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="会话不存在")
    return row


@router.get("/session/{session_id}")
def get_annotation_session(session_id: int, db: Session = Depends(get_db)):
    row = _load_session(db, session_id)
    trajectory: list = []
    if row.trajectory_filename:
        path = RAW_DIR / row.trajectory_filename
        if path.exists():
            trajectory = json.loads(path.read_text(encoding="utf-8"))
    return ok(
        {
            "session": session_dict(row),
            "video_url": f"/storage/raw/{row.video_filename}" if row.video_filename else None,
            "trajectory": trajectory,
            "segments": [segment_dict(seg) for seg in row.segments],
        }
    )


@router.post("/segments")
def save_segments(payload: SegmentBatchIn, db: Session = Depends(get_db)):
    row = _load_session(db, payload.session_id)
    for item in payload.segments:
        label = item.action_label.strip().upper()
        if label not in ACTION_LABELS:
            raise HTTPException(status_code=400, detail=f"不支持的动作标签 {item.action_label}")
        if item.end_time <= item.start_time:
            raise HTTPException(status_code=400, detail="结束时间必须大于开始时间")
    row.segments.clear()
    for item in payload.segments:
        row.segments.append(
            AnnotationSegment(
                session_id=row.id,
                action_label=item.action_label.strip().upper(),
                start_time=round(item.start_time, 3),
                end_time=round(item.end_time, 3),
                quality_score=item.quality_score,
                notes=item.notes,
                review_status="PENDING",
            )
        )
    row.is_reviewed = False
    if row.task and payload.segments and row.task.status in {"PENDING", "COLLECTING", "CLEANING", "ANNOTATING"}:
        row.task.status = "REVIEWING"
    db.commit()
    db.refresh(row)
    return ok([segment_dict(seg) for seg in row.segments], "标注已保存")
