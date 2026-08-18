from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..entities import (
    CapitalVerification,
    Customer,
    MiddleLayer,
    Order,
    OverseasChain,
    Supplier,
    SupplierQuota,
)
from ..models import AuditLog, User
from ..services.visibility import visible_owner_ids

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _today() -> date:
    return datetime.now(timezone.utc).date()


@router.get("/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    suppliers_q = db.query(Supplier)
    customers_q = db.query(Customer)
    if user.role != "admin":
        s_owners, _ = visible_owner_ids(db, user, "supplier")
        c_owners, _ = visible_owner_ids(db, user, "customer")
        suppliers_q = suppliers_q.filter(Supplier.owner_id.in_(s_owners))
        customers_q = customers_q.filter(Customer.owner_id.in_(c_owners))

    supplier_count = suppliers_q.count()
    customer_count = customers_q.count()
    chain_count = db.query(OverseasChain).count() if user.role == "admin" else db.query(OverseasChain).filter(OverseasChain.owner_id.in_(s_owners)).count()
    middle_count = db.query(MiddleLayer).count() if user.role == "admin" else db.query(MiddleLayer).filter(MiddleLayer.owner_id.in_(c_owners)).count()

    verified_ids = {
        r[0]
        for r in db.query(CapitalVerification.customer_id)
        .filter(CapitalVerification.review_status == "approved")
        .all()
    }
    verified_count = sum(1 for c in customers_q.all() if c.id in verified_ids)
    verified_rate = round(verified_count / customer_count * 100) if customer_count else 0

    active_orders = db.query(Order).filter(~Order.status.in_(["done", "closed"])).count()
    month_start = datetime(_today().year, _today().month, 1)
    month_amount = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.created_at >= month_start)
        .scalar()
    )

    # 配额到期预警(7 天内)
    expiring = []
    today = _today()
    for q in db.query(SupplierQuota).filter(SupplierQuota.status == "available").all():
        if q.quota_end_at and today <= q.quota_end_at <= today + timedelta(days=7):
            sup = db.get(Supplier, q.supplier_id)
            expiring.append(
                {
                    "quota_id": q.id,
                    "supplier": sup.name if sup else "?",
                    "batch_no": q.batch_no,
                    "end_at": str(q.quota_end_at),
                    "remain": (q.quota_end_at - today).days,
                }
            )
    expiring.sort(key=lambda x: x["remain"])

    # 近 12 个月新增趋势
    months = []
    for i in range(11, -1, -1):
        d = _today().replace(day=1) - timedelta(days=1)
        d = d.replace(day=1)
        m = (d.replace(day=1) - timedelta(days=i * 28))
        m = m.replace(day=1)
        start = datetime(m.year, m.month, 1)
        if m.month == 12:
            end = datetime(m.year + 1, 1, 1)
        else:
            end = datetime(m.year, m.month + 1, 1)
        months.append(
            {
                "month": f"{m.year}-{m.month:02d}",
                "suppliers": db.query(Supplier).filter(Supplier.created_at >= start, Supplier.created_at < end).count(),
                "customers": db.query(Customer).filter(Customer.created_at >= start, Customer.created_at < end).count(),
            }
        )

    # 主体动态(最近 20 条主体相关审计)
    dynamics = (
        db.query(AuditLog)
        .filter(AuditLog.entity_type.in_(["supplier", "customer", "middle", "chain", "order"]))
        .order_by(AuditLog.id.desc())
        .limit(20)
        .all()
    )

    return {
        "supplier_count": supplier_count,
        "customer_count": customer_count,
        "chain_count": chain_count,
        "middle_count": middle_count,
        "verified_count": verified_count,
        "verified_rate": verified_rate,
        "active_orders": active_orders,
        "month_amount": float(month_amount or 0),
        "expiring_quotas": expiring,
        "monthly_trend": months,
        "dynamics": [
            {
                "username": d.username,
                "action": d.action,
                "entity_type": d.entity_type,
                "entity_id": d.entity_id,
                "detail": d.detail,
                "at": str(d.created_at),
            }
            for d in dynamics
        ],
    }
