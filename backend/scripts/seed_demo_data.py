#!/usr/bin/env python3
"""演示数据种子:生成带【演示】前缀的模拟业务数据,让分析中台图表有内容可看。

可重复执行:先清掉上一批【演示】数据再重灌。
用法: cd backend && .venv/bin/python scripts/seed_demo_data.py
"""
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.entities import (
    CapitalVerification,
    Customer,
    DealFlow,
    DealNode,
    DealPlan,
    MiddleLayer,
    Order,
    OrderTrack,
    OverseasChain,
    Publication,
    Supplier,
    SupplierQuota,
)
from app.models import User

P = "【演示】"
random.seed(42)


def purge_test_data(db):
    """清理【测】前缀的测试数据(保留【演示】)"""
    from app.entities import Breach, Communication, OrderDocument

    t_sups = [s.id for s in db.query(Supplier).filter(Supplier.name.like("【测】%")).all()]
    t_cus = [c.id for c in db.query(Customer).filter(Customer.name.like("【测】%")).all()]
    t_plans = [p.id for p in db.query(DealPlan).filter(DealPlan.title.like("【测】%")).all()]
    t_orders = [o.id for o in db.query(Order).filter(Order.order_no.like("【测】%")).all()]
    for sid in t_sups:
        db.query(SupplierQuota).filter(SupplierQuota.supplier_id == sid).delete()
    for cid in t_cus:
        db.query(CapitalVerification).filter(CapitalVerification.customer_id == cid).delete()
    for pid in t_plans:
        db.query(DealNode).filter(DealNode.plan_id == pid).delete()
        db.query(DealFlow).filter(DealFlow.plan_id == pid).delete()
    for oid in t_orders:
        db.query(OrderTrack).filter(OrderTrack.order_id == oid).delete()
        db.query(Breach).filter(Breach.order_id == oid).delete()
        db.query(OrderDocument).filter(OrderDocument.order_id == oid).delete()
    db.query(Order).filter(Order.order_no.like("【测】%")).delete()
    db.query(DealPlan).filter(DealPlan.title.like("【测】%")).delete()
    db.query(Supplier).filter(Supplier.name.like("【测】%")).delete()
    db.query(Customer).filter(Customer.name.like("【测】%")).delete()
    db.query(MiddleLayer).filter(MiddleLayer.name.like("【测】%")).delete()
    db.query(Publication).filter(Publication.title.like("【测】%")).delete()
    db.query(Communication).filter(Communication.entity_id.notin_(db.query(Supplier.id))).delete(synchronize_session=False)
    db.commit()
    print("【测】测试数据已清理")


def cleanup(db):
    demo_sups = [s.id for s in db.query(Supplier).filter(Supplier.name.like(f"{P}%")).all()]
    demo_cus = [c.id for c in db.query(Customer).filter(Customer.name.like(f"{P}%")).all()]
    demo_plans = [p.id for p in db.query(DealPlan).filter(DealPlan.title.like(f"{P}%")).all()]
    demo_orders = [o.id for o in db.query(Order).filter(Order.order_no.like(f"{P}%")).all()]
    for sid in demo_sups:
        db.query(SupplierQuota).filter(SupplierQuota.supplier_id == sid).delete()
    for cid in demo_cus:
        db.query(CapitalVerification).filter(CapitalVerification.customer_id == cid).delete()
    for pid in demo_plans:
        db.query(DealNode).filter(DealNode.plan_id == pid).delete()
        db.query(DealFlow).filter(DealFlow.plan_id == pid).delete()
    for oid in demo_orders:
        db.query(OrderTrack).filter(OrderTrack.order_id == oid).delete()
    db.query(Order).filter(Order.order_no.like(f"{P}%")).delete()
    db.query(DealPlan).filter(DealPlan.title.like(f"{P}%")).delete()
    db.query(Supplier).filter(Supplier.name.like(f"{P}%")).delete()
    db.query(Customer).filter(Customer.name.like(f"{P}%")).delete()
    db.query(MiddleLayer).filter(MiddleLayer.name.like(f"{P}%")).delete()
    db.query(OverseasChain).filter(OverseasChain.name.like(f"{P}%")).delete()
    db.query(Publication).filter(Publication.title.like(f"{P}%")).delete()
    db.commit()
    print("旧演示数据已清理")


