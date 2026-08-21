from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import User
from ..schemas import UserBrief, UserCreate, UserOut, UserUpdate
from ..config import settings
from ..security import hash_password
from ..services.audit import write_audit

router = APIRouter(prefix="/users", tags=["users"])

VALID_ROLES = ("admin", "user")
VALID_STATUSES = ("active", "disabled")


@router.get("/initial-password")
def initial_password(admin: User = Depends(require_admin)):
    return {"initial_password": settings.default_user_password}


@router.get("/options", response_model=list[UserBrief])
def user_options(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(User).filter(User.status == "active").order_by(User.id).all()


@router.get("", response_model=list[UserOut])
def list_users(
    keyword: str = "",
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(User)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(User.username.like(like) | User.display_name.like(like))
    return q.order_by(User.id).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="角色不合法")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="账号已存在")

    init_pwd = body.password or settings.default_user_password
    user = User(
        username=body.username,
        password_hash=hash_password(init_pwd),
        display_name=body.display_name,
        role=body.role,
        phone=body.phone,
        email=body.email,
        must_change_password=1,
    )
    db.add(user)
    db.flush()
    write_audit(
        db,
        request,
        admin,
        "create",
        "user",
        str(user.id),
        new_value=body.model_dump(exclude={"password"}),
        detail=f"创建账号 {body.username}({body.role}),初设密码统一,登录后须改密",
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")

    changes = body.model_dump(exclude_unset=True)
    if "role" in changes and changes["role"] not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="角色不合法")
    if "status" in changes and changes["status"] not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="状态不合法")
    if user.id == admin.id and changes.get("status") == "disabled":
        raise HTTPException(status_code=400, detail="不能停用自己的账号")

    old = {
        "display_name": user.display_name,
        "role": user.role,
        "status": user.status,
        "phone": user.phone,
        "email": user.email,
    }

    if changes.pop("reset_password", None):
        user.password_hash = hash_password(settings.default_user_password)
        user.must_change_password = 1
        write_audit(db, request, admin, "update", "user", str(user.id), detail="重置为统一初设密码(登录后须改密)")

    if changes.pop("unlock", None):
        user.locked_until = None
        user.failed_attempts = 0
        write_audit(db, request, admin, "update", "user", str(user.id), detail="解锁账号")

    for field, value in changes.items():
        setattr(user, field, value)

    new = {
        "display_name": user.display_name,
        "role": user.role,
        "status": user.status,
        "phone": user.phone,
        "email": user.email,
    }
    if old != new or "new_password" in body.model_dump(exclude_unset=True):
        write_audit(
            db, request, admin, "update", "user", str(user.id),
            old_value=old, new_value=new, detail="修改用户信息",
        )
    db.commit()
    db.refresh(user)
    return user
