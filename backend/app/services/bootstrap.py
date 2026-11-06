"""Seed a small operational catalog the first time the database is created."""

from sqlalchemy.orm import Session

from app.db.models import Device, Task

DEVICES = [
    {
        "device_sn": "UMI-001",
        "device_type": "UMI_GRIPPER",
        "name": "Stanford UMI 手持夹爪 #1",
        "status": "ONLINE",
        "meta_json": {
            "ip": "192.168.10.21",
            "mac": "02:11:22:33:44:01",
            "firmware": "umi-1.4.2",
            "intrinsics": {"fx": 615.2, "fy": 614.8, "cx": 320.0, "cy": 240.0},
        },
    },
    {
        "device_sn": "PICO-004",
        "device_type": "PICO_VR",
        "name": "Pico Neo 3 头显 #4",
        "status": "ONLINE",
        "meta_json": {
            "ip": "192.168.10.34",
            "mac": "02:11:22:33:44:04",
            "firmware": "pico-5.8.1",
            "hz": 72,
        },
    },
    {
        "device_sn": "EGO-012",
        "device_type": "EGO_CAM",
        "name": "GoPro 头戴第一视角 #12",
        "status": "CALIBRATING",
        "meta_json": {
            "ip": "192.168.10.12",
            "mac": "02:11:22:33:44:12",
            "firmware": "hero-2.11",
            "resolution": "1920x1080",
        },
    },
    {
        "device_sn": "ARM-007",
        "device_type": "ROBOT_ARM",
        "name": "Piper 机械臂本体 #7",
        "status": "ONLINE",
        "meta_json": {
            "ip": "192.168.10.70",
            "mac": "02:11:22:33:44:70",
            "firmware": "piper-0.9.3",
            "dof": 6,
        },
    },
    {
        "device_sn": "ARM-008",
        "device_type": "ROBOT_ARM",
        "name": "Franka Research 3 #8",
        "status": "OFFLINE",
        "meta_json": {
            "ip": "192.168.10.80",
            "mac": "02:11:22:33:44:80",
            "firmware": "franka-5.6.0",
            "dof": 7,
        },
    },
]

TASKS = [
    {
        "task_code": "TSK-2026-001",
        "title": "桌面杯具抓取摆放",
        "scene_category": "机械臂抓取",
        "priority": "HIGH",
        "status": "ANNOTATING",
        "assignee": "林可",
        "sample_target": 80,
        "completed_samples": 12,
    },
    {
        "task_code": "TSK-2026-002",
        "title": "厨房双手装配第一视角",
        "scene_category": "VR第一视角",
        "priority": "MEDIUM",
        "status": "COLLECTING",
        "assignee": "周衡",
        "sample_target": 60,
        "completed_samples": 8,
    },
    {
        "task_code": "TSK-2026-003",
        "title": "UMI 布料折叠",
        "scene_category": "触觉作业",
        "priority": "URGENT",
        "status": "REVIEWING",
        "assignee": "赵敏",
        "sample_target": 40,
        "completed_samples": 36,
    },
    {
        "task_code": "TSK-2026-004",
        "title": "货架避障巡检",
        "scene_category": "工业巡检",
        "priority": "LOW",
        "status": "PENDING",
        "assignee": None,
        "sample_target": 50,
        "completed_samples": 0,
    },
    {
        "task_code": "TSK-2026-005",
        "title": "Franka 零件插接",
        "scene_category": "双手装配",
        "priority": "MEDIUM",
        "status": "DONE",
        "assignee": "陈述",
        "sample_target": 30,
        "completed_samples": 30,
    },
    {
        "task_code": "TSK-2026-006",
        "title": "抽屉开合与取物",
        "scene_category": "抓取摆放",
        "priority": "HIGH",
        "status": "CLEANING",
        "assignee": "林可",
        "sample_target": 45,
        "completed_samples": 20,
    },
]


def seed_if_empty(db: Session) -> None:
    if db.query(Device).count() == 0:
        db.add_all(Device(**row) for row in DEVICES)
    if db.query(Task).count() == 0:
        db.add_all(Task(**row) for row in TASKS)
    db.commit()
