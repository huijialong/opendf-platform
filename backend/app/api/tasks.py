from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import PRIORITIES, TASK_STATUSES
from app.db.database import get_db
from app.db.models import Task
from app.schemas.task import AssignIn, TaskIn, TaskUpdate
from app.services.present import ok, task_dict

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get(db: Session, task_id: int) -> Task:
    row = db.query(Task).filter(Task.id == task_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="任务不存在")
    return row


def _next_code(db: Session) -> str:
    latest = db.query(Task).order_by(Task.id.desc()).first()
    seq = (latest.id + 1) if latest else 1
    return f"TSK-{seq:04d}-{uuid4().hex[:4].upper()}"


@router.get("")
def list_tasks(
    keyword: str | None = None,
    status: str | None = None,
    scene_category: str | None = None,
    priority: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Task)
    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.filter((Task.title.like(like)) | (Task.task_code.like(like)))
    if status:
        query = query.filter(Task.status == status)
    if scene_category:
        query = query.filter(Task.scene_category == scene_category)
    if priority:
        query = query.filter(Task.priority == priority)
    total = query.count()
    rows = query.order_by(Task.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return ok({"items": [task_dict(row) for row in rows], "total": total, "page": page})


@router.post("")
def create_task(payload: TaskIn, db: Session = Depends(get_db)):
    if payload.priority not in PRIORITIES:
        raise HTTPException(status_code=400, detail="优先级不合法")
    if payload.status not in TASK_STATUSES:
        raise HTTPException(status_code=400, detail="状态不合法")
    code = (payload.task_code or "").strip() or _next_code(db)
    if db.query(Task).filter(Task.task_code == code).first():
        raise HTTPException(status_code=400, detail="任务编号已存在")
    row = Task(
        task_code=code,
        title=payload.title.strip(),
        scene_category=payload.scene_category,
        priority=payload.priority,
        status=payload.status,
        assignee=payload.assignee,
        sample_target=payload.sample_target,
        completed_samples=0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(task_dict(row), "任务已创建")


@router.get("/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db)):
    return ok(task_dict(_get(db, task_id)))


@router.put("/{task_id}")
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    row = _get(db, task_id)
    data = payload.model_dump(exclude_unset=True)
    if "priority" in data and data["priority"] not in PRIORITIES:
        raise HTTPException(status_code=400, detail="优先级不合法")
    if "status" in data and data["status"] not in TASK_STATUSES:
        raise HTTPException(status_code=400, detail="状态不合法")
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ok(task_dict(row), "任务已更新")


@router.post("/assign")
def assign_tasks(payload: AssignIn, db: Session = Depends(get_db)):
    rows = db.query(Task).filter(Task.id.in_(payload.task_ids)).all()
    if not rows:
        raise HTTPException(status_code=404, detail="没有匹配的任务")
    for row in rows:
        row.assignee = payload.assignee.strip()
    db.commit()
    return ok({"updated": [row.id for row in rows], "assignee": payload.assignee}, "已批量指派")


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    row = _get(db, task_id)
    db.delete(row)
    db.commit()
    return ok({"id": task_id}, "任务已删除")
