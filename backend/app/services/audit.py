from fastapi import Request
from sqlalchemy.orm import Session

from ..models import AuditLog, LoginLog, User


def write_audit(
    db: Session,
    request: Request,
    user: User | None,
    action: str,
    entity_type: str = "",
    entity_id: str = "",
    old_value: dict | None = None,
    new_value: dict | None = None,
    detail: str = "",
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            username=user.username if user else "",
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            detail=detail,
            old_value=old_value,
            new_value=new_value,
            ip=request.client.host if request.client else "",
            user_agent=(request.headers.get("user-agent") or "")[:256],
        )
    )


def write_login_log(db: Session, request: Request, username: str, result: str, detail: str = "") -> None:
    db.add(
        LoginLog(
            username=username,
            result=result,
            detail=detail,
            ip=request.client.host if request.client else "",
            user_agent=(request.headers.get("user-agent") or "")[:256],
        )
    )
