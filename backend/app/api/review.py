from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.config import REVIEW_DECISIONS
from app.db.database import get_db
from app.db.models import AnnotationSegment, CaptureSession
from app.schemas.annotation import ReviewDecisionIn
from app.services.present import ok, segment_dict

router = APIRouter(prefix="/review", tags=["review"])


@router.get("/queue")
def review_queue(
    status: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(AnnotationSegment).options(
        joinedload(AnnotationSegment.session).joinedload(CaptureSession.task)
    )
    if status:
        query = query.filter(AnnotationSegment.review_status == status)
    total = query.count()
    rows = (
        query.order_by(AnnotationSegment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for row in rows:
        session = row.session
        task = session.task if session else None
        item = segment_dict(row)
        item["session_uuid"] = session.session_uuid if session else None
        item["task_title"] = task.title if task else None
        item["task_code"] = task.task_code if task else None
        item["video_url"] = (
            f"/storage/raw/{session.video_filename}" if session and session.video_filename else None
        )
        items.append(item)
    pending = db.query(AnnotationSegment).filter(AnnotationSegment.review_status == "PENDING").count()
    approved = db.query(AnnotationSegment).filter(AnnotationSegment.review_status == "APPROVED").count()
    rejected = db.query(AnnotationSegment).filter(AnnotationSegment.review_status == "REJECTED").count()
    decided = approved + rejected
    return ok(
        {
            "items": items,
            "total": total,
            "page": page,
            "summary": {
                "pending": pending,
                "approved": approved,
                "rejected": rejected,
                "pass_rate": round(approved / decided * 100, 1) if decided else 0,
            },
        }
    )


@router.post("/decision")
def review_decision(payload: ReviewDecisionIn, db: Session = Depends(get_db)):
    decision = payload.decision.strip().upper()
    if decision not in REVIEW_DECISIONS:
        raise HTTPException(status_code=400, detail="decision 仅支持 APPROVED / REJECTED")
    reason = (payload.reason or "").strip()
    if decision == "REJECTED" and not reason:
        raise HTTPException(status_code=400, detail="驳回时必须填写问题描述")
    row = (
        db.query(AnnotationSegment)
        .options(joinedload(AnnotationSegment.session))
        .filter(AnnotationSegment.id == payload.segment_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="标注切片不存在")
    row.review_status = decision
    row.reject_reason = reason if decision == "REJECTED" else None
    session = row.session
    if session:
        siblings = (
            db.query(AnnotationSegment)
            .filter(AnnotationSegment.session_id == session.id)
            .all()
        )
        session.is_reviewed = bool(siblings) and all(seg.review_status == "APPROVED" for seg in siblings)
        if session.task and decision == "REJECTED":
            session.task.status = "ANNOTATING"
        elif session.task and session.is_reviewed:
            session.task.status = "DONE"
    db.commit()
    db.refresh(row)
    return ok(segment_dict(row), "审核结论已提交")
