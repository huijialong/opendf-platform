"""Sinusoidal arm trajectory and a matching test video for hardware-free demos."""

import json
import math
import subprocess
from pathlib import Path

import numpy as np

# 5x7 glyphs. Each row is 5 bits, MSB on the left.
_GLYPHS = {
    " ": [0, 0, 0, 0, 0, 0, 0],
    "-": [0, 0, 0, 31, 0, 0, 0],
    ":": [0, 4, 4, 0, 4, 4, 0],
    ".": [0, 0, 0, 0, 0, 12, 12],
    "+": [0, 4, 4, 14, 4, 4, 0],
    "/": [1, 2, 4, 8, 16, 0, 0],
    "0": [14, 17, 19, 21, 25, 17, 14],
    "1": [4, 12, 4, 4, 4, 4, 14],
    "2": [14, 17, 1, 6, 8, 16, 31],
    "3": [14, 17, 1, 6, 1, 17, 14],
    "4": [2, 6, 10, 18, 31, 2, 2],
    "5": [31, 16, 30, 1, 1, 17, 14],
    "6": [6, 8, 16, 30, 17, 17, 14],
    "7": [31, 1, 2, 4, 8, 8, 8],
    "8": [14, 17, 17, 14, 17, 17, 14],
    "9": [14, 17, 17, 15, 1, 2, 12],
    "A": [14, 17, 17, 31, 17, 17, 17],
    "B": [30, 17, 17, 30, 17, 17, 30],
    "C": [14, 17, 16, 16, 16, 17, 14],
    "D": [30, 17, 17, 17, 17, 17, 30],
    "E": [31, 16, 16, 30, 16, 16, 31],
    "F": [31, 16, 16, 30, 16, 16, 16],
    "G": [14, 17, 16, 23, 17, 17, 14],
    "H": [17, 17, 17, 31, 17, 17, 17],
    "I": [14, 4, 4, 4, 4, 4, 14],
    "J": [7, 2, 2, 2, 2, 18, 12],
    "K": [17, 18, 20, 24, 20, 18, 17],
    "L": [16, 16, 16, 16, 16, 16, 31],
    "M": [17, 27, 21, 21, 17, 17, 17],
    "N": [17, 25, 21, 19, 17, 17, 17],
    "O": [14, 17, 17, 17, 17, 17, 14],
    "P": [30, 17, 17, 30, 16, 16, 16],
    "Q": [14, 17, 17, 17, 21, 18, 13],
    "R": [30, 17, 17, 30, 20, 18, 17],
    "S": [14, 17, 16, 14, 1, 17, 14],
    "T": [31, 4, 4, 4, 4, 4, 4],
    "U": [17, 17, 17, 17, 17, 17, 14],
    "V": [17, 17, 17, 17, 17, 10, 4],
    "W": [17, 17, 17, 21, 21, 21, 10],
    "X": [17, 17, 10, 4, 10, 17, 17],
    "Y": [17, 17, 10, 4, 4, 4, 4],
    "Z": [31, 1, 2, 4, 8, 16, 31],
}


def generate_mock_trajectory(file_path: Path, duration_sec: float = 10.0, hz: int = 30):
    total_frames = int(duration_sec * hz)
    records = []

    for i in range(total_frames):
        t = round(i / hz, 3)
        # 模拟机械臂末端 3 轴正弦运动及夹爪闭合曲线
        x = round(0.4 + 0.1 * math.sin(t * 1.5), 4)
        y = round(0.0 + 0.15 * math.cos(t * 1.5), 4)
        z = round(0.2 + 0.05 * math.sin(t * 3.0), 4)
        # 夹爪在 3.0s - 7.0s 处于抓取闭合状态
        gripper = 0.08 if (t < 3.0 or t > 7.0) else 0.01

        records.append({
            "timestamp": t,
            "frame_idx": i,
            "ee_pose": [x, y, z, 0.0, 3.14, 0.0],
            "gripper_width": gripper,
            "velocity": round(0.1 * math.cos(t * 1.5), 4)
        })

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    return total_frames


def _fill(img: np.ndarray, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int]) -> None:
    height, width = img.shape[:2]
    x0 = 0 if x0 < 0 else x0
    y0 = 0 if y0 < 0 else y0
    x1 = width if x1 > width else x1
    y1 = height if y1 > height else y1
    if x1 > x0 and y1 > y0:
        img[y0:y1, x0:x1] = color


def _text(img: np.ndarray, text: str, x: int, y: int, color: tuple[int, int, int], scale: int = 2) -> None:
    cursor = x
    for ch in text.upper():
        rows = _GLYPHS.get(ch, _GLYPHS[" "])
        for row_index, bits in enumerate(rows):
            for col in range(5):
                if bits & (1 << (4 - col)):
                    _fill(
                        img,
                        cursor + col * scale,
                        y + row_index * scale,
                        cursor + (col + 1) * scale,
                        y + (row_index + 1) * scale,
                        color,
                    )
        cursor += 6 * scale


