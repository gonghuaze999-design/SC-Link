from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import ChangePasswordRequest, LoginRequest, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password
from ..services.audit import write_audit, write_login_log

router = APIRouter(prefix="/auth", tags=["auth"])


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _is_locked(user: User, now: datetime) -> bool:
    return bool(user.locked_until and user.locked_until > now)


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    now = _now_naive()
    user = db.query(User).filter(User.username == body.username).first()

    if user is None:
        write_login_log(db, request, body.username, "fail", "账号不存在")
        db.commit()
        raise HTTPException(status_code=401, detail="账号或密码错误")

    if user.status != "active":
        write_login_log(db, request, body.username, "fail", "账号已停用")
        db.commit()
        raise HTTPException(status_code=403, detail="账号已停用,请联系管理员")

    if _is_locked(user, now):
        remain_min = int((user.locked_until - now).total_seconds() // 60) + 1
        write_login_log(db, request, body.username, "lockout", "锁定期内尝试登录")
        db.commit()
        raise HTTPException(
            status_code=423, detail=f"账号已锁定,请 {remain_min} 分钟后再试"
        )

    if not verify_password(body.password, user.password_hash):
        user.failed_attempts += 1
        detail = f"密码错误({user.failed_attempts}/{settings.max_login_attempts})"
        if user.failed_attempts >= settings.max_login_attempts:
            user.locked_until = now + timedelta(minutes=settings.lockout_minutes)
            user.failed_attempts = 0
            detail = f"连续失败达上限,锁定 {settings.lockout_minutes} 分钟"
        write_login_log(db, request, body.username, "fail", detail)
        db.commit()
        raise HTTPException(status_code=401, detail="账号或密码错误")

    user.failed_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    write_login_log(db, request, body.username, "success")
    write_audit(db, request, user, "login", "user", str(user.id), detail="登录成功")
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.username, user.role)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if body.old_password == body.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    user.password_hash = hash_password(body.new_password)
    write_audit(db, request, user, "update", "user", str(user.id), detail="修改密码")
    db.commit()
    return {"ok": True}
