from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..entities import DutyReport, OrderDocument
from ..models import User
from ..schemas_entities import OrderDocIn, OrderDocOut
from ..services.audit import write_audit
from ..services.duty import run_duty_for_user

router = APIRouter(tags=["duty"])


@router.get("/duty/reports/latest")
def latest_report(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(DutyReport).filter(DutyReport.user_id == user.id).order_by(DutyReport.id.desc()).first()
    if r is None:
        return {"report": None, "unread": 0}
    unread = db.query(DutyReport).filter(DutyReport.user_id == user.id, DutyReport.is_read == 0).count()
    return {
        "report": {
            "id": r.id, "content": r.content, "ai_text": r.ai_text,
            "is_read": bool(r.is_read), "created_at": str(r.created_at),
        },
        "unread": unread,
    }


@router.get("/duty/reports")
def list_reports(limit: int = 20, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(DutyReport)
        .filter(DutyReport.user_id == user.id)
        .order_by(DutyReport.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {"id": r.id, "content": r.content, "ai_text": r.ai_text, "is_read": bool(r.is_read), "created_at": str(r.created_at)}
        for r in rows
    ]


@router.post("/duty/run")
def run_now(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = run_duty_for_user(user)
    write_audit(db, request, user, "create", "duty_report", str(report.id), detail="手动触发值班机器人扫描")
    db.commit()
    return {"report": {"id": report.id, "content": report.content, "ai_text": report.ai_text, "created_at": str(report.created_at)}}


@router.post("/duty/reports/{rid}/read")
def mark_read(rid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.get(DutyReport, rid)
    if r is None or r.user_id != user.id:
        raise HTTPException(status_code=404, detail="简报不存在")
    # 查看最新简报即视为全部已读(历史简报不再悬挂未读)
    db.query(DutyReport).filter(DutyReport.user_id == user.id, DutyReport.is_read == 0).update({DutyReport.is_read: 1})
    db.commit()
    return {"ok": True}


# ---------- 订单合同文件 ----------
@router.get("/orders/{order_id}/documents", response_model=list[OrderDocOut])
def list_documents(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from .orders import _order_or_404

    _order_or_404(db, order_id, user)
    return db.query(OrderDocument).filter(OrderDocument.order_id == order_id).order_by(OrderDocument.id.desc()).all()


@router.post("/orders/{order_id}/documents", response_model=OrderDocOut, status_code=201)
def create_document(
    order_id: int, body: OrderDocIn, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    from .orders import _order_or_404

    _order_or_404(db, order_id, user)
    doc = OrderDocument(
        order_id=order_id, doc_type=body.doc_type, file_name=body.file_name,
        file_path=body.file_path, note=body.note,
        uploaded_by=user.id, uploaded_by_name=user.display_name or user.username,
    )
    db.add(doc)
    db.flush()
    write_audit(db, request, user, "create", "order_doc", str(doc.id), new_value=body.model_dump(), detail=f"订单#{order_id} 上传合同文件({body.doc_type}:{body.file_name})")
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/order-documents/{doc_id}")
def delete_document(doc_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.get(OrderDocument, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文件不存在")
    from .orders import _order_or_404

    _order_or_404(db, doc.order_id, user)
    old = {"doc_type": doc.doc_type, "file_name": doc.file_name}
    write_audit(db, request, user, "delete", "order_doc", str(doc.id), old_value=old, detail=f"删除合同文件 {doc.file_name}")
    db.delete(doc)
    db.commit()
    return {"ok": True}
