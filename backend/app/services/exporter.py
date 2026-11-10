"""Pack a task's sessions into a LeRobot v2.1, HDF5-layout, or JSON zip."""

import csv
import io
import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from app.db.models import AnnotationSegment, CaptureSession, Task

CHUNK_SIZE = 1000
CAMERA_KEY = "observation.images.rgb"
PARQUET_COLUMNS = [
    "observation.state",
    "observation.velocity",
    "action",
    "action_label",
    "timestamp",
    "frame_index",
    "episode_index",
    "index",
    "task_index",
]
CSV_FALLBACK_WARNING = (
    "pandas 或 pyarrow 当前不可用，LeRobot 回合表已回退为 CSV"
    "（data/chunk-XXX/episode_XXXXXX.csv），不是 v2.1 parquet。"
    "请安装 pandas 与 pyarrow 后重新导出。"
)


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


def _pose(record: dict) -> list[float]:
    raw = list(record.get("ee_pose") or [])
    pose = [float(value) for value in raw[:6]]
    while len(pose) < 6:
        pose.append(0.0)
    return pose


def _label_at(timestamp: float, segments: list[AnnotationSegment]) -> str:
    for seg in segments:
        if seg.start_time <= timestamp <= seg.end_time:
            return seg.action_label or ""
    return ""


def _build_lerobot_rows(
    records: list[dict],
    segments: list[AnnotationSegment],
    episode_index: int,
    task_index: int,
    global_index: int,
) -> tuple[list[dict], int]:
    rows = []
    for offset, record in enumerate(records):
        timestamp = float(record.get("timestamp", 0.0))
        frame_index = int(record.get("frame_idx", offset))
        rows.append(
            {
                "observation.state": _pose(record),
                "observation.velocity": [float(record.get("velocity", 0.0))],
                "action": [float(record.get("gripper_width", 0.0))],
                "action_label": _label_at(timestamp, segments),
                "timestamp": timestamp,
                "frame_index": frame_index,
                "episode_index": episode_index,
                "index": global_index,
                "task_index": task_index,
            }
        )
        global_index += 1
    return rows, global_index


def _infer_fps(rows: list[dict]) -> int:
    if len(rows) >= 2:
        delta = float(rows[1]["timestamp"]) - float(rows[0]["timestamp"])
        if delta > 0:
            return max(1, int(round(1.0 / delta)))
    return 30


def _data_arc(episode_index: int, suffix: str) -> str:
    chunk = episode_index // CHUNK_SIZE
    return f"data/chunk-{chunk:03d}/episode_{episode_index:06d}.{suffix}"


def _video_arc(episode_index: int, camera_key: str = CAMERA_KEY) -> str:
    chunk = episode_index // CHUNK_SIZE
    return f"videos/chunk-{chunk:03d}/{camera_key}/episode_{episode_index:06d}.mp4"


def _data_template(suffix: str) -> str:
    return f"data/chunk-{{episode_chunk:03d}}/episode_{{episode_index:06d}}.{suffix}"


def _parquet_supported() -> bool:
    try:
        import pandas  # noqa: F401
        import pyarrow  # noqa: F401
        import pyarrow.parquet  # noqa: F401
    except ImportError:
        return False
    return True


def _parquet_bytes(rows: list[dict]) -> bytes:
    import pandas as pd

    frame = pd.DataFrame(rows, columns=PARQUET_COLUMNS)
    if not frame.empty:
        frame["timestamp"] = frame["timestamp"].astype("float32")
        for column in ("frame_index", "episode_index", "index", "task_index"):
            frame[column] = frame[column].astype("int64")
    buffer = io.BytesIO()
    frame.to_parquet(buffer, engine="pyarrow", index=False)
    return buffer.getvalue()


