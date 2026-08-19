"""值班机器人:扫描用户可见范围(含共享),生成撮合建议/陈旧提醒/风险提示,AI 深度解读"""
from datetime import datetime, timedelta, timezone

from ..database import SessionLocal
from ..entities import (
    CapitalVerification,
    Customer,
    DutyReport,
    Order,
    Publication,
    Supplier,
    SupplierQuota,
)
from ..models import User
from ..services.ai_gateway import ai_enabled, _call
from ..services.matching import available_quantity, hard_filters, score_supplier
from ..services.visibility import visible_owner_ids

STALE_DAYS = 3


def _today():
    return datetime.now(timezone.utc).date()


def _demand_of_customer(db, c: Customer) -> dict:
    pid = c.intent_products[0].get("product_line_id") if c.intent_products else None
    try:
        qty = int(float(c.intent_quantity or 0))
    except (TypeError, ValueError):
        qty = 0
    return {
        "product_line_id": pid,
        "quantity": qty,
        "intent_modes": c.intent_modes or [],
        "goods_preference": c.goods_preference or "",
        "price_min": None,
        "price_max": None,
        "verified": (
            db.query(CapitalVerification.id)
            .filter(CapitalVerification.customer_id == c.id, CapitalVerification.review_status == "approved")
            .first()
            is not None
        ),
    }


def scan_for_user(user: User) -> dict:
    db = SessionLocal()
    try:
        s_owners, _ = visible_owner_ids(db, user, "supplier")
        c_owners, _ = visible_owner_ids(db, user, "customer")

        suppliers = db.query(Supplier).filter(Supplier.owner_id.in_(s_owners)).all() if user.role != "admin" else db.query(Supplier).all()
        customers = db.query(Customer).filter(Customer.owner_id.in_(c_owners)).all() if user.role != "admin" else db.query(Customer).all()
        pubs = (
            db.query(Publication)
            .filter(Publication.status == "active", Publication.type == "demand")
            .all()
            if user.role == "admin"
            else db.query(Publication)
            .filter(
                Publication.status == "active",
                Publication.type == "demand",
                (Publication.visibility == "public") | (Publication.user_id == user.id),
            )
            .all()
        )

        matches: list[dict] = []
        for pub in pubs:
            try:
                qty = int(float(pub.quantity or 0))
            except (TypeError, ValueError):
                qty = 0
            demand = {
                "product_line_id": pub.product_line_id,
                "quantity": qty,
                "intent_modes": pub.intent_modes or [],
                "goods_preference": pub.goods_preference or "",
                "price_min": float(pub.price_min) if pub.price_min else None,
                "price_max": float(pub.price_max) if pub.price_max else None,
                "verified": False,
            }
            ranked = []
            for s in suppliers:
                out, fail = score_supplier(db, user.id, s, demand)
                if fail:
                    continue
                ranked.append((out["score"], s))
            ranked.sort(key=lambda x: -x[0])
            matches.append(
                {
                    "demand": pub.title,
                    "publication_id": pub.id,
                    "top": [
                        {"name": s.name, "score": sc, "avail": available_quantity(db, s.id, pub.product_line_id)}
                        for sc, s in ranked[:3]
                    ],
                }
            )

        # 客户意向匹配(有意向数量且近期有更新)
        for c in customers:
            if not (c.intent_quantity or c.intent_products):
                continue
            demand = _demand_of_customer(db, c)
            if demand["quantity"] <= 0:
                continue
            ranked = []
            for s in suppliers:
                out, fail = score_supplier(db, user.id, s, demand)
                if fail:
                    continue
                ranked.append((out["score"], s))
            ranked.sort(key=lambda x: -x[0])
            if ranked:
                matches.append(
                    {
                        "demand": f"客户 {c.name}(意向 {c.intent_quantity})",
                        "customer_id": c.id,
                        "top": [
                            {"name": s.name, "score": sc, "avail": available_quantity(db, s.id, demand["product_line_id"])}
                            for sc, s in ranked[:3]
                        ],
                    }
                )

        today = _today()
        stale: list[dict] = []
        for pub in pubs:
            if (today - pub.updated_at.date()).days > STALE_DAYS:
                stale.append({"type": "需求", "name": pub.title, "days": (today - pub.updated_at.date()).days})
        for s in suppliers:
            if (today - s.updated_at.date()).days > STALE_DAYS:
                stale.append({"type": "供货方", "name": s.name, "days": (today - s.updated_at.date()).days})
        stale.sort(key=lambda x: -x["days"])

        risks: list[dict] = []
        for q in db.query(SupplierQuota).filter(SupplierQuota.status == "available").all():
            if q.quota_end_at and today <= q.quota_end_at <= today + timedelta(days=7):
                sup = db.get(Supplier, q.supplier_id)
                risks.append({"type": "配额到期", "detail": f"{sup.name if sup else '?'} 配额 {q.quota_end_at} 到期(剩 {(q.quota_end_at - today).days} 天)"})
        for v in db.query(CapitalVerification).filter(CapitalVerification.review_status == "approved").all():
            if v.valid_until and today <= v.valid_until <= today + timedelta(days=7):
                cust = db.get(Customer, v.customer_id)
                risks.append({"type": "验资到期", "detail": f"{cust.name if cust else '?'} 验资 {v.valid_until} 到期"})
        for o in db.query(Order).filter(Order.status.in_(["breach", "breach_processing"])).all():
            risks.append({"type": "违约订单", "detail": f"订单 {o.order_no} 处于违约状态"})

        return {
            "matches": matches,
            "stale": stale[:20],
            "risks": risks[:10],
        }
    finally:
        db.close()


def _ai_brief(user_name: str, data: dict) -> str:
    if not ai_enabled():
        return ""
    prompt = (
        "你是供应链值班机器人。根据以下结构化数据,用 200 字以内生成一段中文值班简报:"
        "①撮合建议(需求与供货方匹配亮点)②风险与到期提醒 ③陈旧信息提醒。直接输出正文。\n\n"
        f"用户:{user_name}\n数据:{data}"
    )
    try:
        import json

        return (_call([{"text": prompt}]) or "")[:2000]
    except Exception:
        return ""


def run_duty_for_user(user: User) -> DutyReport:
    data = scan_for_user(user)
    ai_text = _ai_brief(user.display_name or user.username, {
        "matches": data["matches"][:5],
        "stale": data["stale"][:10],
        "risks": data["risks"],
    })
    db = SessionLocal()
    try:
        report = DutyReport(user_id=user.id, content=data, ai_text=ai_text)
        db.add(report)
        db.commit()
        db.refresh(report)
        return report
    finally:
        db.close()


def run_duty_all() -> int:
    from ..models import AuditLog

    db = SessionLocal()
    try:
        users = db.query(User).filter(User.status == "active").all()
    finally:
        db.close()
    count = 0
    for u in users:
        try:
            report = run_duty_for_user(u)
            db = SessionLocal()
            try:
                db.add(
                    AuditLog(
                        user_id=u.id,
                        username=u.username,
                        action="duty_scan",
                        entity_type="duty_report",
                        entity_id=str(report.id),
                        detail=f"值班机器人自动扫描:撮合 {len((report.content or {}).get('matches', []))} 条/陈旧 {(len((report.content or {}).get('stale', [])))} 条/风险 {(len((report.content or {}).get('risks', [])))} 条",
                    )
                )
                db.commit()
            finally:
                db.close()
            count += 1
        except Exception:
            continue
    return count
