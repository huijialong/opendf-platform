"""JSON shapes shared by the routers."""

from app.db.models import AnnotationSegment, CaptureSession, Device, Task


def iso(value) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def device_dict(row: Device) -> dict:
    return {
        "id": row.id,
        "device_sn": row.device_sn,
        "device_type": row.device_type,
        "name": row.name,
        "status": row.status,
        "meta_json": row.meta_json or {},
        "created_at": iso(row.created_at),
    }


def task_dict(row: Task) -> dict:
    target = row.sample_target or 0
    done = row.completed_samples or 0
    progress = round(min(100.0, (done / target) * 100), 1) if target else 0.0
    return {
        "id": row.id,
        "task_code": row.task_code,
        "title": row.title,
        "scene_category": row.scene_category,
        "priority": row.priority,
        "status": row.status,
        "assignee": row.assignee,
        "sample_target": target,
        "completed_samples": done,
        "progress": progress,
        "created_at": iso(row.created_at),
    }


def session_dict(row: CaptureSession) -> dict:
    task = row.task
    return {
        "id": row.id,
        "session_uuid": row.session_uuid,
        "task_id": row.task_id,
        "task_code": task.task_code if task else None,
        "task_title": task.title if task else None,
        "device_sn": row.device_sn,
        "video_filename": row.video_filename,
        "trajectory_filename": row.trajectory_filename,
        "video_url": f"/storage/raw/{row.video_filename}" if row.video_filename else None,
        "trajectory_url": f"/storage/raw/{row.trajectory_filename}" if row.trajectory_filename else None,
        "duration_seconds": row.duration_seconds,
        "frame_count": row.frame_count,
        "is_reviewed": row.is_reviewed,
        "segment_count": len(row.segments) if row.segments is not None else 0,
        "created_at": iso(row.created_at),
    }


def segment_dict(row: AnnotationSegment) -> dict:
    fps = 30
    return {
        "id": row.id,
        "session_id": row.session_id,
        "action_label": row.action_label,
        "start_time": row.start_time,
        "end_time": row.end_time,
        "start_frame": int(round((row.start_time or 0) * fps)),
        "end_frame": int(round((row.end_time or 0) * fps)),
        "quality_score": row.quality_score,
        "notes": row.notes,
        "review_status": row.review_status,
        "reject_reason": row.reject_reason,
        "created_at": iso(row.created_at),
    }


def ok(data, message: str = "ok") -> dict:
    return {"code": 200, "message": message, "data": data}
