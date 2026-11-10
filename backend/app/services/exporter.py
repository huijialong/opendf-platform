"""Pack a task's sessions into a LeRobot v2.1, HDF5-layout, or JSON zip."""

import csv
import io
import json
import shutil
import subprocess
import tempfile
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
    """Write episode columns with the dtypes declared in meta/info.json.

    List features such as observation.state are float32, not the float64 pyarrow
    infers from Python floats. Index columns stay int64.
    """
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq

    frame = pd.DataFrame(rows, columns=PARQUET_COLUMNS)

    def matrix(column: str, width: int) -> np.ndarray:
        if frame.empty:
            return np.zeros((0, width), dtype=np.float32)
        return np.asarray(frame[column].tolist(), dtype=np.float32)

    def fixed_list(column: str, width: int) -> pa.Array:
        values = np.ascontiguousarray(matrix(column, width))
        flat = pa.array(values.reshape(-1), type=pa.float32())
        return pa.FixedSizeListArray.from_arrays(flat, width)

    def numbers(column: str, dtype: str, arrow_type: pa.DataType) -> pa.Array:
        if frame.empty:
            return pa.array([], type=arrow_type)
        return pa.array(frame[column].to_numpy(dtype=dtype), type=arrow_type)

    labels = [] if frame.empty else frame["action_label"].astype("string").tolist()
    table = pa.table(
        {
            "observation.state": fixed_list("observation.state", 6),
            "observation.velocity": fixed_list("observation.velocity", 1),
            "action": fixed_list("action", 1),
            "action_label": pa.array(labels, type=pa.string()),
            "timestamp": numbers("timestamp", "float32", pa.float32()),
            "frame_index": numbers("frame_index", "int64", pa.int64()),
            "episode_index": numbers("episode_index", "int64", pa.int64()),
            "index": numbers("index", "int64", pa.int64()),
            "task_index": numbers("task_index", "int64", pa.int64()),
        }
    )
    buffer = io.BytesIO()
    pq.write_table(table, buffer)
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


def _dimensions_from_bytes(data: bytes) -> tuple[int | None, int | None]:
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


def _even(value: int) -> int:
    value = max(2, int(value))
    return value if value % 2 == 0 else value - 1


def _parse_rate(text: str | None) -> float | None:
    if not text or text in {"0/0", "N/A"}:
        return None
    if "/" in text:
        num, den = text.split("/", 1)
        try:
            den_f = float(den)
        except ValueError:
            return None
        if den_f == 0:
            return None
        try:
            return float(num) / den_f
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def _shared(values: list) -> object | None:
    seen = []
    for value in values:
        if value is None:
            return None
        if value not in seen:
            seen.append(value)
    if len(seen) == 1:
        return seen[0]
    return None


def _read_probe_bytes(path: Path) -> bytes:
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size <= 32 * 1024 * 1024:
            return handle.read()
        head = handle.read(8 * 1024 * 1024)
        handle.seek(max(0, size - 2 * 1024 * 1024))
        return head + handle.read()


def _sniff_video(path: Path) -> dict | None:
    """Best-effort codec and size when ffprobe is not installed."""
    try:
        data = _read_probe_bytes(path)
    except OSError:
        return None
    if not data:
        return None
    suffix = path.suffix.lower()
    if suffix == ".webm" or data.startswith(b"\x1a\x45\xdf\xa3"):
        codec = None
        for token, name in ((b"V_VP9", "vp9"), (b"V_VP8", "vp8"), (b"V_AV1", "av1"), (b"V_MPEG4/ISO/AVC", "h264")):
            if token in data:
                codec = name
                break
        return {
            "codec": codec,
            "pix_fmt": None,
            "width": None,
            "height": None,
            "fps": None,
            "nb_frames": None,
            "has_audio": False,
        }
    codec = None
    for token, name in (
        (b"avc1", "h264"),
        (b"avc3", "h264"),
        (b"hvc1", "hevc"),
        (b"hev1", "hevc"),
        (b"vp09", "vp9"),
        (b"av01", "av1"),
        (b"mp4v", "mpeg4"),
    ):
        if token in data:
            codec = name
            break
    width, height = _dimensions_from_bytes(data)
    if codec is None and width is None:
        return None
    return {
        "codec": codec,
        "pix_fmt": None,
        "width": width,
        "height": height,
        "fps": None,
        "nb_frames": None,
        "has_audio": False,
    }