def _phase(t: float) -> tuple[str, tuple[int, int, int]]:
    if t < 3.0:
        return "APPROACH", (59, 130, 246)
    if t < 5.0:
        return "GRASP", (34, 197, 94)
    if t <= 7.0:
        return "LIFT", (245, 158, 11)
    return "PLACE", (168, 85, 247)


def _render_frame(rec: dict, width: int = 960, height: int = 540) -> np.ndarray:
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:, :] = (11, 18, 32)
    _fill(img, 0, 0, width, 52, (15, 23, 42))
    _text(img, "OPENDF CAPTURE", 20, 12, (248, 250, 252), 3)
    _text(img, "EE SINE  30HZ", 20, 34, (148, 163, 184), 1)

    t = float(rec["timestamp"])
    label, color = _phase(t)
    _fill(img, 760, 12, 940, 40, color)
    _text(img, label, 778, 18, (255, 255, 255), 2)

    # Work surface.
    _fill(img, 36, 78, 680, 500, (30, 41, 59))
    _fill(img, 48, 92, 668, 486, (51, 65, 85))
    for gx in range(80, 660, 40):
        _fill(img, gx, 92, gx + 1, 486, (71, 85, 105))
    for gy in range(120, 480, 40):
        _fill(img, 48, gy, 668, gy + 1, (71, 85, 105))

    x, y, _z = rec["ee_pose"][:3]
    grip = float(rec["gripper_width"])

    def map_x(value: float) -> int:
        return int(90 + (value - 0.30) / 0.22 * 520)

    def map_y(value: float) -> int:
        return int(140 + (0.18 - value) / 0.36 * 280)

    gx = map_x(x)
    gy = map_y(y)

    # Object rests until the grasp window, then rides with the gripper.
    if t < 3.0:
        ox, oy = map_x(0.47), map_y(0.02)
    elif t <= 7.0:
        ox, oy = gx, gy + 34
    else:
        ox = map_x(0.4 + 0.1 * math.sin(7.0 * 1.5))
        oy = map_y(0.15 * math.cos(7.0 * 1.5)) + 34
    _fill(img, ox - 18, oy - 16, ox + 18, oy + 16, (245, 158, 11))
    _fill(img, ox - 8, oy - 22, ox + 8, oy - 14, (253, 224, 71))

    gap = int(10 + (grip / 0.08) * 26)
    _fill(img, gx - gap - 12, gy - 28, gx - gap, gy + 28, (226, 232, 240))
    _fill(img, gx + gap, gy - 28, gx + gap + 12, gy + 28, (226, 232, 240))
    _fill(img, gx - gap - 12, gy - 36, gx + gap + 12, gy - 26, (148, 163, 184))
    _fill(img, gx - 4, gy - 52, gx + 4, gy - 34, (203, 213, 225))

    # Side readout.
    _fill(img, 700, 78, 940, 500, (15, 23, 42))
    clock = f"{int(t // 60):02d}:{t % 60:05.2f}"
    _text(img, clock, 724, 100, (248, 250, 252), 3)
    _text(img, "GRIPPER", 724, 150, (148, 163, 184), 2)
    bar_w = int((grip / 0.10) * 180)
    _fill(img, 724, 176, 904, 196, (30, 41, 59))
    _fill(img, 724, 176, 724 + bar_w, 196, (59, 130, 246))
    _text(img, f"{grip:.2f} M", 724, 206, (191, 219, 254), 2)

    velocity = float(rec["velocity"])
    _text(img, "EE VELOCITY", 724, 250, (148, 163, 184), 2)
    _fill(img, 724, 276, 904, 296, (30, 41, 59))
    mid = 814
    vel_px = int((velocity / 0.12) * 80)
    if vel_px >= 0:
        _fill(img, mid, 276, mid + vel_px, 296, (251, 146, 60))
    else:
        _fill(img, mid + vel_px, 276, mid, 296, (251, 146, 60))
    _text(img, f"{velocity:+.3f}", 724, 306, (254, 215, 170), 2)

    pose = rec["ee_pose"]
    _text(img, "EE POSE", 724, 360, (148, 163, 184), 2)
    _text(img, f"X {pose[0]:.3f}", 724, 388, (226, 232, 240), 2)
    _text(img, f"Y {pose[1]:.3f}", 724, 412, (226, 232, 240), 2)
    _text(img, f"Z {pose[2]:.3f}", 724, 436, (226, 232, 240), 2)
    _text(img, f"F {int(rec['frame_idx']):04d}", 724, 468, (100, 116, 139), 2)
    return img


def generate_mock_video(file_path: Path, trajectory_path: Path, fps: int = 30) -> None:
    """Render a 10s H.264 clip whose gripper motion matches the trajectory JSON."""
    records = json.loads(Path(trajectory_path).read_text(encoding="utf-8"))
    if not records:
        raise ValueError("trajectory is empty")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 960, 540
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(file_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for rec in records:
            frame = np.ascontiguousarray(_render_frame(rec, width, height))
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        code = proc.wait(timeout=60)
    except Exception:
        proc.kill()
        proc.wait(timeout=10)
        raise
    if code != 0:
        err = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        raise RuntimeError(f"ffmpeg failed: {err[:500]}")
