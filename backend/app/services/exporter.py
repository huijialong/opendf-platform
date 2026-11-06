"""Pack a task's sessions into a LeRobot-style, HDF5-layout, or JSON zip."""

import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import AnnotationSegment, CaptureSession, Task


def _load_trajectory(raw_dir: Path, filename: str | None) -> list[dict]:
    if not filename:
        return []
    path = raw_dir / filename
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _episode_rows(records: list[dict], segments: list[AnnotationSegment]) -> list[dict]:
    labeled = []
    for rec in records:
        t = float(rec["timestamp"])
        label = ""
        for seg in segments:
            if seg.start_time <= t <= seg.end_time:
                label = seg.action_label or ""
                break
        pose = rec.get("ee_pose") or [0, 0, 0, 0, 0, 0]
        labeled.append(
            {
                "timestamp": t,
                "frame_idx": rec.get("frame_idx", 0),
                "ee_x": pose[0],
                "ee_y": pose[1],
                "ee_z": pose[2],
                "ee_rx": pose[3] if len(pose) > 3 else 0,
                "ee_ry": pose[4] if len(pose) > 4 else 0,
                "ee_rz": pose[5] if len(pose) > 5 else 0,
                "gripper_width": rec.get("gripper_width", 0),
                "velocity": rec.get("velocity", 0),
                "action_label": label,
            }
        )
    return labeled


def export_task(db: Session, task: Task, fmt: str, raw_dir: Path, export_dir: Path) -> dict:
    started = time.perf_counter()
    sessions = (
        db.query(CaptureSession)
        .filter(CaptureSession.task_id == task.id)
        .order_by(CaptureSession.id.asc())
        .all()
    )
    if not sessions:
        raise ValueError("该任务还没有采集会话，无法导出")

    fmt = fmt.lower().strip()
    if fmt not in {"lerobot", "hdf5", "json"}:
        raise ValueError("format 仅支持 lerobot / hdf5 / json")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename = f"task_{task.task_code}_{fmt}_{stamp}.zip"
    export_dir.mkdir(parents=True, exist_ok=True)
    zip_path = export_dir / filename

    episodes_meta = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for index, session in enumerate(sessions):
            records = _load_trajectory(raw_dir, session.trajectory_filename)
            segments = list(session.segments)
            rows = _episode_rows(records, segments)
            episodes_meta.append(
                {
                    "episode_index": index,
                    "session_uuid": session.session_uuid,
                    "length": len(rows),
                    "duration_seconds": session.duration_seconds,
                    "video": session.video_filename,
                    "tasks": [task.title],
                }
            )
            frame = pd.DataFrame(rows)
            csv_name = f"data/episode_{index:06d}.csv"
            bundle.writestr(csv_name, frame.to_csv(index=False))
            bundle.writestr(
                f"annotations/episode_{index:06d}.json",
                json.dumps(
                    [
                        {
                            "action_label": seg.action_label,
                            "start_time": seg.start_time,
                            "end_time": seg.end_time,
                            "quality_score": seg.quality_score,
                            "review_status": seg.review_status,
                            "notes": seg.notes,
                        }
                        for seg in segments
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            if session.trajectory_filename:
                src = raw_dir / session.trajectory_filename
                if src.exists():
                    bundle.write(src, arcname=f"origin/episode_{index:06d}.trajectory.json")
            if session.video_filename:
                src = raw_dir / session.video_filename
                if src.exists():
                    bundle.write(src, arcname=f"videos/episode_{index:06d}.mp4")

        if fmt == "lerobot":
            info = {
                "codebase_version": "v2.1",
                "robot_type": "opendf_arm",
                "total_episodes": len(sessions),
                "total_frames": sum(item["length"] for item in episodes_meta),
                "fps": 30,
                "features": {
                    "observation.state": {
                        "dtype": "float32",
                        "shape": [6],
                        "names": ["x", "y", "z", "rx", "ry", "rz"],
                    },
                    "action.gripper_width": {"dtype": "float32", "shape": [1]},
                    "observation.velocity": {"dtype": "float32", "shape": [1]},
                },
                "data_path": "data/episode_{episode_index:06d}.csv",
                "video_path": "videos/episode_{episode_index:06d}.mp4",
                "task_code": task.task_code,
                "task_title": task.title,
            }
            bundle.writestr("meta/info.json", json.dumps(info, ensure_ascii=False, indent=2))
            bundle.writestr(
                "meta/episodes.jsonl",
                "\n".join(json.dumps(item, ensure_ascii=False) for item in episodes_meta) + "\n",
            )
            bundle.writestr(
                "meta/tasks.jsonl",
                json.dumps(
                    {"task_index": 0, "task": task.title, "scene_category": task.scene_category},
                    ensure_ascii=False,
                )
                + "\n",
            )
        elif fmt == "hdf5":
            # Binary HDF5 needs h5py, which is intentionally outside the
            # zero-extra dependency set. The zip carries the same arrays under
            # the group paths a training loader expects.
            layout = {
                "format": "hdf5-layout",
                "note": "Arrays are stored as CSV columns and map onto these HDF5 groups.",
                "groups": {
                    "/observations/ee_pose": ["ee_x", "ee_y", "ee_z", "ee_rx", "ee_ry", "ee_rz"],
                    "/observations/gripper_width": ["gripper_width"],
                    "/observations/images": "videos/episode_*.mp4",
                    "/actions": ["gripper_width", "velocity"],
                    "/timestamps": ["timestamp"],
                },
                "episodes": episodes_meta,
                "task_code": task.task_code,
            }
            bundle.writestr("hdf5/layout.json", json.dumps(layout, ensure_ascii=False, indent=2))
        else:
            bundle.writestr(
                "dataset.json",
                json.dumps(
                    {
                        "task_code": task.task_code,
                        "title": task.title,
                        "scene_category": task.scene_category,
                        "episodes": episodes_meta,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )

        bundle.writestr(
            "README.txt",
            (
                f"OpenDF export\n"
                f"task: {task.task_code} {task.title}\n"
                f"format: {fmt}\n"
                f"episodes: {len(sessions)}\n"
                "origin/ holds the raw trajectory. data/ is the aligned std table.\n"
            ),
        )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "format": fmt,
        "filename": filename,
        "download_url": f"/storage/export/{filename}",
        "size_bytes": zip_path.stat().st_size,
        "episode_count": len(sessions),
        "elapsed_ms": elapsed_ms,
        "task_code": task.task_code,
    }
