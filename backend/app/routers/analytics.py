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
    ProductLine,
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

    # ---- 深挖指标 ----
    # 在途资金敞口(付款中订单金额)
    funding_in_progress = float(
        db.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.status.in_(["sourcing", "sourced", "paying", "paid", "arrived", "delivered"]))
        .scalar()
        or 0
    )
    breach_count = db.query(Order).filter(Order.status.in_(["breach", "breach_processing"])).count()

    # 付款方式分布(数量+金额)
    pm_rows = db.query(Order.payment_mode, func.count(Order.id), func.coalesce(func.sum(Order.total_amount), 0)).group_by(Order.payment_mode).all()
    payment_mode_dist = [{"mode": m or "未标注", "count": c, "amount": float(a or 0)} for m, c, a in pm_rows]

    # 货源结构:现货/准现货/期货
    goods_rows = db.query(Supplier.goods_type, func.count(Supplier.id)).group_by(Supplier.goods_type).all()
    goods_structure = [{"type": g or "未标注", "count": c} for g, c in goods_rows]

    # 配额:按产品线/按链路方/时效分布(可见范围)
    quota_cache_all = {}
    for q in db.query(SupplierQuota).filter(SupplierQuota.status.in_(["available", "locked"])).all():
        if q.quota_end_at and q.quota_end_at < today:
            continue
        quota_cache_all[(q.supplier_id, q.product_line_id)] = quota_cache_all.get((q.supplier_id, q.product_line_id), 0) + max(0, q.quantity - q.used_quantity)
    sup_owner = {s.id: s for s in suppliers_q.all()}
    quota_by_line: dict = {}
    quota_by_chain: dict = {}
    for (sid, pid), amt in quota_cache_all.items():
        s = sup_owner.get(sid)
        if s is None:
            continue
        pl_name = db.get(ProductLine, pid).name if pid else "未指定"
        quota_by_line[pl_name] = quota_by_line.get(pl_name, 0) + amt
        if s.chain_id:
            ch = db.get(OverseasChain, s.chain_id)
            cname = ch.name if ch else f"链路#{s.chain_id}"
        else:
            cname = "未标注链路"
        quota_by_chain[cname] = quota_by_chain.get(cname, 0) + amt

    aging = {"已过期": 0, "7天内": 0, "7-30天": 0, "30天以上": 0}
    for q in db.query(SupplierQuota).all():
        if q.quota_end_at is None:
            aging["30天以上"] += 1
        elif q.quota_end_at < today:
            aging["已过期"] += 1
        elif q.quota_end_at <= today + timedelta(days=7):
            aging["7天内"] += 1
        elif q.quota_end_at <= today + timedelta(days=30):
            aging["7-30天"] += 1
        else:
            aging["30天以上"] += 1
    quota_aging = [{"bucket": k, "count": v} for k, v in aging.items()]

    # 需求覆盖率:客户意向数量合计 vs 可见可用配额合计
    intent_qty = 0
    for c in customers_q.all():
        try:
            intent_qty += int(float(c.intent_quantity or 0))
        except (TypeError, ValueError):
            pass
    available_qty = sum(quota_cache_all.values())
    demand_coverage = {
        "intent_qty": intent_qty,
        "available_qty": available_qty,
        "rate": round(available_qty / intent_qty * 100) if intent_qty else None,
    }

    # 验资状态分布
    v_pending = (
        db.query(CapitalVerification.customer_id)
        .filter(CapitalVerification.review_status == "pending")
        .distinct()
        .count()
    )
    verification_dist = {"verified": verified_count, "unverified": customer_count - verified_count, "pending": v_pending}

    # 客户价值分级
    grade_rows = db.query(Customer.value_grade, func.count(Customer.id)).filter(Customer.value_grade != "").group_by(Customer.value_grade).all()
    value_grade_dist = [{"grade": g, "count": c} for g, c in grade_rows]

    # 供货方履约率分布
    f_high = f_low = f_none = 0
    for s in suppliers_q.all():
        if not s.fulfillment_rate:
            f_none += 1
        else:
            try:
                if float(str(s.fulfillment_rate).replace("%", "")) >= 95:
                    f_high += 1
                else:
                    f_low += 1
            except ValueError:
                f_none += 1
    fulfillment_dist = [{"bucket": "≥95%", "count": f_high}, {"bucket": "<95%", "count": f_low}, {"bucket": "未记录", "count": f_none}]

    # 中间层资金指标汇总(可见交易方案)
    middle_held_total = 0.0
    middle_upfront_total = 0.0
    try:
        from ..entities import DealFlow, DealNode, DealPlan
        from ..services.deal_calc import compute as deal_compute
        from ..services.visibility import apply_visibility as _av

        plans = _av(db.query(DealPlan), DealPlan, db, user, "supplier").limit(50).all()
        for plan in plans:
            nodes = db.query(DealNode).filter(DealNode.plan_id == plan.id).all()
            flows = db.query(DealFlow).filter(DealFlow.plan_id == plan.id).all()
            c = deal_compute(plan, nodes, flows)
            for mm in c.get("middle_metrics", []):
                middle_held_total += mm.get("held_peak", 0) or 0
                middle_upfront_total += (mm.get("upfront_amount", 0) or 0) + (mm.get("upfront_fee", 0) or 0)
    except Exception:
        pass

    # 近12月成交金额趋势
    amount_trend = []
    for i in range(11, -1, -1):
        base = today.replace(day=1)
        y, m0 = divmod(base.month - 1 - i, 12)
        yy = base.year + y
        mm0 = m0 + 1
        start = datetime(yy, mm0, 1)
        if mm0 == 12:
            end = datetime(yy + 1, 1, 1)
        else:
            end = datetime(yy, mm0 + 1, 1)
        amt = float(
            db.query(func.coalesce(func.sum(Order.total_amount), 0))
            .filter(Order.created_at >= start, Order.created_at < end)
            .scalar()
            or 0
        )
        amount_trend.append({"month": f"{yy}-{mm0:02d}", "amount": round(amt, 2)})

    return {
        "supplier_count": supplier_count,
        "customer_count": customer_count,
        "chain_count": chain_count,
        "middle_count": middle_count,
        "verified_count": verified_count,
        "verified_rate": verified_rate,
        "active_orders": active_orders,
        "month_amount": float(month_amount or 0),
        "funding_in_progress": round(funding_in_progress, 2),
        "breach_count": breach_count,
        "middle_held_total": round(middle_held_total, 2),
        "middle_upfront_total": round(middle_upfront_total, 2),
        "demand_coverage": demand_coverage,
        "payment_mode_dist": payment_mode_dist,
        "goods_structure": goods_structure,
        "quota_by_line": [{"name": k, "available": v} for k, v in sorted(quota_by_line.items(), key=lambda x: -x[1])],
        "quota_by_chain": [{"name": k, "available": v} for k, v in sorted(quota_by_chain.items(), key=lambda x: -x[1])][:8],
        "quota_aging": quota_aging,
        "verification_dist": verification_dist,
        "value_grade_dist": value_grade_dist,
        "fulfillment_dist": fulfillment_dist,
        "expiring_quotas": expiring,
        "monthly_trend": months,
        "amount_trend": amount_trend,
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
