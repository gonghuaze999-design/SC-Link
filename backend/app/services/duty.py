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
from ..services.matching import available_quantity, build_priority_cache, build_quota_cache, hard_filters, score_supplier
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
        # 批量缓存:配额/优先级各一次查询,避免逐条评分时的 N+1
        quota_cache = build_quota_cache(db)
        priority_cache = build_priority_cache(db, user.id)
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
                out, fail = score_supplier(db, user.id, s, demand, quota_cache, priority_cache)
                if fail:
                    continue
                ranked.append((out["score"], s))
            ranked.sort(key=lambda x: -x[0])
            matches.append(
                {
                    "demand": pub.title,
                    "publication_id": pub.id,
                    "top": [
                        {"name": s.name, "score": sc, "avail": available_quantity(db, s.id, pub.product_line_id, quota_cache)}
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
                out, fail = score_supplier(db, user.id, s, demand, quota_cache, priority_cache)
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
                            {"name": s.name, "score": sc, "avail": available_quantity(db, s.id, demand["product_line_id"], quota_cache)}
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
        "你是供应链值班机器人。请根据以下结构化数据撰写一份正式的每日值班简报,"
        "要求:①正式报告行文,措辞专业简洁,总长 200 字以内;"
        "②按「一、撮合建议」「二、风险与到期提醒」「三、陈旧信息提醒」三个板块组织;"
        "③严禁使用任何 Markdown 标记(如 **、#、-、*),数字与金额用中文表述。\n\n"
        f"用户:{user_name}\n数据:{data}"
    )
    try:
        import json

        return (_call([{"text": prompt}]) or "")[:2000]
    except Exception:
        return ""


def _has_recent_updates(db, user: User, since) -> bool:
    """自上次扫描以来是否有供需信息更新"""
    from ..entities import Customer, Publication

    s_owners, _ = visible_owner_ids(db, user, "supplier")
    c_owners, _ = visible_owner_ids(db, user, "customer")
    if user.role == "admin":
        sup_q = db.query(Supplier)
        cus_q = db.query(Customer)
        pub_q = db.query(Publication)
    else:
        sup_q = db.query(Supplier).filter(Supplier.owner_id.in_(s_owners))
        cus_q = db.query(Customer).filter(Customer.owner_id.in_(c_owners))
        pub_q = db.query(Publication).filter((Publication.visibility == "public") | (Publication.user_id == user.id))
    if sup_q.filter(Supplier.updated_at >= since).first():
        return True
    if cus_q.filter(Customer.updated_at >= since).first():
        return True
    if pub_q.filter(Publication.updated_at >= since).first():
        return True
    return False


def _has_active_orders(db, user: User) -> bool:
    orders_q = db.query(Order)
    if user.role != "admin":
        s_owners, _ = visible_owner_ids(db, user, "supplier")
        orders_q = orders_q.filter(Order.owner_id.in_(s_owners))
    return orders_q.filter(~Order.status.in_(["done", "closed"])).first() is not None


def run_duty_for_user(user: User, skip_if_idle: bool = False) -> DutyReport:
    db = SessionLocal()
    try:
        if skip_if_idle:
            last = (
                db.query(DutyReport)
                .filter(DutyReport.user_id == user.id)
                .order_by(DutyReport.id.desc())
                .first()
            )
            since = last.created_at if last else datetime(2000, 1, 1)
            has_update = _has_recent_updates(db, user, since)
            has_orders = _has_active_orders(db, user)
            if not has_update and not has_orders:
                idle_report = DutyReport(
                    user_id=user.id,
                    content={"matches": [], "stale": [], "risks": [], "note": "今日无供需信息更新,亦无在途订单。每日自动扫描已正常执行。"},
                    ai_text="",
                )
                db.add(idle_report)
                db.commit()
                db.refresh(idle_report)
                return idle_report
    finally:
        db.close()

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
            report = run_duty_for_user(u, skip_if_idle=True)
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
