"""个人行动工作台:待办审批/在途订单/到期提醒/值班简报/陈旧信息 一屏聚合"""
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..entities import (
    CapitalVerification,
    Customer,
    DataShare,
    DetailRequest,
    DutyReport,
    Order,
    Publication,
    Supplier,
    SupplierQuota,
)
from ..models import User
from ..services.visibility import apply_visibility, visible_owner_ids

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

STALE_DAYS = 3


def _today() -> date:
    return datetime.now(timezone.utc).date()


@router.get("/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # ---- 待我审批 ----
    pending_shares = (
        db.query(DataShare)
        .filter(DataShare.target_id == user.id, DataShare.status == "pending")
        .count()
    )
    pending_detail_requests = (
        db.query(DetailRequest)
        .filter(DetailRequest.status == "pending")
        .count()
    )
    if user.role != "admin":
        # 详情申请须看实体归属是否为我
        mine_sup = {s.id for s in db.query(Supplier).filter(Supplier.owner_id == user.id).all()}
        pending_detail_requests = (
            db.query(DetailRequest)
            .filter(
                DetailRequest.status == "pending",
                DetailRequest.entity_type == "supplier",
                DetailRequest.entity_id.in_(mine_sup),
            )
            .count()
        )

    # ---- 我的在途订单(违约优先) ----
    orders_q = apply_visibility(db.query(Order), Order, db, user, "supplier")
    active_orders = (
        orders_q.filter(~Order.status.in_(["done", "closed"]))
        .order_by(Order.updated_at.desc())
        .limit(8)
        .all()
    )
    orders_out = []
    for o in active_orders:
        sup = db.get(Supplier, o.supplier_id) if o.supplier_id else None
        cus = db.get(Customer, o.customer_id) if o.customer_id else None
        orders_out.append(
            {
                "id": o.id,
                "order_no": o.order_no,
                "status": o.status,
                "quantity": o.quantity,
                "total_amount": float(o.total_amount or 0),
                "supplier_name": sup.name if sup else "",
                "customer_name": cus.name if cus else "",
                "updated_at": str(o.updated_at),
            }
        )
    orders_out.sort(key=lambda x: (x["status"] not in ("breach", "breach_processing"), -(x["updated_at"] > x["updated_at"])))  # 违约在前
    orders_out.sort(key=lambda x: 0 if x["status"] in ("breach", "breach_processing") else 1)

    # ---- 到期提醒(配额+验资,7 天内) ----
    s_owners, _ = visible_owner_ids(db, user, "supplier")
    c_owners, _ = visible_owner_ids(db, user, "customer")
    if user.role == "admin":
        sup_q = db.query(Supplier)
        cus_q = db.query(Customer)
    else:
        sup_q = db.query(Supplier).filter(Supplier.owner_id.in_(s_owners))
        cus_q = db.query(Customer).filter(Customer.owner_id.in_(c_owners))
    sup_ids = {s.id for s in sup_q.all()}
    cus_ids = {c.id for c in cus_q.all()}

    today = _today()
    expiring = []
    for q in db.query(SupplierQuota).filter(SupplierQuota.status == "available", SupplierQuota.supplier_id.in_(sup_ids)).all():
        if q.quota_end_at and today <= q.quota_end_at <= today + timedelta(days=7):
            sup = db.get(Supplier, q.supplier_id)
            expiring.append({"type": "配额", "detail": f"{sup.name if sup else '?'} 配额 {q.batch_no or '#' + str(q.id)} {q.quota_end_at} 到期(剩 {(q.quota_end_at - today).days} 天)"})
    for v in db.query(CapitalVerification).filter(CapitalVerification.review_status == "approved", CapitalVerification.customer_id.in_(cus_ids)).all():
        if v.valid_until and today <= v.valid_until <= today + timedelta(days=7):
            cus = db.get(Customer, v.customer_id)
            expiring.append({"type": "验资", "detail": f"{cus.name if cus else '?'} 验资 {v.valid_until} 到期"})
    expiring.sort(key=lambda x: x["detail"])

    # ---- 值班简报摘要 ----
    duty = db.query(DutyReport).filter(DutyReport.user_id == user.id).order_by(DutyReport.id.desc()).first()
    duty_out = None
    if duty:
        duty_out = {
            "id": duty.id,
            "ai_text": (duty.ai_text or "")[:160],
            "note": (duty.content or {}).get("note", ""),
            "created_at": str(duty.created_at),
        }
    unread_duty = db.query(DutyReport).filter(DutyReport.user_id == user.id, DutyReport.is_read == 0).count()

    # ---- 陈旧信息(>3 天未更新,最多 8 条) ----
    stale = []
    for s in sup_q.all():
        if (today - s.updated_at.date()).days > STALE_DAYS:
            stale.append({"type": "供货方", "name": s.name, "days": (today - s.updated_at.date()).days})
    for c in cus_q.all():
        if (today - c.updated_at.date()).days > STALE_DAYS:
            stale.append({"type": "客户", "name": c.name, "days": (today - c.updated_at.date()).days})
    if user.role == "admin":
        pub_q = db.query(Publication)
    else:
        pub_q = db.query(Publication).filter((Publication.visibility == "public") | (Publication.user_id == user.id))
    for p in pub_q.filter(Publication.status == "active").all():
        if (today - p.updated_at.date()).days > STALE_DAYS:
            stale.append({"type": "需求", "name": p.title, "days": (today - p.updated_at.date()).days})
    stale.sort(key=lambda x: -x["days"])

    # ---- 快捷统计 ----
    active_pubs = pub_q.filter(Publication.status == "active").count()

    return {
        "pending_shares": pending_shares,
        "pending_detail_requests": pending_detail_requests,
        "orders": orders_out,
        "active_orders_count": len(active_orders),
        "expiring": expiring,
        "duty": duty_out,
        "unread_duty": unread_duty,
        "stale": stale[:8],
        "stats": {
            "supplier_count": len(sup_ids),
            "customer_count": len(cus_ids),
            "active_pubs": active_pubs,
        },
    }
