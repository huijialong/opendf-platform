import json
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.config import RAW_DIR
from app.db.database import get_db
from app.db.models import CaptureSession, Device, Task
from app.schemas.session import MockSampleIn
from app.services.mock_generator import generate_mock_trajectory, generate_mock_video
from app.services.present import ok, session_dict

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _probe_mp4_duration(path: Path) -> float:
    data = path.read_bytes()
    idx = data.find(b"mvhd")
    if idx < 0 or idx + 32 > len(data):
        return 0.0
    version = data[idx + 4]
    if version == 0:
        timescale = int.from_bytes(data[idx + 16 : idx + 20], "big")
        duration = int.from_bytes(data[idx + 20 : idx + 24], "big")
    else:
        if idx + 40 > len(data):
            return 0.0
        timescale = int.from_bytes(data[idx + 28 : idx + 32], "big")
        duration = int.from_bytes(data[idx + 32 : idx + 40], "big")
    if not timescale:
        return 0.0
    return round(duration / timescale, 3)


async def _save_upload(upload: UploadFile, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(dest, "wb") as handle:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            await handle.write(chunk)


@router.get("")
def list_sessions(
    task_id: int | None = None,
    device_sn: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(CaptureSession)
    if task_id:
        query = query.filter(CaptureSession.task_id == task_id)
    if device_sn:
        query = query.filter(CaptureSession.device_sn == device_sn)
    total = query.count()
    rows = (
        query.order_by(CaptureSession.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ok({"items": [session_dict(row) for row in rows], "total": total, "page": page})


@router.get("/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)):
    row = db.query(CaptureSession).filter(CaptureSession.id == session_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="会话不存在")
    return ok(session_dict(row))


@router.post("/upload")
async def upload_session(
    task_id: int = Form(...),
    device_sn: str = Form(""),
    video_file: UploadFile | None = File(default=None),
    trajectory_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if video_file is None and trajectory_file is None:
        raise HTTPException(status_code=400, detail="至少上传视频或轨迹文件")

    token = uuid.uuid4().hex[:12]
    video_name = None
    traj_name = None
    duration = 0.0
    frames = 0

    if video_file is not None and video_file.filename:
        suffix = Path(video_file.filename).suffix.lower() or ".mp4"
        if suffix not in {".mp4", ".webm", ".mov"}:
            raise HTTPException(status_code=400, detail="视频仅支持 mp4 / webm / mov")
        video_name = f"{token}{suffix}"
        await _save_upload(video_file, RAW_DIR / video_name)
        if suffix == ".mp4":
            duration = _probe_mp4_duration(RAW_DIR / video_name)

    if trajectory_file is not None and trajectory_file.filename:
        suffix = Path(trajectory_file.filename).suffix.lower() or ".json"
        if suffix not in {".json", ".csv"}:
            raise HTTPException(status_code=400, detail="轨迹仅支持 json / csv")
        traj_name = f"{token}{suffix}"
        await _save_upload(trajectory_file, RAW_DIR / traj_name)
        if suffix == ".json":
            try:
                records = json.loads((RAW_DIR / traj_name).read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=400, detail="轨迹 JSON 无法解析") from exc
            if isinstance(records, list) and records:
                frames = len(records)
                last = records[-1]
                if isinstance(last, dict) and "timestamp" in last:
                    duration = duration or float(last["timestamp"])

    if frames == 0 and duration:
        frames = int(duration * 30)

    sn = device_sn.strip() or None
    if sn and not db.query(Device).filter(Device.device_sn == sn).first():
        raise HTTPException(status_code=400, detail="设备序列号未登记")

    row = CaptureSession(
        session_uuid=token,
        task_id=task.id,
        device_sn=sn,
        video_filename=video_name,
        trajectory_filename=traj_name,
        duration_seconds=round(duration, 3),
        frame_count=frames,
        is_reviewed=False,
    )
    task.completed_samples = (task.completed_samples or 0) + 1
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(session_dict(row), "会话已入库")


@router.post("/mock-sample")
async def create_mock_sample(request: Request, db: Session = Depends(get_db)):
    """Generate one sine-wave trajectory and a matched test video."""
    raw = await request.body()
    data = json.loads(raw) if raw else {}
    body = MockSampleIn(**data)
    task = None
    if body.task_id:
        task = db.query(Task).filter(Task.id == body.task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
    if task is None:
        task = db.query(Task).filter(Task.task_code == "TSK-2026-001").first() or db.query(Task).first()
    if task is None:
        task = Task(
            task_code="TSK-MOCK-001",
            title="模拟抓取样本",
            scene_category="机械臂抓取",
            priority="MEDIUM",
            status="ANNOTATING",
            assignee="林可",
            sample_target=50,
        )
        db.add(task)
        db.flush()

    device = None
    if body.device_sn:
        device = db.query(Device).filter(Device.device_sn == body.device_sn).first()
        if not device:
            raise HTTPException(status_code=400, detail="设备序列号未登记")
    if device is None:
        device = db.query(Device).filter(Device.device_type == "ROBOT_ARM", Device.status == "ONLINE").first()
    if device is None:
        device = db.query(Device).first()

    token = uuid.uuid4().hex[:12]
    traj_name = f"{token}.json"
    video_name = f"{token}.mp4"
    traj_path = RAW_DIR / traj_name
    video_path = RAW_DIR / video_name
    frames = generate_mock_trajectory(traj_path, duration_sec=body.duration_sec, hz=30)
    try:
        generate_mock_video(video_path, traj_path, fps=30)
    except Exception as exc:
        if traj_path.exists():
            traj_path.unlink()
        raise HTTPException(status_code=500, detail=f"测试视频生成失败: {exc}") from exc

    duration = round((frames - 1) / 30.0, 3) if frames else body.duration_sec
    row = CaptureSession(
        session_uuid=token,
        task_id=task.id,
        device_sn=device.device_sn if device else None,
        video_filename=video_name,
        trajectory_filename=traj_name,
        duration_seconds=duration,
        frame_count=frames,
        is_reviewed=False,
    )
    task.completed_samples = (task.completed_samples or 0) + 1
    if task.status in {"PENDING", "COLLECTING"}:
        task.status = "ANNOTATING"
    db.add(row)
    db.commit()
    db.refresh(row)
    data = session_dict(row)
    data["message"] = "已生成正弦轨迹与测试视频"
    return ok(data, "模拟样本已生成")
