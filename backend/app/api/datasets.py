from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import EXPORT_DIR, RAW_DIR
from app.db.database import get_db
from app.db.models import Task
from app.schemas.annotation import ExportIn
from app.services.exporter import export_task
from app.services.present import ok

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/export")
def export_dataset(payload: ExportIn, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == payload.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    try:
        result = export_task(db, task, payload.format, RAW_DIR, EXPORT_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(result, "数据包已生成")


@router.get("/exports")
def list_exports():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for path in sorted(EXPORT_DIR.glob("*.zip"), key=lambda item: item.stat().st_mtime, reverse=True):
        files.append(
            {
                "filename": path.name,
                "download_url": f"/storage/export/{path.name}",
                "size_bytes": path.stat().st_size,
                "modified_at": int(path.stat().st_mtime),
            }
        )
    return ok({"items": files, "total": len(files)})
