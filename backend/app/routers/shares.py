from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..entities import DataShare
from ..models import User
from ..schemas_entities import ShareIn, ShareOut, ShareRespond
from ..services.audit import write_audit

router = APIRouter(prefix="/shares", tags=["shares"])

VALID_SCOPES = ("all", "supplier", "customer", "middle")


@router.get("", response_model=list[ShareOut])
def list_shares(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(DataShare)
        .filter((DataShare.requester_id == user.id) | (DataShare.target_id == user.id))
        .order_by(DataShare.id.desc())
        .all()
    )


@router.post("", response_model=ShareOut, status_code=201)
def create_share(
    body: ShareIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.target_id == user.id:
        raise HTTPException(status_code=400, detail="不能与自己共享")
    target = db.get(User, body.target_id)
    if target is None:
        raise HTTPException(status_code=400, detail="目标用户不存在")
    scopes = list(dict.fromkeys(body.scopes))
    if not scopes or any(s not in VALID_SCOPES for s in scopes):
        raise HTTPException(status_code=400, detail="共享范围不合法")
    exists = (
        db.query(DataShare)
        .filter(
            DataShare.status.in_(["pending", "active"]),
            (
                (DataShare.requester_id == user.id) & (DataShare.target_id == body.target_id)
            )
            | (
                (DataShare.requester_id == body.target_id) & (DataShare.target_id == user.id)
            ),
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="已存在待处理或生效中的共享关系")
    share = DataShare(
        requester_id=user.id,
        target_id=body.target_id,
        scopes=scopes,
        note=body.note,
    )
    db.add(share)
    db.flush()
    write_audit(db, request, user, "create", "share", str(share.id), new_value={"target": target.username, "scopes": scopes}, detail=f"向 {target.username} 发起共享申请")
    db.commit()
    db.refresh(share)
    return share


def _respond(db: Session, request: Request, user: User, share_id: int, accept: bool, note: str):
    share = db.get(DataShare, share_id)
    if share is None or share.target_id != user.id:
        raise HTTPException(status_code=404, detail="申请不存在或无权处理")
    if share.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已处理")
    requester = db.get(User, share.requester_id)
    share.status = "active" if accept else "rejected"
    share.responded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    share.responded_by = user.id
    share.note = note or share.note
    action = "approve" if accept else "reject"
    write_audit(db, request, user, "update", "share", str(share.id), old_value={"status": "pending"}, new_value={"status": share.status}, detail=f"{'批准' if accept else '拒绝'}与 {requester.username if requester else '?'} 的共享申请")
    db.commit()
    db.refresh(share)
    return share


@router.post("/{share_id}/approve", response_model=ShareOut)
def approve_share(share_id: int, body: ShareRespond, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _respond(db, request, user, share_id, accept=True, note=body.note)


@router.post("/{share_id}/reject", response_model=ShareOut)
def reject_share(share_id: int, body: ShareRespond, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _respond(db, request, user, share_id, accept=False, note=body.note)


@router.post("/{share_id}/cancel", response_model=ShareOut)
def cancel_share(share_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    share = db.get(DataShare, share_id)
    if share is None or (share.requester_id != user.id and share.target_id != user.id):
        raise HTTPException(status_code=404, detail="共享关系不存在")
    if share.status != "active":
        raise HTTPException(status_code=400, detail="仅生效中的共享关系可解除")
    other = db.get(User, share.target_id if share.requester_id == user.id else share.requester_id)
    old = {"status": share.status, "scopes": share.scopes}
    share.status = "cancelled"
    share.responded_at = datetime.now(timezone.utc).replace(tzinfo=None)
    share.responded_by = user.id
    write_audit(db, request, user, "update", "share", str(share.id), old_value=old, new_value={"status": "cancelled"}, detail=f"解除与 {other.username if other else '?'} 的共享关系")
    db.commit()
    db.refresh(share)
    return share