def _probe_with_ffprobe(path: Path) -> dict | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "stream=codec_type,codec_name,width,height,pix_fmt,avg_frame_rate,nb_frames",
        "-of",
        "json",
        str(path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        payload = json.loads(proc.stdout.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return None
    streams = payload.get("streams") or []
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    if video is None and streams:
        video = streams[0]
    if not video:
        return None
    raw_frames = video.get("nb_frames")
    nb_frames = int(raw_frames) if isinstance(raw_frames, str) and raw_frames.isdigit() else None
    width = video.get("width")
    height = video.get("height")
    return {
        "codec": video.get("codec_name") or None,
        "pix_fmt": video.get("pix_fmt") or None,
        "width": int(width) if width else None,
        "height": int(height) if height else None,
        "fps": _parse_rate(video.get("avg_frame_rate")),
        "nb_frames": nb_frames,
        "has_audio": any(item.get("codec_type") == "audio" for item in streams),
    }


def _probe_video(path: Path) -> dict | None:
    probed = _probe_with_ffprobe(path)
    if probed and probed.get("codec") and probed.get("width") and probed.get("height"):
        return probed
    sniffed = _sniff_video(path)
    if probed and sniffed:
        for key, value in sniffed.items():
            if not probed.get(key) and value:
                probed[key] = value
        return probed
    return probed or sniffed


def _run_ffmpeg(cmd: list[str], timeout: int = 180) -> bool:
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def _transcode_h264(src: Path, dest: Path, target_wh: tuple[int, int] | None) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    filters = ["format=yuv420p"]
    if target_wh and target_wh[0] and target_wh[1]:
        filters.insert(0, f"scale={_even(target_wh[0])}:{_even(target_wh[1])}:flags=bilinear")
    cmd = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-an",
        "-vf",
        ",".join(filters),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "ultrafast",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    return _run_ffmpeg(cmd) and dest.is_file() and dest.stat().st_size > 0


def _normalize_to_mp4(src: Path, dest: Path, target_wh: tuple[int, int] | None) -> dict | None:
    """Copy an H.264 MP4 through, or transcode to one. Never relabel a foreign container."""
    probe = _probe_video(src)
    width = (probe or {}).get("width")
    height = (probe or {}).get("height")
    same_size = target_wh is None or (width == target_wh[0] and height == target_wh[1])
    already_h264 = (
        probe
        and probe.get("codec") == "h264"
        and probe.get("pix_fmt") == "yuv420p"
        and src.suffix.lower() == ".mp4"
        and same_size
        and width
        and height
    )
    if already_h264:
        shutil.copyfile(src, dest)
        return _probe_video(dest) or probe
    if shutil.which("ffmpeg"):
        size = target_wh
        if size is None and width and height:
            size = (_even(int(width)), _even(int(height)))
        if not _transcode_h264(src, dest, size):
            return None
        probed = _probe_video(dest)
        if probed and probed.get("codec"):
            return probed
        out_w = size[0] if size else width
        out_h = size[1] if size else height
        return {
            "codec": "h264",
            "pix_fmt": "yuv420p",
            "width": out_w,
            "height": out_h,
            "fps": (probe or {}).get("fps"),
            "nb_frames": (probe or {}).get("nb_frames"),
            "has_audio": False,
        }
    if src.suffix.lower() == ".mp4":
        shutil.copyfile(src, dest)
        return _probe_video(dest) or probe
    return None


def _write_placeholder(dest: Path, target_wh: tuple[int, int], fps: float, frames: int) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    width, height = _even(target_wh[0]), _even(target_wh[1])
    rate = max(1, int(round(fps or 30)))
    cmd = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s={width}x{height}:r={rate}",
        "-frames:v",
        str(max(1, frames)),
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "ultrafast",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    return _run_ffmpeg(cmd) and dest.is_file() and dest.stat().st_size > 0


def _sample_indices(total: int) -> list[int]:
    if total <= 1:
        return [0]
    count = total if total < 100 else max(100, min(int(total**0.75), 10_000))
    return np.round(np.linspace(0, total - 1, count)).astype(int).tolist()


def _stat_size(width: int, height: int) -> tuple[int, int]:
    if max(width, height) < 300:
        return width, height
    factor = int(max(width, height) / 150) or 1
    return max(1, width // factor), max(1, height // factor)


def _sample_rgb_frames(path: Path, probe: dict, frame_hint: int) -> tuple[np.ndarray, int] | None:
    ffmpeg = shutil.which("ffmpeg")
    width = probe.get("width")
    height = probe.get("height")
    if not ffmpeg or not width or not height:
        return None
    total = int(probe.get("nb_frames") or frame_hint or 0)
    out_w, out_h = _stat_size(int(width), int(height))
    if total > 0:
        select = "+".join(f"eq(n,{index})" for index in _sample_indices(total))
        vf = f"select='{select}',scale={out_w}:{out_h}"
        commands = [
            [ffmpeg, "-v", "error", "-i", str(path), "-vf", vf, "-fps_mode", "vfr", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            [ffmpeg, "-v", "error", "-i", str(path), "-vf", f"scale={out_w}:{out_h}", "-frames:v", "60", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        ]
    else:
        commands = [
            [ffmpeg, "-v", "error", "-i", str(path), "-vf", f"fps=2,scale={out_w}:{out_h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        ]
    payload = b""
    for cmd in commands:
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=180, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode == 0 and proc.stdout:
            payload = proc.stdout
            break
    frame_bytes = out_w * out_h * 3
    decoded = len(payload) // frame_bytes
    if decoded <= 0:
        return None
    raw = np.frombuffer(payload[: decoded * frame_bytes], dtype=np.uint8)
    frames = raw.reshape(decoded, out_h, out_w, 3).transpose(0, 3, 1, 2)
    return frames, total or decoded


def _image_stats_np(frames: np.ndarray, count: int) -> dict[str, np.ndarray]:
    """Per-channel RGB stats in [0, 1], shaped (C, 1, 1), matching LeRobot v2.1."""
    axes = (0, 2, 3)

    def pack(values: np.ndarray) -> np.ndarray:
        scaled = np.asarray(values, dtype=np.float64).reshape(-1) / 255.0
        return scaled.reshape(-1, 1, 1)

    return {
        "min": pack(np.min(frames, axis=axes)),
        "max": pack(np.max(frames, axis=axes)),
        "mean": pack(np.mean(frames, axis=axes)),
        "std": pack(np.std(frames, axis=axes)),
        "count": np.array([int(count)], dtype=np.int64),
        "q01": pack(np.quantile(frames.astype(np.float64), 0.01, axis=axes)),
        "q99": pack(np.quantile(frames.astype(np.float64), 0.99, axis=axes)),
    }


def _aggregate_image_stats(parts: list[dict[str, np.ndarray]]) -> dict[str, np.ndarray]:
    if len(parts) == 1:
        return parts[0]
    means = np.stack([part["mean"] for part in parts])
    variances = np.stack([part["std"] for part in parts]) ** 2
    counts = np.stack([part["count"] for part in parts]).astype(np.float64)
    total_count = counts.sum(axis=0)
    weight = counts
    total = total_count
    while weight.ndim < means.ndim:
        weight = np.expand_dims(weight, axis=-1)
        total = np.expand_dims(total, axis=-1)
    total_mean = (means * weight).sum(axis=0) / total
    total_var = ((variances + (means - total_mean) ** 2) * weight).sum(axis=0) / total
    aggregated = {
        "min": np.min(np.stack([part["min"] for part in parts]), axis=0),
        "max": np.max(np.stack([part["max"] for part in parts]), axis=0),
        "mean": total_mean,
        "std": np.sqrt(np.maximum(total_var, 0)),
        "count": total_count.reshape(-1)[:1].astype(np.int64),
    }
    for key in ("q01", "q99"):
        if all(key in part for part in parts):
            stacked = np.stack([part[key] for part in parts])
            aggregated[key] = np.min(stacked, axis=0) if key == "q01" else np.max(stacked, axis=0)
    return aggregated


def _json_image_stats(stats: dict[str, np.ndarray]) -> dict:
    payload = {}
    for key, value in stats.items():
        array = np.asarray(value)
        if key == "count":
            payload[key] = [int(array.reshape(-1)[0])]
        else:
            payload[key] = np.asarray(array, dtype=np.float64).tolist()
    return payload


def _video_feature(produced: list[dict], fallback_fps: float) -> dict | None:
    probes = [item["probe"] for item in produced]
    codec = _shared([probe.get("codec") for probe in probes])
    width = _shared([probe.get("width") for probe in probes])
    height = _shared([probe.get("height") for probe in probes])
    if not codec or not width or not height:
        return None
    pix_fmt = _shared([probe.get("pix_fmt") for probe in probes])
    rates = [probe.get("fps") for probe in probes]
    rate = _shared(rates) or fallback_fps
    if isinstance(rate, float) and rate.is_integer():
        rate = int(rate)
    info = {
        "video.fps": rate,
        "video.height": int(height),
        "video.width": int(width),
        "video.channels": 3,
        "video.codec": codec,
        "video.is_depth_map": False,
        "has_audio": any(bool(probe.get("has_audio")) for probe in probes),
    }
    if pix_fmt:
        info["video.pix_fmt"] = pix_fmt
    return {
        "dtype": "video",
        "shape": [int(height), int(width), 3],
        "names": ["height", "width", "channels"],
        "info": info,
    }


def _prepare_videos(episodes: list[dict], fps: float, tmp: Path) -> tuple[list[dict | None], dict | None, str | None]:
    sources: list[Path | None] = []
    for episode in episodes:
        filename = episode["session"].video_filename
        src = episode["raw_dir"] / filename if filename else None
        sources.append(src if src is not None and src.is_file() else None)
    if not any(sources):
        return [None] * len(episodes), None, None

    produced: list[dict | None] = [None] * len(episodes)
    target_wh = None
    for index, src in enumerate(sources):
        if src is None:
            continue
        dest = tmp / f"episode_{index:06d}.mp4"
        probe = _normalize_to_mp4(src, dest, target_wh)
        if probe is None or not dest.is_file() or not probe.get("width") or not probe.get("height"):
            continue
        if target_wh is None:
            target_wh = (int(probe["width"]), int(probe["height"]))
        produced[index] = {"path": dest, "probe": probe, "stats": None}

    notes: list[str] = []
    missing = [index for index, item in enumerate(produced) if item is None]
    if missing and target_wh and shutil.which("ffmpeg"):
        for index in missing:
            dest = tmp / f"episode_{index:06d}.mp4"
            frames = max(len(episodes[index]["rows"]), 1)
            if not _write_placeholder(dest, target_wh, fps, frames):
                continue
            probe = _probe_video(dest) or {
                "codec": "h264",
                "pix_fmt": "yuv420p",
                "width": _even(target_wh[0]),
                "height": _even(target_wh[1]),
                "fps": float(fps),
                "nb_frames": frames,
                "has_audio": False,
            }
            produced[index] = {"path": dest, "probe": probe, "stats": None}
        if any(produced[index] is not None for index in missing):
            notes.append("部分会话没有视频，已用 ffmpeg 生成黑色 H.264 占位片段。")
    elif missing and any(sources):
        notes.append("部分会话没有可写入的 MP4，且没有 ffmpeg 可以生成占位视频。")

    filled = [item for item in produced if item is not None]
    if not filled:
        notes.append("没有可导出的视频，info.json 不声明相机特征。")
        return produced, None, " ".join(notes)
    if any(item is None for item in produced):
        notes.append("未能为每个回合提供视频，因此 info.json 不声明相机特征。")
        return produced, None, " ".join(notes)

    for index, item in enumerate(produced):
        assert item is not None
        sampled = _sample_rgb_frames(item["path"], item["probe"], len(episodes[index]["rows"]))
        if sampled is None:
            continue
        frames, full_count = sampled
        item["stats"] = _image_stats_np(frames, full_count)

    feature = _video_feature(produced, fps)
    if feature is None:
        notes.append("视频编码或分辨率不一致，info.json 不声明单一相机特征。")
    elif any(item is None or item.get("stats") is None for item in produced):
        notes.append("有视频未能采样出画面统计。")
    return produced, feature, " ".join(notes) or None


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


def _join_notes(*notes: str | None) -> str | None:
    parts = [note for note in notes if note]
    return " ".join(parts) if parts else None


def _write_lerobot(bundle: zipfile.ZipFile, task: Task, sessions: list[CaptureSession], raw_dir: Path) -> str | None:
    use_parquet = _parquet_supported()
    notes = [] if use_parquet else [CSV_FALLBACK_WARNING]
    task_name = task.title or task.task_code
    episodes_meta = []
    matrices = []
    episodes = []
    global_index = 0
    fps = 30
    fps_ready = False

    for index, session in enumerate(sessions):
        records = _load_trajectory(raw_dir, session.trajectory_filename)
        segments = list(session.segments)
        rows, global_index = _build_lerobot_rows(records, segments, index, 0, global_index)
        if rows and not fps_ready:
            fps = _infer_fps(rows)
            fps_ready = True
        episodes.append(
            {
                "index": index,
                "session": session,
                "segments": segments,
                "rows": rows,
                "raw_dir": raw_dir,
            }
        )
        matrices.append(_numeric_blocks(rows))
        episodes_meta.append(
            {
                "episode_index": index,
                "tasks": [task_name],
                "length": len(rows),
                "session_uuid": session.session_uuid,
            }
        )

    with tempfile.TemporaryDirectory(prefix="opendf-lerobot-") as tmp:
        produced, video_feature, video_note = _prepare_videos(episodes, fps, Path(tmp))
        if video_note:
            notes.append(video_note)
        videos_written = 0
        for episode, item in zip(episodes, produced):
            index = episode["index"]
            bundle.writestr(f"annotations/episode_{index:06d}.json", _annotation_payload(episode["segments"]))
            filename = episode["session"].trajectory_filename
            if filename:
                src = raw_dir / filename
                if src.exists():
                    bundle.write(src, arcname=f"origin/episode_{index:06d}.trajectory.json")
            if item is not None:
                bundle.write(item["path"], arcname=_video_arc(index))
                videos_written += 1

        written_suffixes = []
        for episode in episodes:
            suffix = "parquet" if use_parquet else "csv"
            try:
                payload = _parquet_bytes(episode["rows"]) if suffix == "parquet" else _csv_bytes(episode["rows"])
            except Exception as exc:
                payload = _csv_bytes(episode["rows"])
                suffix = "csv"
                notes.append(f"写出 parquet 失败，已改写 CSV（{exc.__class__.__name__}: {exc}）。")
            written_suffixes.append(suffix)
            bundle.writestr(_data_arc(episode["index"], suffix), payload)

    if written_suffixes and all(item == "csv" for item in written_suffixes):
        data_suffix = "csv"
    else:
        data_suffix = "parquet"
    if written_suffixes and len(set(written_suffixes)) > 1:
        notes.append("部分回合写成了 CSV，因为对应的 parquet 写出失败。")

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
    if video_feature is not None:
        features[CAMERA_KEY] = video_feature
        video_path = "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4"

    dataset_stats = _stats(_concat_blocks(matrices))
    image_parts = [item["stats"] for item in produced if item is not None and item.get("stats") is not None]
    if video_feature is not None and image_parts:
        dataset_stats[CAMERA_KEY] = _json_image_stats(_aggregate_image_stats(image_parts))
    episode_stat_lines = []
    for episode, block, item in zip(episodes, matrices, produced):
        stats = _stats(block)
        if video_feature is not None and item is not None and item.get("stats") is not None:
            stats[CAMERA_KEY] = _json_image_stats(item["stats"])
        episode_stat_lines.append(json.dumps({"episode_index": episode["index"], "stats": stats}, ensure_ascii=False))

    total_episodes = len(sessions)
    warning = _join_notes(*notes)
    info = {
        "codebase_version": "v2.1",
        "robot_type": "opendf_arm",
        "total_episodes": total_episodes,
        "total_frames": sum(item["length"] for item in episodes_meta),
        "total_tasks": 1,
        "total_videos": videos_written,
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
    bundle.writestr("meta/stats.json", json.dumps(dataset_stats, ensure_ascii=False, indent=2))
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
    if video_feature is not None:
        readme.append(f"video.codec: {video_feature['info'].get('video.codec')}")
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
