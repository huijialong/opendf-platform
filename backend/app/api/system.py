import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import EXPORT_DIR, RAW_DIR, SETTINGS_PATH

router = APIRouter(prefix="/system", tags=["system"])

DEFAULT_SETTINGS = {
    "qa_ratio": 20,
    "sample_fps": 30,
    "action_labels": ["APPROACH", "GRASP", "LIFT", "MOVE", "PLACE"],
    "storage_raw": "storage/raw",
    "storage_export": "storage/export",
}


class SettingsIn(BaseModel):
    qa_ratio: int = Field(..., ge=10, le=100)
    sample_fps: int = Field(default=30, ge=1, le=120)
    action_labels: list[str] = Field(default_factory=lambda: list(DEFAULT_SETTINGS["action_labels"]))


def _read() -> dict:
    if not SETTINGS_PATH.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        stored = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        stored = {}
    merged = dict(DEFAULT_SETTINGS)
    merged.update(stored)
    return merged


@router.get("/settings")
def get_settings():
    data = _read()
    data["raw_files"] = len(list(RAW_DIR.glob("*"))) if RAW_DIR.exists() else 0
    data["export_files"] = len(list(EXPORT_DIR.glob("*.zip"))) if EXPORT_DIR.exists() else 0
    return {"code": 200, "message": "ok", "data": data}


@router.put("/settings")
def put_settings(payload: SettingsIn):
    if payload.qa_ratio not in {10, 20, 50, 100}:
        raise HTTPException(status_code=400, detail="抽检比例仅支持 10 / 20 / 50 / 100")
    data = _read()
    data.update(
        {
            "qa_ratio": payload.qa_ratio,
            "sample_fps": payload.sample_fps,
            "action_labels": [label.strip().upper() for label in payload.action_labels if label.strip()],
        }
    )
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"code": 200, "message": "配置已保存", "data": data}
