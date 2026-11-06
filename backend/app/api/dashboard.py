from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import PIPELINE_STEPS, PLATFORM_STATS
from app.db.database import get_db
from app.db.models import AnnotationSegment, CaptureSession, Task
from app.services.present import iso, ok, session_dict, task_dict

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    tasks = db.query(Task).order_by(Task.id.desc()).limit(6).all()
    sessions = db.query(CaptureSession).order_by(CaptureSession.id.desc()).limit(6).all()
    segments = (
        db.query(AnnotationSegment).order_by(AnnotationSegment.id.desc()).limit(6).all()
    )
    activities = []
    for session in sessions:
        activities.append(
            {
                "time": iso(session.created_at),
                "kind": "session",
                "text": f"会话 {session.session_uuid[:8]} 已入库，设备 {session.device_sn}",
            }
        )
    for seg in segments:
        activities.append(
            {
                "time": iso(seg.created_at),
                "kind": "segment",
                "text": f"动作切片 {seg.action_label} · {seg.review_status}",
            }
        )
    activities.sort(key=lambda item: item["time"] or "", reverse=True)

    data = {
        **PLATFORM_STATS,
        "pipeline_steps": PIPELINE_STEPS,
        "recent_tasks": [task_dict(row) for row in tasks],
        "recent_sessions": [session_dict(row) for row in sessions],
        "activities": activities[:8],
    }
    return ok(data)
