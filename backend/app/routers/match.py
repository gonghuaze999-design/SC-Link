from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..entities import (
    Customer,
    DetailRequest,
    MatchResult,
    Publication,
    Supplier,
    UserPriority,
)
from ..models import User
from ..schemas_entities import (
    DetailRequestIn,
    DetailRequestOut,
    DetailRespond,
    PriorityIn,
    PriorityOut,
)
from ..services.audit import write_audit
from ..services.matching import demand_verified, score_supplier
from ..services.visibility import can_access_entity

router = APIRouter(tags=["match"])


def _supplier_full(db: Session, supplier: Supplier) -> dict:
    return {
        "id": supplier.id,
        "name": supplier.name,
        "short_name": supplier.short_name,
        "reg_location": supplier.reg_location,
        "credit_code": supplier.credit_code,
        "chain_role": supplier.chain_role,
        "procurement_modes": supplier.procurement_modes,
        "goods_type": supplier.goods_type,
        "price": float(supplier.price) if supplier.price is not None else None,
        "currency": supplier.currency,
        "price_valid_until": str(supplier.price_valid_until) if supplier.price_valid_until else None,
        "moq": supplier.moq,
        "delivery_cycle": supplier.delivery_cycle,
        "payment_terms": supplier.payment_terms,
        "guarantee_type": supplier.guarantee_type,
        "guarantee_ratio": supplier.guarantee_ratio,
        "guarantee_issuer": supplier.guarantee_issuer,
        "guarantee_issuer_name": supplier.guarantee_issuer_name,
        "coop_status": supplier.coop_status,
        "fulfillment_rate": supplier.fulfillment_rate,
        "credit_rating": supplier.credit_rating,
        "owner_id": supplier.owner_id,
        "updated_at": str(supplier.updated_at),
    }


def _supplier_brief(db: Session, supplier: Supplier, owner_name: str) -> dict:
    return {
        "id": supplier.id,
        "name": supplier.name,
        "short_name": supplier.short_name,
        "goods_type": supplier.goods_type,
        "price": float(supplier.price) if supplier.price is not None else None,
        "currency": supplier.currency,
        "procurement_modes": supplier.procurement_modes,
        "updated_at": str(supplier.updated_at),
        "owner_id": supplier.owner_id,
        "owner_name": owner_name,
    }


def _demand_from_customer(db: Session, customer: Customer) -> dict:
    product_line_id = None
    if customer.intent_products:
        product_line_id = customer.intent_products[0].get("product_line_id")
    quantity = 0
    try:
        quantity = int(float(customer.intent_quantity or 0))
    except (TypeError, ValueError):
        quantity = 0
    return {
        "product_line_id": product_line_id,
        "quantity": quantity,
        "intent_modes": customer.intent_modes or [],
        "goods_preference": customer.goods_preference or "",
        "price_min": None,
        "price_max": None,
        "verified": demand_verified(db, customer.id),
    }


def _demand_from_publication(db: Session, pub: Publication) -> dict:
    quantity = 0
    try:
        quantity = int(float(pub.quantity or 0))
    except (TypeError, ValueError):
        quantity = 0
    return {
        "product_line_id": pub.product_line_id,
        "quantity": quantity,
        "intent_modes": pub.intent_modes or [],
        "goods_preference": pub.goods_preference or "",
        "price_min": float(pub.price_min) if pub.price_min is not None else None,
        "price_max": float(pub.price_max) if pub.price_max is not None else None,
        "verified": False,
    }


def _owner_name(db: Session, owner_id: int) -> str:
    u = db.get(User, owner_id)
    return (u.display_name or u.username) if u else f"用户#{owner_id}"


def _has_full_access(db: Session, user: User, supplier: Supplier) -> bool:
    if can_access_entity(db, user, "supplier", supplier.owner_id):
        return True
    approved = (
        db.query(DetailRequest.id)
        .filter(
            DetailRequest.requester_id == user.id,
            DetailRequest.entity_type == "supplier",
            DetailRequest.entity_id == supplier.id,
            DetailRequest.status == "approved",
        )
        .first()
        is not None
    )
    return approved


@router.get("/match")
def run_match(
    request: Request,
    customer_id: int | None = None,
    publication_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if (customer_id is None) == (publication_id is None):
        raise HTTPException(status_code=400, detail="customer_id 与 publication_id 二选一")

    demand_type, demand_id = ("customer", customer_id) if customer_id else ("publication", publication_id)
    if demand_type == "customer":
        cust = db.get(Customer, customer_id)
        if cust is None or not can_access_entity(db, user, "customer", cust.owner_id):
            raise HTTPException(status_code=404, detail="客户不存在或无权访问")
        demand = _demand_from_customer(db, cust)
    else:
        pub = db.get(Publication, publication_id)
        if pub is None:
            raise HTTPException(status_code=404, detail="发布不存在")
        if pub.user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="仅发布人可基于该发布匹配")
        demand = _demand_from_publication(db, pub)

    suppliers = db.query(Supplier).all()
    results, failed = [], []
    for s in suppliers:
        out, fail = score_supplier(db, user.id, s, demand)
        if fail:
            failed.append({"supplier_id": s.id, "name": s.name, "reason": fail})
            continue
        full = _has_full_access(db, user, s)
        entity = _supplier_full(db, s) if full else _supplier_brief(db, s, _owner_name(db, s.owner_id))
        results.append(
            {
                "score": out["score"],
                "breakdown": out["breakdown"],
                "reasons": out["reasons"],
                "available_quantity": out["available_quantity"],
                "entity": entity,
                "full": full,
            }
        )
    results.sort(key=lambda x: -x["score"])

    # 快照入库(重算时重建)
    db.query(MatchResult).filter(MatchResult.demand_type == demand_type, MatchResult.demand_id == demand_id).delete()
    for r in results[:50]:
        db.add(
            MatchResult(
                demand_type=demand_type,
                demand_id=demand_id,
                supplier_id=r["entity"]["id"],
                score=r["score"],
                breakdown=r["breakdown"],
                reasons=r["reasons"],
            )
        )
    write_audit(db, request, user, "create", "match", f"{demand_type}#{demand_id}", detail=f"执行匹配:命中 {len(results)} 条,过滤 {len(failed)} 条")
    db.commit()

    return {"demand_type": demand_type, "demand_id": demand_id, "results": results, "filtered": failed}


