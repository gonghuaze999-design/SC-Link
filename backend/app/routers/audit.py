from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import AuditLog, LoginLog, User
from ..schemas import AuditLogOut, LoginLogOut

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    keyword: str = "",
    action: str = "",
    entity_type: str = "",
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            AuditLog.username.like(like)
            | AuditLog.entity_id.like(like)
            | AuditLog.detail.like(like)
        )
    if action:
        q = q.filter(AuditLog.action == action)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if from_ts:
        q = q.filter(AuditLog.created_at >= from_ts)
    if to_ts:
        q = q.filter(AuditLog.created_at <= to_ts)
    return q.order_by(AuditLog.id.desc()).offset(offset).limit(limit).all()


@router.get("/login", response_model=list[LoginLogOut])
def list_login_logs(
    username: str = "",
    result: str = "",
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    q = db.query(LoginLog)
    if username:
        q = q.filter(LoginLog.username.like(f"%{username}%"))
    if result:
        q = q.filter(LoginLog.result == result)
    return q.order_by(LoginLog.id.desc()).offset(offset).limit(limit).all()