def seed(db):
    admin = db.query(User).filter(User.role == "admin").first()
    owner = admin.id if admin else 1
    today = date.today()

    def dt(months_ago: int, day: int = 15) -> datetime:
        base = today.replace(day=1)
        y, m = divmod(base.month - 1 - months_ago, 12)
        yy = base.year + y
        mm = m + 1
        d = min(day, 28)
        return datetime(yy, mm, d, 10, 30)

    # ---- 链路方 ----
    chains = []
    for name, region in [(f"{P}链路A-新加坡", "新加坡"), (f"{P}链路B-香港", "香港"), (f"{P}链路C-中东", "中东")]:
        c = OverseasChain(name=name, region=region, contact_person="演示联系人", owner_id=owner, last_editor_id=owner)
        db.add(c)
        db.flush()
        chains.append(c)

    # ---- 供货方(10 家,覆盖各维度,创建时间分散在 12 个月内) ----
    sup_specs = [
        ("芯联国际", "现货", "100%", "A", 0, 1, 142, 1000),   # (简称,类型,履约率,评级,创建月,链,价,配额)
        ("速达供应链", "准现货", "95%", "B", 1, 1, 138, 600),
        ("远洋科技", "期货", "", "", 2, 1, 135, 400),
        ("中港贸易", "现货", "85%", "B", 3, 2, 140, 500),
        ("华芯电子", "现货", "", "C", 4, 2, 143, 300),
        ("云算力贸易", "准现货", "90%", "B", 6, 2, 139, 350),
        ("跨境通道", "期货", "92%", "B", 8, 3, 137, 450),
        ("算力直供", "现货", "100%", "A", 10, 3, 141, 800),
        ("备用货源", "准现货", "70%", "C", 11, 1, 136, 200),
        ("暂停合作方", "现货", "", "", 9, 3, 145, 100),
    ]
    suppliers = []
    for i, (name, gtype, rate, grade, months_ago, chain_idx, price, qty) in enumerate(sup_specs):
        s = Supplier(
            name=f"{P}{name}", short_name=name, goods_type=gtype, price=price, currency="CNY",
            fulfillment_rate=rate, credit_rating=grade, coop_status="终止" if name == "暂停合作方" else "合作中",
            procurement_modes=["预付款"] if i % 3 else ["预付款", "信用证-跨境"],
            chain_id=chains[chain_idx - 1].id, chain_role="一手" if i % 2 == 0 else "二手",
            owner_id=owner, last_editor_id=owner,
            created_at=dt(months_ago), updated_at=dt(months_ago),
        )
        db.add(s)
        db.flush()
        suppliers.append(s)
        # 配额:各时效档位
        end_days = [-5, 3, 6, 15, 40, 90][i % 6]
        db.add(SupplierQuota(
            supplier_id=s.id, batch_no=f"QB-DEMO-{i:02d}", quantity=qty, used_quantity=int(qty * random.uniform(0.1, 0.6)),
            quota_start_at=today - timedelta(days=60), quota_end_at=today + timedelta(days=end_days),
            status="available", created_by=owner,
        ))

    # ---- 客户(8 家,验资/分级/意向) ----
    cus_specs = [
        ("国资算力平台", "A", "approved", 200, 1), ("云服务商甲", "B", "approved", 100, 2),
        ("金融机构乙", "A", "approved", 150, 4), ("互联网集团", "B", "unverified", 80, 5),
        ("智算中心", "A", "approved", 120, 7), ("贸易商丙", "C", "unverified", 50, 8),
        ("初创AI公司", "B", "pending", 30, 10), ("行业客户丁", "A", "approved", 90, 11),
    ]
    customers = []
    for i, (name, grade, vstate, qty, months_ago) in enumerate(cus_specs):
        c = Customer(
            name=f"{P}{name}", industry="算力", value_grade=grade, intent_quantity=str(qty),
            intent_modes=["预付款"] if i % 2 else ["信用证-国内"],
            customer_type="国资平台" if grade == "A" else "民营",
            owner_id=owner, last_editor_id=owner,
            created_at=dt(months_ago), updated_at=dt(months_ago),
        )
        db.add(c)
        db.flush()
        customers.append(c)
        if vstate != "unverified":
            db.add(CapitalVerification(
                customer_id=c.id, verify_type="bank_certificate", file_name="资信证明.pdf",
                material_date=today - timedelta(days=10), valid_until=today + timedelta(days=20),
                amount=str(qty * 100), review_status=vstate,
                ai_status="passed", reviewed_by=owner, reviewed_at=datetime.now() if vstate == "approved" else None,
            ))

    # ---- 中间层 ----
    mid1 = MiddleLayer(name=f"{P}国资供应链通道", entity_nature="国资", layer_no=1, purposes=["代开信用证", "开保函"], fee_rate="1.5%", owner_id=owner, last_editor_id=owner, created_at=dt(3))
    mid2 = MiddleLayer(name=f"{P}民营贸易通道", entity_nature="民营", layer_no=2, purposes=["居间分账"], fee_rate="", owner_id=owner, last_editor_id=owner, created_at=dt(5))
    db.add(mid1)
    db.add(mid2)
    db.flush()

    # ---- 订单(18 单跨 12 个月,金额趋势/付款方式/状态) ----
    modes = ["预付款", "信用证-国内", "信用证-跨境"]
    status_pool = ["done", "done", "done", "arrived", "delivered", "paid", "paying", "sourcing", "breach", "breach_processing"]
    order_specs = []
    for m_ago in range(11, -1, -1):
        n = 1 if m_ago % 3 == 0 else 2
        for k in range(n):
            order_specs.append((m_ago, k))
    for idx, (m_ago, k) in enumerate(order_specs):
        qty = random.choice([10, 15, 20, 30, 50, 80])
        unit = random.choice([136, 138, 140, 142, 144])
        total = qty * unit
        st = "done" if m_ago < 9 else status_pool[idx % len(status_pool)]
        if st == "breach":
            st = "breach_processing"
        o = Order(
            order_no=f"{P}DD-{2601 + idx}", quantity=qty, unit_price=unit, total_amount=total,
            currency="CNY", payment_mode=modes[idx % 3],
            supplier_id=suppliers[idx % len(suppliers)].id, customer_id=customers[idx % len(customers)].id,
            status=st, pre_breach_status="paying" if st in ("breach", "breach_processing") else "",
            contract_no=f"HT-DEMO-{idx:03d}", signed_at=dt(m_ago).date(),
            owner_id=owner, last_editor_id=owner, created_at=dt(m_ago), updated_at=dt(m_ago),
        )
        db.add(o)
        db.flush()
        db.add(OrderTrack(order_id=o.id, category="货源", title="配额锁定", content="演示:货源确认", created_by=owner, created_by_name="演示", created_at=dt(m_ago)))
        if st in ("paid", "arrived", "delivered", "done"):
            db.add(OrderTrack(order_id=o.id, category="资金", title="货款支付", content="演示:付款完成", created_by=owner, created_by_name="演示", created_at=dt(m_ago)))
        if st in ("breach", "breach_processing"):
            db.add(OrderTrack(order_id=o.id, category="违约", title="交付延期", content="演示:上游延期 10 天", created_by=owner, created_by_name="演示", created_at=dt(m_ago)))
    # 强制两笔近期订单进入违约状态(演示风险指标)
    recent = db.query(Order).filter(Order.order_no.like(f"{P}%")).order_by(Order.id.desc()).limit(3).all()
    for o2 in recent[:2]:
        o2.status = "breach_processing"
        o2.pre_breach_status = "paying"

    # ---- 交易方案(3 个,含截流与代开证) ----
    def mk_plan(title, qty, up, down, wrapped, fee_fixed, upfront, mode="预付款"):
        p = DealPlan(
            title=f"{P}{title}", quantity=qty, upstream_price=up, downstream_price=down,
            wrapped_spread=wrapped, supplier_fee_fixed=fee_fixed, upfront_percent=upfront,
            payment_mode=mode, currency="CNY", owner_id=owner, last_editor_id=owner,
            created_at=dt(1), updated_at=dt(0),
        )
        db.add(p)
        db.flush()
        n_c = DealNode(plan_id=p.id, role="customer", name=f"{P}下游方", seq=1)
        n_m = DealNode(plan_id=p.id, role="middle", name=f"{P}通道方", seq=2, purpose="交易居间")
        n_s = DealNode(plan_id=p.id, role="supplier", name=f"{P}上游方", seq=3)
        db.add_all([n_c, n_m, n_s])
        db.flush()
        flows = [
            (1, "payment", "客户预付 20%", n_c.id, n_m.id, "percent", 20, "downstream_total"),
            (2, "payment", "预付上游 10%", n_m.id, n_s.id, "percent", 10, "upstream_total"),
            (3, "guarantee", "向客户开保函 30%", n_m.id, n_c.id, "percent", 30, "downstream_total"),
            (4, "upfront_fee", "上游居间前置", n_s.id, n_m.id, "percent", 20, "middle_wrapped"),
            (5, "payment", "客户尾款 80%", n_c.id, n_m.id, "percent", 80, "downstream_total"),
            (6, "payment", "付清上游余款", n_m.id, n_s.id, "percent", 90, "upstream_total"),
        ]
        for seq, ft, label, frm, to, at, val, base in flows:
            db.add(DealFlow(plan_id=p.id, seq=seq, flow_type=ft, label=label, from_node_id=frm, to_node_id=to, amount_type=at, percent=val if at == "percent" else None, amount=None if at == "percent" else val, base=base))
        return p, n_m

    mk_plan("三方链路-预付款+保函", 20, 136, 142, 3, 30, 20)
    mk_plan("三方链路-现货快单", 30, 135, 140, 2, 25, 25)

    # 代开证方案
    p3 = DealPlan(
        title=f"{P}信用证代开链路", quantity=10, upstream_price=100, downstream_price=105,
        payment_mode="信用证-国内", currency="CNY", owner_id=owner, last_editor_id=owner,
        created_at=dt(0), updated_at=dt(0),
    )
    db.add(p3)
    db.flush()
    db.add_all([
        DealNode(plan_id=p3.id, role="customer", name=f"{P}信用证客户", seq=1),
        DealNode(plan_id=p3.id, role="middle", name=f"{P}代开证主体", seq=2, purpose="代开信用证", fee_percent=1.5, income_fixed=2, deposit_fixed=50),
        DealNode(plan_id=p3.id, role="supplier", name=f"{P}证下供货方", seq=3),
    ])

    # ---- 看板发布 ----
    db.add(Publication(user_id=owner, type="demand", product_line_id=None, title=f"{P}求购B300现货50台", quantity="50", price_min=135, price_max=145, intent_modes=["预付款"], visibility="public", validity_until=today + timedelta(days=14), created_at=dt(0)))
    db.add(Publication(user_id=owner, type="supply", product_line_id=None, title=f"{P}现货300台货源释放", quantity="300", price_min=138, price_max=142, intent_modes=["信用证-跨境"], visibility="public", validity_until=today + timedelta(days=7), created_at=dt(0)))

    db.commit()
    print(f"演示数据已生成:链路 {len(chains)} / 供货方 {len(suppliers)} / 客户 {len(customers)} / 订单 {len(order_specs)} / 交易方案 3 / 看板 2")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        if "--purge-tests" in sys.argv:
            purge_test_data(db)
        cleanup(db)
        seed(db)
    finally:
        db.close()
    print("完成。刷新「分析中台」页面即可看到效果(以管理员登录)。")