# ================= 优先级 =================
@router.get("/priorities", response_model=list[PriorityOut])
def list_priorities(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(UserPriority).filter(UserPriority.user_id == user.id).all()


@router.put("/priorities", response_model=PriorityOut)
def set_priority(
    body: PriorityIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(UserPriority)
        .filter(
            UserPriority.user_id == user.id,
            UserPriority.entity_type == body.entity_type,
            UserPriority.entity_id == body.entity_id,
        )
        .first()
    )
    if row is None:
        row = UserPriority(user_id=user.id, entity_type=body.entity_type, entity_id=body.entity_id, priority=body.priority)
        db.add(row)
        db.flush()
    old = {"priority": row.priority}
    row.priority = body.priority
    write_audit(db, request, user, "update", "priority", str(row.id), old_value=old, new_value={"priority": body.priority}, detail=f"设置 {body.entity_type}#{body.entity_id} 优先级 {body.priority}")
    db.commit()
    db.refresh(row)
    return row


@router.delete("/priorities/{entity_type}/{entity_id}")
def clear_priority(entity_type: str, entity_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = (
        db.query(UserPriority)
        .filter(
            UserPriority.user_id == user.id,
            UserPriority.entity_type == entity_type,
            UserPriority.entity_id == entity_id,
        )
        .first()
    )
    if row is None:
        return {"ok": True}
    write_audit(db, request, user, "delete", "priority", str(row.id), old_value={"priority": row.priority}, detail=f"清除 {entity_type}#{entity_id} 优先级")
    db.delete(row)
    db.commit()
    return {"ok": True}


# ================= 详情申请 =================
@router.get("/detail-requests", response_model=list[DetailRequestOut])
def list_detail_requests(
    mine: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(DetailRequest)
    if mine == "pending":
        q = q.filter(DetailRequest.status == "pending")
        q = q.join(Supplier, DetailRequest.entity_id == Supplier.id).filter(Supplier.owner_id == user.id)
        return q.order_by(DetailRequest.id.desc()).all()
    q = q.filter((DetailRequest.requester_id == user.id) | (DetailRequest.responded_by == user.id))
    return q.order_by(DetailRequest.id.desc()).limit(100).all()


@router.post("/detail-requests", response_model=DetailRequestOut, status_code=201)
def create_detail_request(
    body: DetailRequestIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.entity_type == "supplier":
        obj = db.get(Supplier, body.entity_id)
    else:
        obj = db.get(Customer, body.entity_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="主体不存在")
    if can_access_entity(db, user, body.entity_type, obj.owner_id):
        raise HTTPException(status_code=400, detail="你已可查看该数据全量,无需申请")
    approved = (
        db.query(DetailRequest.id)
        .filter(
            DetailRequest.requester_id == user.id,
            DetailRequest.entity_type == body.entity_type,
            DetailRequest.entity_id == body.entity_id,
            DetailRequest.status == "approved",
        )
        .first()
        is not None
    )
    if approved:
        raise HTTPException(status_code=400, detail="你已获批查看该数据全量,无需重复申请")
    exists = (
        db.query(DetailRequest)
        .filter(
            DetailRequest.requester_id == user.id,
            DetailRequest.entity_type == body.entity_type,
            DetailRequest.entity_id == body.entity_id,
            DetailRequest.status == "pending",
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="已有待处理的申请")
    req = DetailRequest(requester_id=user.id, entity_type=body.entity_type, entity_id=body.entity_id, note=body.note)
    db.add(req)
    db.flush()
    write_audit(db, request, user, "create", "detail_request", str(req.id), new_value=body.model_dump(), detail=f"申请查看 {body.entity_type}#{body.entity_id} 全量信息")
    db.commit()
    db.refresh(req)
    return req


@router.post("/detail-requests/{rid}/approve", response_model=DetailRequestOut)
def approve_detail_request(rid: int, body: DetailRespond, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _respond(db, request, user, rid, "approved", body.note)


@router.post("/detail-requests/{rid}/reject", response_model=DetailRequestOut)
def reject_detail_request(rid: int, body: DetailRespond, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _respond(db, request, user, rid, "rejected", body.note)


def _respond(db: Session, request: Request, user: User, rid: int, status: str, note: str):
    req = db.get(DetailRequest, rid)
    if req is None or req.status != "pending":
        raise HTTPException(status_code=404, detail="申请不存在或已处理")
    if req.entity_type == "supplier":
        obj = db.get(Supplier, req.entity_id)
    else:
        obj = db.get(Customer, req.entity_id)
    if obj is None or not can_access_entity(db, user, req.entity_type, obj.owner_id):
        raise HTTPException(status_code=403, detail="仅数据维护人可处理该申请")
    from datetime import datetime as dt
    from datetime import timezone

    req.status = status
    req.responded_at = dt.now(timezone.utc).replace(tzinfo=None)
    req.responded_by = user.id
    req.note = note or req.note
    write_audit(db, request, user, "update", "detail_request", str(req.id), old_value={"status": "pending"}, new_value={"status": status}, detail=f"{'批准' if status == 'approved' else '拒绝'}详情查看申请")
    db.commit()
    db.refresh(req)
    return req
