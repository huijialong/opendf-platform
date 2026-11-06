"""Base paths and runtime settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
RAW_DIR = STORAGE_DIR / "raw"
EXPORT_DIR = STORAGE_DIR / "export"
SETTINGS_PATH = STORAGE_DIR / "settings.json"

# Platform overview figures from the product contract. The four dashboard
# cards render these values directly.
PLATFORM_STATS = {
    "device_count": 47,
    "storage_bytes": 192414534860800,
    "storage_formatted": "175 TB",
    "active_tasks": 20,
    "dataset_count": 95,
}

PIPELINE_STEPS = [
    {"step": 1, "name": "多源数据采集", "desc": "支持多机器人本体、机械臂等采集方式"},
    {"step": 2, "name": "数据上传", "desc": "支持批量断点上传与实时同步"},
    {"step": 3, "name": "云端/本地存储", "desc": "分布式存储与版本管理"},
    {"step": 4, "name": "数据清洗标注", "desc": "时序去噪与多模态专业标注"},
    {"step": 5, "name": "审核通过", "desc": "质量多级审核，确保时序完整"},
    {"step": 6, "name": "高质量数据集", "desc": "形成标准化数据集，支持 LeRobot 导出"},
]

DEVICE_TYPES = ("UMI_GRIPPER", "PICO_VR", "EGO_CAM", "ROBOT_ARM")
TASK_STATUSES = ("PENDING", "CLEANING", "COLLECTING", "ANNOTATING", "REVIEWING", "DONE")
PRIORITIES = ("LOW", "MEDIUM", "HIGH", "URGENT")
ACTION_LABELS = ("APPROACH", "GRASP", "LIFT", "MOVE", "PLACE")
REVIEW_DECISIONS = ("APPROVED", "REJECTED")


class Settings(BaseSettings):
    app_name: str = "OpenDF 具身智能采标平台"
    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "*"

    model_config = SettingsConfigDict(env_prefix="OPENDF_", extra="ignore")


settings = Settings()