def _csv_bytes(rows: list[dict]) -> bytes:
    fieldnames = [
        "timestamp",
        "frame_index",
        "episode_index",
        "index",
        "task_index",
        "ee_x",
        "ee_y",
        "ee_z",
        "ee_rx",
        "ee_ry",
        "ee_rz",
        "gripper_width",
        "velocity",
        "action_label",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        state = row["observation.state"]
        writer.writerow(
            {
                "timestamp": row["timestamp"],
                "frame_index": row["frame_index"],
                "episode_index": row["episode_index"],
                "index": row["index"],
                "task_index": row["task_index"],
                "ee_x": state[0],
                "ee_y": state[1],
                "ee_z": state[2],
                "ee_rx": state[3],
                "ee_ry": state[4],
                "ee_rz": state[5],
                "gripper_width": row["action"][0],
                "velocity": row["observation.velocity"][0],
                "action_label": row["action_label"],
            }
        )
    return buffer.getvalue().encode("utf-8")


def _numeric_blocks(rows: list[dict]) -> dict[str, np.ndarray]:
    if not rows:
        return {}

    def column(name: str) -> np.ndarray:
        return np.asarray([row[name] for row in rows], dtype=np.float64).reshape(-1, 1)

    return {
        "observation.state": np.asarray([row["observation.state"] for row in rows], dtype=np.float64),
        "observation.velocity": np.asarray([row["observation.velocity"] for row in rows], dtype=np.float64),
        "action": np.asarray([row["action"] for row in rows], dtype=np.float64),
        "timestamp": column("timestamp"),
        "frame_index": column("frame_index"),
        "episode_index": column("episode_index"),
        "index": column("index"),
        "task_index": column("task_index"),
    }


def _stats(block: dict[str, np.ndarray]) -> dict:
    stats = {}
    for name, values in block.items():
        if values.size == 0:
            continue
        matrix = values.reshape(-1, 1) if values.ndim == 1 else values
        stats[name] = {
            "min": matrix.min(axis=0).astype(float).tolist(),
            "max": matrix.max(axis=0).astype(float).tolist(),
            "mean": matrix.mean(axis=0).astype(float).tolist(),
            "std": matrix.std(axis=0).astype(float).tolist(),
            "count": [int(matrix.shape[0])],
            "q01": np.quantile(matrix, 0.01, axis=0).astype(float).tolist(),
            "q99": np.quantile(matrix, 0.99, axis=0).astype(float).tolist(),
        }
    return stats


def _concat_blocks(blocks: list[dict[str, np.ndarray]]) -> dict[str, np.ndarray]:
    names: list[str] = []
    for block in blocks:
        for name in block:
            if name not in names:
                names.append(name)
    merged = {}
    for name in names:
        parts = [block[name] for block in blocks if name in block and block[name].size]
        if parts:
            merged[name] = np.concatenate(parts, axis=0)
    return merged


def _mp4_dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        data = path.read_bytes()
    except OSError:
        return None, None
    start = 0
    while start < len(data):
        idx = data.find(b"tkhd", start)
        if idx < 4:
            return None, None
        size = int.from_bytes(data[idx - 4 : idx], "big")
        if size < 32 or idx - 4 + size > len(data):
            start = idx + 4
            continue
        end = idx - 4 + size
        width = int.from_bytes(data[end - 8 : end - 4], "big") / 65536.0
        height = int.from_bytes(data[end - 4 : end], "big") / 65536.0
        if width >= 2 and height >= 2:
            return int(round(width)), int(round(height))
        start = idx + 4
    return None, None


def _annotation_payload(segments: list[AnnotationSegment]) -> str:
    return json.dumps(
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
    )


def _write_lerobot(bundle: zipfile.ZipFile, task: Task, sessions: list[CaptureSession], raw_dir: Path) -> str | None:
    use_parquet = _parquet_supported()
    warning = None if use_parquet else CSV_FALLBACK_WARNING
    task_name = task.title or task.task_code
    episodes_meta = []
    episode_stat_lines = []
    matrices = []
    pending: list[tuple[int, list[dict]]] = []
    global_index = 0
    fps = 30
    fps_ready = False
    videos_copied = 0
    video_width = None
    video_height = None

    for index, session in enumerate(sessions):
        records = _load_trajectory(raw_dir, session.trajectory_filename)
        segments = list(session.segments)
        rows, global_index = _build_lerobot_rows(records, segments, index, 0, global_index)
        if rows and not fps_ready:
            fps = _infer_fps(rows)
            fps_ready = True
        pending.append((index, rows))
        block = _numeric_blocks(rows)
        matrices.append(block)
        episode_stat_lines.append(
            json.dumps({"episode_index": index, "stats": _stats(block)}, ensure_ascii=False)
        )
        episodes_meta.append(
            {
                "episode_index": index,
                "tasks": [task_name],
                "length": len(rows),
                "session_uuid": session.session_uuid,
            }
        )
        bundle.writestr(f"annotations/episode_{index:06d}.json", _annotation_payload(segments))
        if session.trajectory_filename:
            src = raw_dir / session.trajectory_filename
            if src.exists():
                bundle.write(src, arcname=f"origin/episode_{index:06d}.trajectory.json")
        if session.video_filename:
            src = raw_dir / session.video_filename
            if src.is_file():
                if video_width is None:
                    video_width, video_height = _mp4_dimensions(src)
                bundle.write(src, arcname=_video_arc(index))
                videos_copied += 1

    written_suffixes = []
    for index, rows in pending:
        suffix = "parquet" if use_parquet else "csv"
        try:
            payload = _parquet_bytes(rows) if suffix == "parquet" else _csv_bytes(rows)
        except Exception as exc:
            payload = _csv_bytes(rows)
            suffix = "csv"
            detail = f"{exc.__class__.__name__}: {exc}"
            warning = f"{warning or CSV_FALLBACK_WARNING} 写出 parquet 失败，已改写 CSV（{detail}）。"
        written_suffixes.append(suffix)
        bundle.writestr(_data_arc(index, suffix), payload)

    if written_suffixes and all(item == "csv" for item in written_suffixes):
        data_suffix = "csv"
    else:
        data_suffix = "parquet"
    if written_suffixes and len(set(written_suffixes)) > 1 and warning is None:
        warning = "部分回合写成了 CSV，因为对应的 parquet 写出失败。"

    features = {
        "observation.state": {
            "dtype": "float32",
            "shape": [6],
            "names": ["x", "y", "z", "rx", "ry", "rz"],
        },
        "observation.velocity": {"dtype": "float32", "shape": [1], "names": ["velocity"]},
        "action": {"dtype": "float32", "shape": [1], "names": ["gripper_width"]},
        "action_label": {"dtype": "string", "shape": [1], "names": None},
        "timestamp": {"dtype": "float32", "shape": [1], "names": None},
        "frame_index": {"dtype": "int64", "shape": [1], "names": None},
        "episode_index": {"dtype": "int64", "shape": [1], "names": None},
        "index": {"dtype": "int64", "shape": [1], "names": None},
        "task_index": {"dtype": "int64", "shape": [1], "names": None},
    }
    video_path = None
    if videos_copied:
        video_path = "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4"
        video_feature = {
            "dtype": "video",
            "shape": [video_height or 0, video_width or 0, 3],
            "names": ["height", "width", "channels"],
            "info": {
                "video.fps": fps,
                "video.channels": 3,
                "video.codec": "h264",
                "video.pix_fmt": "yuv420p",
                "video.is_depth_map": False,
                "has_audio": False,
            },
        }
        if video_height and video_width:
            video_feature["info"]["video.height"] = video_height
            video_feature["info"]["video.width"] = video_width
        features[CAMERA_KEY] = video_feature

    total_episodes = len(sessions)
    info = {
        "codebase_version": "v2.1",
        "robot_type": "opendf_arm",
        "total_episodes": total_episodes,
        "total_frames": sum(item["length"] for item in episodes_meta),
        "total_tasks": 1,
        "total_videos": videos_copied,
        "total_chunks": max(1, (total_episodes + CHUNK_SIZE - 1) // CHUNK_SIZE),
        "chunks_size": CHUNK_SIZE,
        "fps": fps,
        "splits": {"train": f"0:{total_episodes}"},
        "data_path": _data_template(data_suffix),
        "video_path": video_path,
        "features": features,
        "task_code": task.task_code,
        "task_title": task.title,
    }
    if warning:
        info["warning"] = warning

    bundle.writestr("meta/info.json", json.dumps(info, ensure_ascii=False, indent=2))
    bundle.writestr(
        "meta/episodes.jsonl",
        "\n".join(json.dumps(item, ensure_ascii=False) for item in episodes_meta) + "\n",
    )
    bundle.writestr(
        "meta/tasks.jsonl",
        json.dumps({"task_index": 0, "task": task_name}, ensure_ascii=False) + "\n",
    )
    bundle.writestr("meta/stats.json", json.dumps(_stats(_concat_blocks(matrices)), ensure_ascii=False, indent=2))
    bundle.writestr("meta/episodes_stats.jsonl", "\n".join(episode_stat_lines) + ("\n" if episode_stat_lines else ""))

    readme = [
        "OpenDF export",
        f"task: {task.task_code} {task.title}",
        "format: lerobot",
        "codebase_version: v2.1",
        f"episodes: {total_episodes}",
        f"tables: {_data_template(data_suffix)}",
        "meta: info.json, episodes.jsonl, tasks.jsonl, stats.json, episodes_stats.jsonl",
        f"videos: videos/chunk-{{episode_chunk:03d}}/{CAMERA_KEY}/episode_{{episode_index:06d}}.mp4",
        "origin/ holds the raw trajectory. annotations/ holds review slices.",
    ]
    if warning:
        readme.append(f"warning: {warning}")
    bundle.writestr("README.txt", "\n".join(readme) + "\n")
    return warning


def _write_legacy(
    bundle: zipfile.ZipFile,
    task: Task,
    sessions: list[CaptureSession],
    raw_dir: Path,
    fmt: str,
) -> None:
    episodes_meta = []
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
        buffer = io.StringIO()
        fieldnames = [
            "timestamp",
            "frame_idx",
            "ee_x",
            "ee_y",
            "ee_z",
            "ee_rx",
            "ee_ry",
            "ee_rz",
            "gripper_width",
            "velocity",
            "action_label",
        ]
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})
        bundle.writestr(f"data/episode_{index:06d}.csv", buffer.getvalue())
        bundle.writestr(f"annotations/episode_{index:06d}.json", _annotation_payload(segments))
        if session.trajectory_filename:
            src = raw_dir / session.trajectory_filename
            if src.exists():
                bundle.write(src, arcname=f"origin/episode_{index:06d}.trajectory.json")
        if session.video_filename:
            src = raw_dir / session.video_filename
            if src.exists():
                bundle.write(src, arcname=f"videos/episode_{index:06d}.mp4")

    if fmt == "hdf5":
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

    warning = None
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        if fmt == "lerobot":
            warning = _write_lerobot(bundle, task, sessions, raw_dir)
        else:
            _write_legacy(bundle, task, sessions, raw_dir, fmt)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    result = {
        "format": fmt,
        "filename": filename,
        "download_url": f"/storage/export/{filename}",
        "size_bytes": zip_path.stat().st_size,
        "episode_count": len(sessions),
        "elapsed_ms": elapsed_ms,
        "task_code": task.task_code,
    }
    if warning:
        result["warning"] = warning
    return result
