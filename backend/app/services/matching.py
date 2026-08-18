"""匹配引擎:硬过滤 → 加权评分 → 归属裁剪。

权重(方案 5.2):
- 用户自设优先级 30%(最高)
- 最近维护/更新时间 20%
- 价格吻合度 + 现货/期货偏好 + 起订量 25%
- 历史履约率 / 客户验资状态与画像匹配 25%
"""
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from ..entities import (
    CapitalVerification,
    Supplier,
    SupplierQuota,
    UserPriority,
)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _parse_rate(s: str) -> float | None:
    s = (s or "").strip().replace("%", "")
    try:
        v = float(s)
        return max(0.0, min(100.0, v))
    except ValueError:
        return None


def available_quantity(db: Session, supplier_id: int, product_line_id: int | None) -> int:
    q = db.query(SupplierQuota).filter(SupplierQuota.supplier_id == supplier_id)
    if product_line_id is not None:
        q = q.filter(SupplierQuota.product_line_id == product_line_id)
    today = _today()
    total = 0
    for quota in q.all():
        if quota.status not in ("available", "locked"):
            continue
        if quota.quota_end_at and quota.quota_end_at < today:
            continue
        total += max(0, quota.quantity - quota.used_quantity)
    return total


def hard_filters(db: Session, supplier: Supplier, demand: dict) -> str | None:
    """返回不通过的原因,通过返回 None。demand: product_line_id/quantity/intent_modes"""
    if supplier.coop_status in ("暂停", "终止"):
        return "合作状态为" + supplier.coop_status
    quantity = demand.get("quantity") or 0
    avail = available_quantity(db, supplier.id, demand.get("product_line_id"))
    if avail <= 0:
        return "无有效配额"
    if quantity > 0 and avail < quantity:
        return f"配额不足(可用 {avail})"
    modes = demand.get("intent_modes") or []
    if modes and supplier.procurement_modes:
        if not set(modes) & set(supplier.procurement_modes):
            return "采购方式不兼容"
    return None


def _priority_score(db: Session, user_id: int, supplier_id: int) -> float:
    row = (
        db.query(UserPriority)
        .filter(
            UserPriority.user_id == user_id,
            UserPriority.entity_type == "supplier",
            UserPriority.entity_id == supplier_id,
        )
        .first()
    )
    if row is None:
        return 50.0
    return (row.priority - 1) / 8 * 100


def _freshness_score(updated_at: datetime) -> float:
    if updated_at is None:
        return 40.0
    days = (_today() - updated_at.date()).days
    if days <= 1:
        return 100.0
    if days <= 3:
        return 90.0
    if days <= 7:
        return 80.0
    if days <= 30:
        return 60.0
    return 40.0


def _preference_score(supplier: Supplier, demand: dict) -> float:
    pref = demand.get("goods_preference") or ""
    if pref == "现货":
        base = {"现货": 100.0, "准现货": 85.0, "期货": 55.0}.get(supplier.goods_type, 70.0)
    elif pref == "期货":
        base = 100.0 if supplier.goods_type == "期货" else 70.0
    else:
        base = 85.0 if supplier.goods_type == "现货" else 75.0
    return base


def _price_score(supplier: Supplier, demand: dict) -> float:
    if supplier.price is None:
        return 60.0
    lo, hi = demand.get("price_min"), demand.get("price_max")
    if lo is None and hi is None:
        return 80.0
    p = float(supplier.price)
    if lo is not None and hi is not None and lo <= p <= hi:
        return 100.0
    if lo is not None and hi is not None:
        span = max(hi - lo, 1.0)
        if lo - span * 0.1 <= p <= hi + span * 0.1:
            return 75.0
    return 40.0


def _credit_score(db: Session, supplier: Supplier, demand: dict) -> float:
    score = 70.0
    rate = _parse_rate(supplier.fulfillment_rate)
    if rate is not None:
        score = rate
    if supplier.credit_rating:
        score += {"A": 10, "B": 5, "C": -10}.get(supplier.credit_rating.upper(), 0)
    score -= min(30, (supplier.breach_count or 0) * 10)
    if demand.get("verified"):
        score += 10
    return max(0.0, min(100.0, score))


def score_supplier(db: Session, user_id: int, supplier: Supplier, demand: dict):
    fail = hard_filters(db, supplier, demand)
    if fail:
        return None, fail
    avail = available_quantity(db, supplier.id, demand.get("product_line_id"))
    p_pri = _priority_score(db, user_id, supplier.id)
    p_fresh = _freshness_score(supplier.updated_at)
    p_pref = _preference_score(supplier, demand)
    p_price = _price_score(supplier, demand)
    p_credit = _credit_score(db, supplier, demand)
    total = round(p_pri * 0.30 + p_fresh * 0.20 + (p_pref + p_price) / 2 * 0.25 + p_credit * 0.25)

    reasons = []
    row = db.query(UserPriority).filter(
        UserPriority.user_id == user_id,
        UserPriority.entity_type == "supplier",
        UserPriority.entity_id == supplier.id,
    ).first()
    if row:
        reasons.append(f"你设置了优先级 {row.priority}")
    days = (_today() - supplier.updated_at.date()).days if supplier.updated_at else 999
    reasons.append(f"最近更新于 {days} 天前")
    if supplier.price is not None:
        reasons.append(f"报价 {float(supplier.price):,.0f} {supplier.currency}")
    if supplier.goods_type:
        reasons.append(f"{supplier.goods_type}")
    if supplier.fulfillment_rate:
        reasons.append(f"历史履约率 {supplier.fulfillment_rate}")
    if demand.get("verified") and supplier.fulfillment_rate:
        reasons.append("客户已验资,履约加成")
    reasons.append(f"可用配额 {avail}")

    breakdown = {
        "priority": round(p_pri, 1),
        "freshness": round(p_fresh, 1),
        "preference": round(p_pref, 1),
        "price": round(p_price, 1),
        "credit": round(p_credit, 1),
    }
    return {"score": total, "breakdown": breakdown, "reasons": reasons, "available_quantity": avail}, None


def demand_verified(db: Session, customer_id: int | None) -> bool:
    if customer_id is None:
        return False
    return (
        db.query(CapitalVerification.id)
        .filter(
            CapitalVerification.customer_id == customer_id,
            CapitalVerification.review_status == "approved",
        )
        .first()
        is not None
    )
