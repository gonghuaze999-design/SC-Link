from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..entities import Breach, Customer, Order, OrderTrack, Supplier
from ..models import User
from ..schemas_entities import (
    AiExtractRequest,
    BreachIn,
    BreachOut,
    BreachUpdate,
    OrderIn,
    OrderOut,
    OrderUpdate,
    StatusChange,
    TrackIn,
    TrackOut,
)
from ..services.ai_gateway import ai_enabled, extract_track_events, order_summary
from ..services.audit import write_audit
from ..services.locking import conditional_update
from ..services.visibility import apply_visibility

router = APIRouter(tags=["orders"])

ORDER_FIELDS = [
    "order_no", "product_line_id", "quantity", "unit_price", "total_amount", "currency",
    "supplier_id", "customer_id", "middle_ids", "payment_mode", "contract_no",
    "contract_file", "signed_at",
]

# 状态机:允许的流转
TRANSITIONS: dict[str, set[str]] = {
    "registered": {"sourcing", "breach"},
    "sourcing": {"sourced", "breach"},
    "sourced": {"paying", "breach"},
    "paying": {"paid", "breach"},
    "paid": {"arrived", "breach"},
    "arrived": {"delivered", "breach"},
    "delivered": {"done", "breach"},
    "breach": {"breach_processing"},
    "breach_processing": {"breach_resolved", "closed"},
    "breach_resolved": {"breach"},  # 再违约可再次进入
    "done": set(),
    "closed": set(),
}

STATUS_LABELS = {
    "registered": "已录入", "sourcing": "货源确认中", "sourced": "货源已确认",
    "paying": "付款中", "paid": "已付款", "arrived": "到货", "delivered": "已交付",
    "done": "已完成", "breach": "违约", "breach_processing": "违约处理中",
    "breach_resolved": "违约已解决", "closed": "已关闭",
}


def _order_or_404(db: Session, order_id: int, user: User) -> Order:
    obj = db.get(Order, order_id)
    if obj is None or not (
        obj.owner_id == user.id or user.role == "admin"
    ):
        raise HTTPException(status_code=404, detail="订单不存在或无权访问")
    return obj


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    status: str = "",
    keyword: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Order)
    q = apply_visibility(q, Order, db, user, "supplier")
    if status:
        q = q.filter(Order.status == status)
    if keyword:
        q = q.filter(Order.order_no.like(f"%{keyword}%") | Order.contract_no.like(f"%{keyword}%"))
    return q.order_by(Order.id.desc()).limit(200).all()


