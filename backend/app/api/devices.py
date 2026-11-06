from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import DEVICE_TYPES
from app.db.database import get_db
from app.db.models import Device
from app.schemas.task import DeviceIn, DeviceUpdate
from app.services.present import device_dict, ok

router = APIRouter(prefix="/devices", tags=["devices"])


def _get(db: Session, device_id: int) -> Device:
    row = db.query(Device).filter(Device.id == device_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="设备不存在")
    return row


@router.get("")
def list_devices(
    keyword: str | None = None,
    device_type: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Device)
    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.filter((Device.name.like(like)) | (Device.device_sn.like(like)))
    if device_type:
        query = query.filter(Device.device_type == device_type)
    if status:
        query = query.filter(Device.status == status)
    total = query.count()
    rows = (
        query.order_by(Device.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ok({"items": [device_dict(row) for row in rows], "total": total, "page": page})


@router.post("")
def create_device(payload: DeviceIn, db: Session = Depends(get_db)):
    if payload.device_type not in DEVICE_TYPES:
        raise HTTPException(status_code=400, detail="不支持的设备类型")
    if db.query(Device).filter(Device.device_sn == payload.device_sn).first():
        raise HTTPException(status_code=400, detail="设备序列号已存在")
    row = Device(
        device_sn=payload.device_sn.strip(),
        device_type=payload.device_type,
        name=payload.name.strip(),
        status=payload.status or "ONLINE",
        meta_json=payload.meta_json or {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ok(device_dict(row), "设备已登记")


@router.get("/{device_id}")
def get_device(device_id: int, db: Session = Depends(get_db)):
    return ok(device_dict(_get(db, device_id)))


@router.put("/{device_id}")
def update_device(device_id: int, payload: DeviceUpdate, db: Session = Depends(get_db)):
    row = _get(db, device_id)
    data = payload.model_dump(exclude_unset=True)
    if "device_type" in data and data["device_type"] not in DEVICE_TYPES:
        raise HTTPException(status_code=400, detail="不支持的设备类型")
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return ok(device_dict(row), "设备已更新")


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    row = _get(db, device_id)
    db.delete(row)
    db.commit()
    return ok({"id": device_id}, "设备已删除")
