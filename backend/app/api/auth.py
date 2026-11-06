from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/auth", tags=["auth"])

USERS = [
    {
        "username": "admin",
        "name": "系统管理员",
        "role": "超级管理员",
        "password": "opendf",
        "status": "启用",
    },
    {
        "username": "collector",
        "name": "林可",
        "role": "采集人员",
        "password": "opendf",
        "status": "启用",
    },
    {
        "username": "qa",
        "name": "周衡",
        "role": "标注与质检员",
        "password": "opendf",
        "status": "启用",
    },
]


class LoginIn(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


def public_user(row: dict) -> dict:
    return {
        "username": row["username"],
        "name": row["name"],
        "role": row["role"],
        "status": row["status"],
    }


@router.post("/login")
def login(payload: LoginIn):
    found = next((row for row in USERS if row["username"] == payload.username), None)
    if not found or found["password"] != payload.password:
        raise HTTPException(status_code=401, detail="账号或密码错误")
    return {
        "code": 200,
        "message": "ok",
        "data": {
            "token": f"opendf-{found['username']}",
            "user": public_user(found),
        },
    }


@router.get("/users")
def list_users():
    return {"code": 200, "message": "ok", "data": {"items": [public_user(row) for row in USERS]}}