@router.post("/orders", response_model=OrderOut, status_code=201)
def create_order(body: OrderIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    obj = Order(**body.model_dump(), owner_id=user.id, last_editor_id=user.id)
    db.add(obj)
    db.flush()
    write_audit(db, request, user, "create", "order", str(obj.id), new_value=body.model_dump(), detail=f"录入订单 {body.order_no}")
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _order_or_404(db, order_id, user)


@router.patch("/orders/{order_id}", response_model=OrderOut)
def update_order(
    order_id: int, body: OrderUpdate, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    obj = _order_or_404(db, order_id, user)
    changes = body.model_dump(exclude_unset=True)
    changes.pop("version", None)
    old = {f: getattr(obj, f) for f in ORDER_FIELDS}
    ok = conditional_update(db, Order, obj.id, body.version, changes, user.id)
    if not ok:
        write_audit(db, request, user, "update_conflict", "order", str(obj.id), detail=f"版本冲突:基于 v{body.version} 更新被拒(当前 v{obj.version})")
        db.commit()
        raise HTTPException(status_code=409, detail=f"数据已被他人更新(当前版本 v{obj.version},你基于 v{body.version} 编辑),请刷新后重试")
    new = {**old, **changes}
    write_audit(db, request, user, "update", "order", str(obj.id), old_value=old, new_value=new, detail=f"更新订单 {obj.order_no}")
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/orders/{order_id}")
def delete_order(order_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    obj = _order_or_404(db, order_id, user)
    old = {"order_no": obj.order_no, "status": obj.status}
    write_audit(db, request, user, "delete", "order", str(obj.id), old_value=old, detail=f"删除订单 {obj.order_no}")
    db.query(OrderTrack).filter(OrderTrack.order_id == obj.id).delete()
    db.query(Breach).filter(Breach.order_id == obj.id).delete()
    db.delete(obj)
    db.commit()
    return {"ok": True}


@router.post("/orders/{order_id}/status", response_model=OrderOut)
def change_status(
    order_id: int, body: StatusChange, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    obj = _order_or_404(db, order_id, user)
    target = body.status
    if target not in TRANSITIONS:
        raise HTTPException(status_code=400, detail="状态不合法")
    old_status = obj.status
    old_version = obj.version
    allowed = TRANSITIONS.get(obj.status, set())
    detail_extra = ""
    changes: dict = {}
    if obj.status == "breach_processing" and target == "breach_resolved":
        # 违约解决:自动回到进入违约前的环节
        changes = {"status": obj.pre_breach_status or "sourcing", "pre_breach_status": ""}
        detail_extra = "(违约解决)"
    elif target not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"状态不可从「{STATUS_LABELS.get(obj.status, obj.status)}」流转到「{STATUS_LABELS.get(target, target)}」",
        )
    else:
        if target == "breach":
            changes = {"status": target, "pre_breach_status": obj.status}
        else:
            changes = {"status": target}
    ok = conditional_update(db, Order, obj.id, old_version, changes, user.id)
    if not ok:
        write_audit(db, request, user, "update_conflict", "order", str(obj.id), detail=f"状态流转冲突:基于 v{old_version} 被拒")
        db.commit()
        raise HTTPException(status_code=409, detail=f"数据已被他人更新(当前版本 v{obj.version}),请刷新后重试")
    new_status = changes.get("status")
    write_audit(db, request, user, "update", "order", str(obj.id), old_value={"status": old_status}, new_value={"status": new_status}, detail=f"订单 {obj.order_no} 状态 → {STATUS_LABELS.get(new_status, new_status)}{detail_extra}")
    db.commit()
    db.refresh(obj)
    return obj


# ================= 跟踪事件(只增不改) =================
@router.get("/orders/{order_id}/tracks", response_model=list[TrackOut])
def list_tracks(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _order_or_404(db, order_id, user)
    return db.query(OrderTrack).filter(OrderTrack.order_id == order_id).order_by(OrderTrack.id.desc()).all()


@router.post("/orders/{order_id}/tracks", response_model=TrackOut, status_code=201)
def create_track(
    order_id: int, body: TrackIn, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    _order_or_404(db, order_id, user)
    track = OrderTrack(
        order_id=order_id, category=body.category, title=body.title,
        content=body.content, attachment=body.attachment,
        created_by=user.id, created_by_name=user.display_name or user.username,
    )
    db.add(track)
    db.flush()
    write_audit(db, request, user, "create", "track", str(track.id), new_value=body.model_dump(), detail=f"订单#{order_id} 新增跟踪事件({body.category})")
    db.commit()
    db.refresh(track)
    return track


# ================= 违约事项 =================
@router.get("/orders/{order_id}/breaches", response_model=list[BreachOut])
def list_breaches(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _order_or_404(db, order_id, user)
    return db.query(Breach).filter(Breach.order_id == order_id).order_by(Breach.id.desc()).all()


@router.post("/orders/{order_id}/breaches", response_model=BreachOut, status_code=201)
def create_breach(
    order_id: int, body: BreachIn, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    _order_or_404(db, order_id, user)
    b = Breach(order_id=order_id, **body.model_dump())
    db.add(b)
    db.flush()
    write_audit(db, request, user, "create", "breach", str(b.id), new_value=body.model_dump(), detail=f"订单#{order_id} 新增违约事项({body.breach_party})")
    db.commit()
    db.refresh(b)
    return b


@router.patch("/breaches/{bid}", response_model=BreachOut)
def update_breach(
    bid: int, body: BreachUpdate, request: Request,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    b = db.get(Breach, bid)
    if b is None:
        raise HTTPException(status_code=404, detail="违约事项不存在")
    _order_or_404(db, b.order_id, user)
    changes = body.model_dump(exclude_unset=True)
    old = {"breach_party": b.breach_party, "solution": b.solution, "status": b.status}
    for f, v in changes.items():
        setattr(b, f, v)
    write_audit(db, request, user, "update", "breach", str(b.id), old_value=old, new_value=changes, detail=f"更新违约事项#{bid}")
    db.commit()
    db.refresh(b)
    return b


# ================= 跟单 AI =================
@router.post("/orders/{order_id}/ai-summary")
def ai_summary(order_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not ai_enabled():
        raise HTTPException(status_code=400, detail="未配置 Gemini API key,AI 摘要暂不可用")
    obj = _order_or_404(db, order_id, user)
    tracks = (
        db.query(OrderTrack)
        .filter(OrderTrack.order_id == order_id)
        .order_by(OrderTrack.id.asc())
        .limit(30)
        .all()
    )
    info = {
        "order_no": obj.order_no, "status": STATUS_LABELS.get(obj.status, obj.status),
        "quantity": obj.quantity, "unit_price": float(obj.unit_price) if obj.unit_price else None,
        "total_amount": float(obj.total_amount) if obj.total_amount else None,
        "currency": obj.currency, "payment_mode": obj.payment_mode,
        "contract_no": obj.contract_no, "signed_at": str(obj.signed_at),
    }
    track_list = [
        {"category": t.category, "title": t.title, "content": t.content, "at": str(t.created_at)}
        for t in tracks
    ]
    text = order_summary(info, track_list)
    if text is None:
        raise HTTPException(status_code=502, detail="AI 生成失败,请稍后重试")
    return {"summary": text}


@router.post("/orders/{order_id}/ai-extract")
def ai_extract(
    order_id: int, body: AiExtractRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    if not ai_enabled():
        raise HTTPException(status_code=400, detail="未配置 Gemini API key,AI 提取暂不可用")
    _order_or_404(db, order_id, user)
    events = extract_track_events(body.text)
    if events is None:
        raise HTTPException(status_code=502, detail="AI 提取失败,请稍后重试")
    return {"events": events}
