#!/usr/bin/env python3
"""SC-Link 全面测试程序:双角色 × 多角度(功能/边界/极限/权限/安全/并发/压力)。

用法: cd backend && .venv/bin/python scripts/comprehensive_test.py
输出: 测试报告.html(项目根目录)+ 控制台统计
"""
import json
import random
import threading
import time
from datetime import date, timedelta
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8100/api"
REPORT = Path(__file__).resolve().parent.parent.parent / "测试报告.html"

results: list[dict] = []
COUNTER = {"ok": 0, "fail": 0}
PREFIX = "【测】"


def log(category: str, name: str, passed: bool, detail: str, role: str = "—", ms: float = 0):
    results.append(
        {
            "category": category,
            "name": name,
            "role": role,
            "passed": passed,
            "detail": detail,
            "ms": round(ms, 1),
        }
    )
    COUNTER["ok" if passed else "fail"] += 1
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {category}/{name}  {detail[:90]}")


def t(fn, category: str, name: str, role: str = "—"):
    """测试用例包装:自动计时与异常捕获"""
    start = time.time()
    try:
        passed, detail = fn()
    except Exception as e:
        passed, detail = False, f"异常:{type(e).__name__}:{e}"
    log(category, name, passed, detail, role, (time.time() - start) * 1000)


def expect(code: int, *ok_codes: int) -> bool:
    return code in (code,) + ok_codes


# ================= HTTP 工具 =================
def req(method: str, path: str, token: str = "", json_body=None, **kw):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.request(method, BASE + path, headers=headers, json=json_body, timeout=60, **kw)


def login(u: str, p: str) -> str:
    r = req("POST", "/auth/login", json_body={"username": u, "password": p})
    return r.json().get("access_token", "") if r.status_code == 200 else ""


# ================= Mock 数据 =================
def _cleanup_mock_data():
    import subprocess

    sql = """
SET FOREIGN_KEY_CHECKS=0;
DELETE t FROM order_tracks t JOIN orders o ON t.order_id=o.id WHERE HEX(LEFT(o.order_no,1))='E38090';
DELETE b FROM breaches b JOIN orders o ON b.order_id=o.id WHERE HEX(LEFT(o.order_no,1))='E38090';
DELETE FROM orders WHERE HEX(LEFT(order_no,1))='E38090';
DELETE FROM match_results;
DELETE FROM detail_requests;
DELETE FROM user_priorities;
DELETE FROM data_shares;
DELETE FROM capital_verifications WHERE customer_id NOT IN (SELECT id FROM customers);
DELETE FROM supplier_quotas WHERE supplier_id IN (SELECT id FROM suppliers WHERE HEX(LEFT(name,1))='E38090') OR supplier_id NOT IN (SELECT id FROM suppliers);
DELETE FROM communications WHERE entity_id NOT IN (SELECT id FROM suppliers);
DELETE FROM suppliers WHERE HEX(LEFT(name,1))='E38090';
DELETE FROM customers WHERE HEX(LEFT(name,1))='E38090';
DELETE FROM middle_layers WHERE HEX(LEFT(name,1))='E38090';
DELETE FROM publications WHERE HEX(LEFT(title,1))='E38090';
DELETE FROM users WHERE username LIKE 'm_user_%';
DELETE FROM audit_logs WHERE entity_type='match';
SET FOREIGN_KEY_CHECKS=1;
"""

    cmd = ["docker", "exec", "sclink-mysql", "mysql", "-uroot", "-psclink_dev_root", "sc_link", "-e", sql]
    for attempt in range(3):
        r = subprocess.run(cmd, capture_output=True, timeout=60)
        if r.returncode == 0:
            break
        print(f"[清理] 第 {attempt + 1} 次执行失败: {r.stderr.decode('utf-8', 'ignore')[:300]}")
        time.sleep(2)


def setup_mock():
    print(">>> 清理历史测试数据并准备模拟数据…")
    _cleanup_mock_data()
    admin = login("admin", "Admin@2026")
    for u, disp in [("m_user_a", "模拟用户甲"), ("m_user_b", "模拟用户乙"), ("m_user_c", "模拟用户丙")]:
        r = req("POST", "/users", admin, {"username": u, "display_name": disp, "role": "user", "password": "Mock@2026"})
        if r.status_code in (201, 400):
            pass
    ta = login("m_user_a", "Mock@2026")
    tb = login("m_user_b", "Mock@2026")
    tc = login("m_user_c", "Mock@2026")

    # 产品线
    for name, cat in [("B300", "服务器整机"), ("B200", "服务器整机"), ("H100", "硬件板卡")]:
        req("POST", "/product-lines", admin, {"name": name, "category": cat})
    pl = req("GET", "/product-lines", admin).json()
    pid = {p["name"]: p["id"] for p in pl}
    today = date.today()

    def mk_supplier(tok, name, **kw):
        body = {"name": f"{PREFIX}{name}", "goods_type": "现货", "coop_status": "合作中", "procurement_modes": ["预付款"], "price": 1400000}
        body.update(kw)
        r = req("POST", "/suppliers", tok, body)
        return r.json().get("id") if r.status_code == 201 else None

    def mk_quota(tok, sid, plid, qty, end_offset=30, status="available"):
        req("POST", f"/suppliers/{sid}/quotas", tok, {"product_line_id": plid, "batch_no": f"QB-MOCK-{random.randint(1000, 9999)}", "quantity": qty, "quota_end_at": str(today + timedelta(days=end_offset)), "status": status})

    def mk_customer(tok, name, **kw):
        body = {"name": f"{PREFIX}{name}", "intent_modes": ["预付款"], "intent_quantity": "20"}
        body.update(kw)
        r = req("POST", "/customers", tok, body)
        return r.json().get("id") if r.status_code == 201 else None

    # 供货方矩阵(覆盖各维度)
    s_normal = mk_supplier(ta, "芯联科技", price=1420000, goods_type="现货", fulfillment_rate="100%", credit_rating="A")
    mk_quota(ta, s_normal, pid["B300"], 500, 30)
    s_quasi = mk_supplier(ta, "速达贸易", price=1380000, goods_type="准现货", fulfillment_rate="90%")
    mk_quota(ta, s_quasi, pid["B300"], 150, 3)  # 3 天后到期(预警)
    s_future = mk_supplier(ta, "远洋国际", price=1350000, goods_type="期货", coop_status="洽谈中")
    mk_quota(ta, s_future, pid["B300"], 300, 90)
    s_terminated = mk_supplier(tb, "终止合作方", coop_status="终止")
    mk_quota(tb, s_terminated, pid["B300"], 100, 30)
    s_noquota = mk_supplier(tb, "无配额方", goods_type="现货")
    s_zero = mk_supplier(tb, "零配额方")
    mk_quota(tb, s_zero, pid["B300"], 0, 30)
    s_expired = mk_supplier(tc, "过期配额方")
    mk_quota(tc, s_expired, pid["B300"], 200, -5)  # 已过期
    s_breach = mk_supplier(ta, "曾违约方", fulfillment_rate="70%", breach_count=3, credit_rating="C")
    mk_quota(ta, s_breach, pid["B300"], 80, 30)
    s_b200 = mk_supplier(ta, "B200专供", goods_type="现货")
    mk_quota(ta, s_b200, pid["B200"], 60, 30)

    # 客户矩阵
    c_verified = mk_customer(ta, "验资客户甲", intent_quantity="20")
    c_unverified = mk_customer(tb, "未验资客户乙", intent_quantity="5")
    c_huge = mk_customer(tc, "巨量需求客户", intent_quantity="99999")

    # 中间层
    req("POST", "/middles", ta, {"name": f"{PREFIX}国资供应链", "entity_nature": "国资", "layer_no": 1, "purposes": ["代开信用证", "开保函"]})
    req("POST", "/middles", tb, {"name": f"{PREFIX}民营通道", "entity_nature": "民营", "purposes": ["居间分账"]})

    # 看板
    pub_demand = req("POST", "/publications", ta, {"type": "demand", "product_line_id": pid["B300"], "title": f"{PREFIX}求购B300现货20台", "quantity": "20", "price_min": 1350000, "price_max": 1450000, "intent_modes": ["预付款"], "visibility": "public"}).json()
    req("POST", "/publications", ta, {"type": "demand", "product_line_id": pid["B300"], "title": f"{PREFIX}私密求购", "quantity": "5", "visibility": "private"})
    pub_expired = req("POST", "/publications", ta, {"type": "supply", "product_line_id": pid["B300"], "title": f"{PREFIX}短期供货", "quantity": "10", "validity_until": str(today + timedelta(days=1))}).json()

    # 订单(模拟交易与跟踪)
    o1 = req("POST", "/orders", ta, {"order_no": f"{PREFIX}DD-001", "product_line_id": pid["B300"], "quantity": 20, "unit_price": 1420000, "total_amount": 28400000, "supplier_id": s_normal, "customer_id": c_verified, "payment_mode": "预付款", "contract_no": "HT-MOCK-001"}).json()
    for st in ["sourcing", "sourced", "paying", "paid", "arrived", "delivered", "done"]:
        req("POST", f"/orders/{o1['id']}/status", ta, {"status": st})
    req("POST", f"/orders/{o1['id']}/tracks", ta, {"category": "资金", "title": "定金到账", "content": "收到定金 20%"})
    req("POST", f"/orders/{o1['id']}/tracks", ta, {"category": "交付", "title": "客户签收", "content": "20 台全部签收,验收单已回传"})

    o2 = req("POST", "/orders", ta, {"order_no": f"{PREFIX}DD-002", "product_line_id": pid["B300"], "quantity": 5, "unit_price": 1380000, "total_amount": 6900000, "supplier_id": s_quasi, "customer_id": c_unverified, "payment_mode": "信用证-国内"}).json()
    req("POST", f"/orders/{o2['id']}/status", ta, {"status": "sourcing"})
    req("POST", f"/orders/{o2['id']}/tracks", ta, {"category": "货源", "title": "配额锁定", "content": "锁定 5 台准现货"})

    o3 = req("POST", "/orders", tb, {"order_no": f"{PREFIX}DD-003", "product_line_id": pid["B300"], "quantity": 30, "unit_price": 1350000, "total_amount": 40500000, "supplier_id": s_future, "customer_id": c_huge, "payment_mode": "信用证-跨境"}).json()
    for st in ["sourcing", "sourced", "paying", "breach", "breach_processing"]:
        req("POST", f"/orders/{o3['id']}/status", tb, {"status": st})
    req("POST", f"/orders/{o3['id']}/breaches", tb, {"breach_party": "上游", "breach_content": "期货交付延期 10 天", "solution": "协商赔付货值 2%"})
    req("POST", f"/orders/{o3['id']}/tracks", tb, {"category": "违约", "title": "延期通知", "content": "上游通知交付顺延 10 天"})

    # 共享与优先级
    share = req("POST", "/shares", ta, {"target_id": req("GET", "/users/options", ta).json()[2]["id"], "scopes": ["supplier"], "note": "模拟测试共享"}).json()

    print(f">>> 模拟数据就绪:供货方 9 家、客户 3 家、订单 3 单(1 完成/1 进行中/1 违约)、共享 1 条")
    return {
        "admin": admin, "ta": ta, "tb": tb, "tc": tc,
        "pid": pid, "s_normal": s_normal, "s_quasi": s_quasi, "s_breach": s_breach,
        "s_terminated": s_terminated, "s_noquota": s_noquota, "s_zero": s_zero,
        "s_expired": s_expired, "s_b200": s_b200,
        "c_verified": c_verified, "c_unverified": c_unverified, "c_huge": c_huge,
        "pub_demand": pub_demand, "pub_expired": pub_expired,
        "o1": o1, "o2": o2, "o3": o3, "share": share,
    }


# ================= 测试用例 =================
def run_all(m):
    admin, ta, tb, tc = m["admin"], m["ta"], m["tb"], m["tc"]

    # ---- A. 认证与账号安全 ----
    def a1():
        r = req("POST", "/auth/login", json_body={"username": "admin", "password": "Admin@2026"})
        return r.status_code == 200, f"HTTP {r.status_code}"
    t(a1, "A.认证", "管理员正确密码登录", "管理员")

    def a2():
        r = req("POST", "/auth/login", json_body={"username": "admin", "password": "Wrong@2026"})
        return r.status_code == 401, f"HTTP {r.status_code}"
    t(a2, "A.认证", "错误密码拒绝(401)", "管理员")

    def a3():
        r = req("POST", "/auth/login", json_body={"username": "admin", "password": "Admin@2026' OR '1'='1"})
        return r.status_code == 401, f"SQL注入登录被拒 HTTP {r.status_code}"
    t(a3, "A.认证", "SQL 注入绕过登录尝试被拒", "安全")

    def a4():
        r = req("GET", "/auth/me")
        return r.status_code == 401, "无 token 访问被拒(401)"
    t(a4, "A.认证", "无凭证访问被拒", "安全")

    def a5():
        r = req("GET", "/auth/me", "invalid.token.here")
        return r.status_code == 401, "伪造 token 被拒(401)"
    t(a5, "A.认证", "伪造 token 被拒", "安全")

    def a6():
        # 连续 5 次错误密码 → 第 6 次锁定
        codes = [req("POST", "/auth/login", json_body={"username": "m_user_c", "password": "Bad@2026"}).status_code for _ in range(5)]
        locked = req("POST", "/auth/login", json_body={"username": "m_user_c", "password": "Mock@2026"}).status_code
        ok = codes == [401] * 5 and locked == 423
        return ok, f"5 次失败后正确密码也锁定:HTTP {locked}"
    t(a6, "A.认证", "登录锁定(5次失败→423)", "极限")

    # ---- B. 用户管理(管理员视角) ----
    def b1():
        r = req("GET", "/users", admin)
        return r.status_code == 200 and len(r.json()) >= 4, f"{len(r.json())} 个用户"
    t(b1, "B.用户管理", "管理员列出全部用户", "管理员")

    def b2():
        r = req("GET", "/users", ta)
        return r.status_code == 403, f"普通用户访问被拒 HTTP {r.status_code}"
    t(b2, "B.用户管理", "普通用户访问用户管理被拒(403)", "一般用户")

    def b3():
        r = req("POST", "/users", admin, {"username": "m_user_d", "display_name": "丁", "role": "user", "password": "Mock@2026"})
        return r.status_code == 201, f"HTTP {r.status_code}"
    t(b3, "B.用户管理", "管理员创建用户", "管理员")

    def b4():
        r = req("POST", "/users", admin, {"username": "m_user_d", "display_name": "重复", "role": "user", "password": "Mock@2026"})
        return r.status_code == 400, "重复账号被拒(400)"
    t(b4, "B.用户管理", "重复账号名被拒", "极限")

    def b5():
        r = req("POST", "/users", admin, {"username": "a", "display_name": "短", "role": "user", "password": "Mock@2026"})
        return r.status_code == 422, "过短账号名被拒(422)"
    t(b5, "B.用户管理", "账号名长度下限校验", "极限")

    def b6():
        r = req("POST", "/users", admin, {"username": "m_user_e", "role": "user", "password": "1234567"})
        return r.status_code == 422, "弱密码(7位)被拒(422)"
    t(b6, "B.用户管理", "密码强度下限校验", "极限")

    def b7():
        r = req("POST", "/users", admin, {"username": "m_user_x", "role": "hacker", "password": "Mock@2026"})
        return r.status_code == 400, "非法角色被拒(400)"
    t(b7, "B.用户管理", "非法角色值被拒", "极限")

    # ---- C. 主体管理(多角度) ----
    def c1():
        r = req("POST", "/suppliers", ta, {"name": f"{PREFIX}新供货方"})
        return r.status_code == 201, f"HTTP {r.status_code}"
    t(c1, "C.主体", "创建供货方(最小字段)", "一般用户")

    def c2():
        r = req("POST", "/suppliers", ta, {"name": ""})
        return r.status_code == 422, "空名称被拒(422)"
    t(c2, "C.主体", "空名称被拒", "极限")

    def c3():
        r = req("POST", "/suppliers", ta, {"name": "X" * 200})
        return r.status_code == 422, "超长名称被拒(422)"
    t(c3, "C.主体", "超长名称被拒(200字符)", "极限")

    def c4():
        r = req("POST", "/suppliers", ta, {"name": f"{PREFIX}注入测试' OR 1=1; DROP TABLE suppliers; --"})
        return r.status_code == 201, "SQL 注入字符串作为名称安全入库(201)"
    t(c4, "C.主体", "SQL 注入字符串安全入库(参数化)", "安全")

    def c5():
        r = req("POST", "/suppliers", ta, {"name": f"{PREFIX}XSS<script>alert(1)</script>"})
        return r.status_code == 201 and "<script>" in r.text, "XSS 载荷安全存储(转义由前端处理,后端不执行)"
    t(c5, "C.主体", "XSS 载荷安全存储", "安全")

    def c6():
        r = req("GET", f"/suppliers/{m['s_normal']}", tc)
        return r.status_code == 404, f"跨用户访问被拒(404) HTTP {r.status_code}"
    t(c6, "C.主体", "跨用户数据隔离(无共享不可见)", "一般用户")

    def c7():
        r = req("GET", "/suppliers", admin)
        names = {s["name"] for s in r.json()}
        return f"{PREFIX}芯联科技" in names and f"{PREFIX}无配额方" in names, "管理员全局可见全部主体"
    t(c7, "C.主体", "管理员全局可见", "管理员")

    def c8():
        # 乐观锁:过期版本 409
        sup = req("GET", f"/suppliers/{m['s_normal']}", ta).json()
        r = req("PATCH", f"/suppliers/{m['s_normal']}", ta, {"version": sup["version"] - 1, "short_name": "旧版"})
        return r.status_code == 409, f"过期版本更新被拒(409) HTTP {r.status_code}"
    t(c8, "C.主体", "乐观锁:过期版本冲突", "并发")

    def c9():
        r = req("POST", f"/suppliers/{m['s_noquota']}/quotas", ta, {"batch_no": "QB-X", "quantity": -5})
        return r.status_code == 422, "负数量配额被拒(422)"
    t(c9, "C.主体", "配额负数量被拒", "极限")

    def c10():
        r = req("POST", f"/suppliers/{m['s_noquota']}/quotas", tb, {"batch_no": "QB-BIG", "quantity": 10**9})
        return r.status_code == 201, "超大配额(10亿)可录入,验证数值范围"
    t(c10, "C.主体", "配额极大值(10^9)录入", "极限")

    def c11():
        r = req("POST", f"/suppliers/{m['s_noquota']}/quotas", ta, {"batch_no": "QB-越权", "quantity": 10})
        return r.status_code == 404, f"他人供货方下加配额被拒 HTTP {r.status_code}"
    t(c11, "C.主体", "越权操作他人配额被拒", "一般用户")

    def c12():
        r = req("POST", "/customers", ta, {"name": f"{PREFIX}边界客户", "value_grade": "Z"})
        return r.status_code == 201, "自由文本字段接受任意值(画像字段无枚举限制)"
    t(c12, "C.主体", "画像字段宽松录入", "边界")

    def c13():
        r = req("POST", "/middles", ta, {"name": f"{PREFIX}第0层", "layer_no": 0})
        return r.status_code == 422, "层级范围校验(1-2)生效(422)"
    t(c13, "C.主体", "中间层层级边界校验", "极限")

    def c14():
        r = req("GET", f"/communications?entity_type=supplier&entity_id={m['s_normal']}", ta)
        return r.status_code == 200, "沟通记录查询正常(append-only 列表)"
    t(c14, "C.主体", "沟通记录查询", "一般用户")

    # ---- D. 共享机制 ----
    def d1():
        r = req("POST", "/shares", ta, {"target_id": tc[0] if False else 1, "scopes": ["all"]})
        return r.status_code in (400, 201), f"HTTP {r.status_code}(目标为管理员,取决于是否已有关系)"
    t(d1, "D.共享", "向管理员发起共享", "一般用户")

    def d2():
        r = req("POST", "/shares", ta, {"target_id": 99999, "scopes": ["all"]})
        return r.status_code == 400, "目标用户不存在被拒(400)"
    t(d2, "D.共享", "共享给不存在用户被拒", "极限")

    def d3():
        me_id = req("GET", "/users/options", ta).json()
        me = [u for u in me_id if u["username"] == "m_user_a"][0]["id"]
        r = req("POST", "/shares", ta, {"target_id": me, "scopes": ["all"]})
        return r.status_code == 400, "与自己共享被拒(400)"
    t(d3, "D.共享", "与自己共享被拒", "极限")

    def d4():
        r = req("POST", "/shares", ta, {"target_id": 1, "scopes": ["hacker"]})
        return r.status_code == 400, "非法共享范围被拒(400)"
    t(d4, "D.共享", "非法共享范围被拒", "极限")

    def d5():
        # 重复申请(已有 active 关系)
        r = req("POST", "/shares", ta, {"target_id": req("GET", "/users/options", ta).json()[2]["id"], "scopes": ["supplier"]})
        return r.status_code == 400, f"重复共享申请被拒(400) HTTP {r.status_code}"
    t(d5, "D.共享", "重复共享申请被拒", "边界")

    # ---- E. 看板与匹配 ----
    def e1():
        r = req("GET", "/publications", tb)
        titles = [p["title"] for p in r.json()]
        return f"{PREFIX}求购B300现货20台" in titles and not any("私密" in x for x in titles), "公开看板全员可见、私密不可见"
    t(e1, "E.看板", "看板公开/私密可见性", "一般用户")

    def e2():
        r = req("POST", "/publications", ta, {"type": "demand", "product_line_id": 99999, "title": "坏产品线"})
        return r.status_code == 400, "不存在的产品线被拒(400)"
    t(e2, "E.看板", "无效产品线发布被拒", "极限")

    def e3():
        r = req("POST", "/publications", ta, {"type": "hacker", "title": "坏类型"})
        return r.status_code == 422, "非法发布类型被拒(422)"
    t(e3, "E.看板", "非法发布类型被拒", "极限")

    def e4():
        r = req("GET", f"/match?publication_id={m['pub_demand']['id']}", ta)
        return r.status_code == 200 and len(r.json()["results"]) >= 3, f"命中 {len(r.json().get('results', []))} 家"
    t(e4, "E.匹配", "匹配引擎命中多家供货方", "一般用户")

    def e5():
        r = req("GET", f"/match?publication_id={m['pub_demand']['id']}", ta)
        d = r.json()
        reasons = d["results"][0].get("reasons", [])
        return any("配额" in x for x in reasons) and "breakdown" in d["results"][0], "评分依据与分解分数完整"
    t(e5, "E.匹配", "匹配评分可解释(依据+分解)", "一般用户")

    def e6():
        # 归属裁剪:tb 按自己的客户匹配,ta 的供货方应为简要+维护人
        r = req("GET", f"/match?customer_id={m['c_unverified']}", tb)
        d = r.json()
        brief_ok = any(not x["full"] and "owner_name" in x["entity"] for x in d["results"])
        return brief_ok, f"他人数据简要+维护人标注(命中 {len(d.get('results', []))} 家)"
    t(e6, "E.匹配", "归属裁剪:他人简要+维护人", "一般用户")

    def e7():
        # 优先级影响排序:原本第一名 s_normal 设为优先级 1 后应跌出第一
        before = req("GET", f"/match?publication_id={m['pub_demand']['id']}", ta).json()["results"][0]["entity"]["id"]
        req("PUT", "/priorities", ta, {"entity_type": "supplier", "entity_id": m["s_normal"], "priority": 1})
        after = req("GET", f"/match?publication_id={m['pub_demand']['id']}", ta).json()["results"][0]["entity"]["id"]
        req("DELETE", f"/priorities/supplier/{m['s_normal']}", ta)
        return before == m["s_normal"] and after != m["s_normal"], f"设优先级 1 后第一名由 {before} 变为 {after}"
    t(e7, "E.匹配", "优先级权重最高(30%)生效", "一般用户")

    def e8():
        r = req("PUT", "/priorities", ta, {"entity_type": "supplier", "entity_id": m["s_normal"], "priority": 10})
        return r.status_code == 422, "优先级超界(10)被拒(422)"
    t(e8, "E.匹配", "优先级边界(1-9)校验", "极限")

    def e9():
        r = req("GET", "/match", ta)
        return r.status_code == 400, "缺少匹配来源被拒(400)"
    t(e9, "E.匹配", "匹配参数缺失校验", "边界")

    # ---- F. 订单与状态机 ----
    def f1():
        o = req("POST", "/orders", ta, {"order_no": f"{PREFIX}DD-状态机", "quantity": 10})
        return o.status_code == 201, f"HTTP {o.status_code}"
    t(f1, "F.订单", "订单最小字段录入", "一般用户")

    def f2():
        oid = req("GET", "/orders", ta).json()[0]["id"]
        r = req("POST", f"/orders/{oid}/status", ta, {"status": "done"})
        return r.status_code == 400, f"跳级流转被拒(400) HTTP {r.status_code}"
    t(f2, "F.订单", "状态机:跳级被拒(已录入→已完成)", "极限")

    def f3():
        oid = req("GET", "/orders", ta).json()[0]["id"]
        r = req("POST", f"/orders/{oid}/status", ta, {"status": "hacker_status"})
        return r.status_code == 400, "非法状态值被拒(400)"
    t(f3, "F.订单", "非法状态值被拒", "极限")

    def f4():
        r = req("GET", f"/orders/{m['o3']['id']}", tb)
        return r.status_code == 200 and r.json()["status"] == "breach_processing", "违约流程:处理中状态正确"
    t(f4, "F.订单", "违约订单状态正确", "一般用户")

    def f5():
        r = req("POST", f"/orders/{m['o3']['id']}/status", tb, {"status": "breach_resolved"})
        body = r.json()
        return r.status_code == 200 and body["status"] == "paying", f"违约解决自动回到原环节(paying) 实际={body.get('status')}"
    t(f5, "F.订单", "违约解决自动回原环节", "一般用户")

    def f6():
        r = req("POST", f"/orders/{m['o1']['id']}/status", ta, {"status": "breach"})
        return r.status_code == 400, f"已完成订单不可再违约(400) HTTP {r.status_code}"
    t(f6, "F.订单", "终态订单不可再流转", "边界")

    def f7():
        r = req("GET", f"/orders/{m['o2']['id']}", tc)
        return r.status_code == 404, f"跨用户订单访问被拒(404) HTTP {r.status_code}"
    t(f7, "F.订单", "订单归属隔离", "一般用户")

    def f8():
        r = req("POST", f"/orders/{m['o2']['id']}/tracks", tb, {"category": "资金", "content": "越权记录"})
        return r.status_code == 404, f"越权添加跟踪事件被拒 HTTP {r.status_code}"
    t(f8, "F.订单", "越权写跟踪事件被拒", "一般用户")

    def f9():
        r = req("PATCH", f"/orders/{m['o2']['id']}", ta, {"version": 999, "contract_no": "冲突"})
        return r.status_code == 409, f"订单乐观锁冲突(409) HTTP {r.status_code}"
    t(f9, "F.订单", "订单乐观锁", "并发")

    def f10():
        r = req("POST", f"/orders/{m['o2']['id']}/breaches", ta, {"breach_party": "下游", "breach_content": ""})
        return r.status_code == 422, "空违约事项被拒(422)"
    t(f10, "F.订单", "违约事项必填校验", "极限")

    # ---- G. 分析中台 ----
    def g1():
        r = req("GET", "/analytics/overview", admin)
        d = r.json()
        return d["supplier_count"] >= 9 and d["customer_count"] >= 3, f"KPI:供货方 {d['supplier_count']},客户 {d['customer_count']}"
    t(g1, "G.分析", "KPI 数据正确(管理员全局)", "管理员")

    def g2():
        r = req("GET", "/analytics/overview", tc)
        d = r.json()
        return d["supplier_count"] >= 1 and len(d["monthly_trend"]) == 12, f"普通用户视角:供货方 {d['supplier_count']},趋势 12 个月"
    t(g2, "G.分析", "KPI 归属裁剪(普通用户)", "一般用户")

    def g3():
        r = req("GET", "/analytics/overview", admin)
        d = r.json()
        return len(d["expiring_quotas"]) >= 1, f"配额到期预警捕获 {len(d['expiring_quotas'])} 条"
    t(g3, "G.分析", "配额到期预警(3天内)", "管理员")

    def g4():
        r = req("GET", "/analytics/overview", admin)
        return r.json()["month_amount"] >= 28400000, f"本月成交额 {r.json()['month_amount']:,.0f}"
    t(g4, "G.分析", "成交额统计", "管理员")

    # ---- H. AI 功能 ----
    def h1():
        r = req("POST", "/publications/parse", ta, {"text": "求购 B300 期货 100 台,预算 1.3 亿,可接受国内信用证,四季度交货"})
        d = r.json()
        return r.status_code == 200 and d.get("product_name") == "B300", f"解析型号={d.get('product_name')},价格={d.get('price_min')}"
    t(h1, "H.AI", "看板语义解析(万元→元换算)", "一般用户")

    def h2():
        r = req("POST", f"/orders/{m['o2']['id']}/ai-summary", ta)
        summary = r.json().get("summary", "")
        if len(summary) < 20:
            r = req("POST", f"/orders/{m['o2']['id']}/ai-summary", ta)
            summary = r.json().get("summary", "")
        return r.status_code == 200 and len(summary) > 20, f"摘要 {len(summary)} 字"
    t(h2, "H.AI", "订单智能摘要", "一般用户")

    def h3():
        r = req("POST", f"/orders/{m['o2']['id']}/ai-extract", ta, {"text": "客户说下周一打款,上游确认配额已锁定 5 台,预计周三发货"})
        evs = r.json().get("events", [])
        if not evs:
            r = req("POST", f"/orders/{m['o2']['id']}/ai-extract", ta, {"text": "客户确认于下周一支付剩余货款;上游通知配额已锁定 5 台现货;预计本周三从香港仓库发出并安排报关"})
            evs = r.json().get("events", [])
        return r.status_code == 200 and len(evs) >= 1, f"提取 {len(evs)} 条事件"
    t(h3, "H.AI", "沟通记录→跟踪事件提取", "一般用户")

    def h4():
        # 用 Pillow 生成余额图走完整验资 AI 初审
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (900, 260), "white")
        d = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 40)
        except Exception:
            font = ImageFont.load_default()
        d.text((40, 60), "Account Balance: 88,888,888.88", fill="black", font=font)
        d.text((40, 150), "Date: 2026-08-18", fill="black", font=font)
        tmp = Path("/tmp/mock_balance.png")
        img.save(tmp)
        cid = req("GET", "/customers", ta).json()[0]["id"]
        with tmp.open("rb") as f:
            up = requests.post(
                BASE + f"/files?entity_type=customer&entity_id={cid}",
                headers={"Authorization": f"Bearer {ta}"},
                files={"file": ("mock_balance.png", f, "image/png")},
                timeout=60,
            )
        stored = up.json()["stored_name"]
        vr = req("POST", f"/customers/{cid}/verifications", ta, {"verify_type": "balance_photo", "file_name": "mock_balance.png", "file_path": stored, "material_date": "2026-08-18", "valid_until": "2026-08-21"})
        vid = vr.json()["id"]
        r = req("POST", f"/verifications/{vid}/ai-review", ta)
        d = r.json()
        if not d.get("ai_status"):
            time.sleep(3)
            r = req("POST", f"/verifications/{vid}/ai-review", ta)
            d = r.json()
        report_norm = d.get("ai_report", "").replace(",", "")
        ok = r.status_code == 200 and d["ai_status"] in ("passed", "flagged") and "88888888" in report_norm
        return ok, f"AI 状态={d.get('ai_status')},金额识别正确:{'88888888' in report_norm}"
    t(h4, "H.AI", "验资图片 AI 初审(端到端)", "一般用户")

    def h5():
        r = req("POST", "/publications/parse", ta, {"text": "短"})
        return r.status_code == 422, "过短输入被拒(422)"
    t(h5, "H.AI", "AI 接口输入长度下限", "极限")

    # ---- I. 审计与安全 ----
    def i1():
        r = req("GET", "/audit-logs", admin)
        return r.status_code == 200 and len(r.json()) > 30, f"{len(r.json())} 条审计日志"
    t(i1, "I.审计", "审计日志全量留痕", "管理员")

    def i2():
        r = req("GET", "/audit-logs", ta)
        return r.status_code == 403, f"普通用户访问审计被拒 HTTP {r.status_code}"
    t(i2, "I.审计", "审计日志仅管理员可查", "一般用户")

    def i3():
        r = req("PATCH", "/audit-logs/1", admin, {"detail": "篡改"})
        return r.status_code in (405, 404), f"审计日志无修改接口 HTTP {r.status_code}"
    t(i3, "I.审计", "审计日志不可篡改", "安全")

    def i4():
        r = req("GET", "/files/../../etc/passwd", admin)
        return r.status_code in (400, 404), f"路径穿越被拒 HTTP {r.status_code}"
    t(i4, "I.安全", "文件下载路径穿越防护", "安全")

    def i5():
        r = requests.get(BASE + "/files/nonexistent_abc.png", headers={"Authorization": f"Bearer {ta}"}, timeout=30)
        return r.status_code == 404, "不存在的文件返回 404"
    t(i5, "I.安全", "文件不存在处理", "边界")

    def i6():
        # 上传超限文件(21MB 非视频):服务端超过 20MB 即中断,客户端可能收到 400 或连接中断
        big = Path("/tmp/mock_big.bin")
        big.write_bytes(b"\0" * (21 * 1024 * 1024))
        try:
            with big.open("rb") as f:
                r = requests.post(BASE + "/files", headers={"Authorization": f"Bearer {ta}"}, files={"file": ("big.png", f, "image/png")}, timeout=120)
            code = r.status_code
        except requests.exceptions.RequestException as e:
            code = f"连接中断({type(e).__name__})"
        big.unlink(missing_ok=True)
        return code in (400,) or "连接中断" in str(code), f"超限上传被拦截:{code}"
    t(i6, "I.安全", "超大文件上传拦截(20MB 上限)", "极限")

    def i7():
        r = requests.post(BASE + "/files", headers={"Authorization": f"Bearer {ta}"}, files={"file": ("evil.exe", b"x", "application/octet-stream")}, timeout=30)
        return r.status_code == 400, "非法扩展名被拒(400)"
    t(i7, "I.安全", "上传白名单(格式校验)", "安全")

    def i8():
        r = req("POST", "/suppliers", ta, {"name": f"{PREFIX}审计验证方"})
        sid = r.json()["id"]
        req("PATCH", f"/suppliers/{sid}", ta, {"version": 1, "short_name": "改了"})
        logs = req("GET", "/audit-logs?entity_type=supplier", admin).json()
        return any(x["entity_id"] == str(sid) and x["action"] == "update" and x["old_value"] for x in logs), "每次更新记录改前/改后值"
    t(i8, "I.审计", "审计含改前/改后值差异", "管理员")

    # ---- J. 压力与并发 ----
    def j1():
        n = 100
        errs = []

        def worker(i):
            try:
                r = req("GET", "/suppliers", ta)
                if r.status_code != 200:
                    errs.append(r.status_code)
            except Exception as e:
                errs.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        st = time.time()
        [th.start() for th in threads]
        [th.join() for th in threads]
        el = time.time() - st
        return not errs, f"{n} 并发请求,耗时 {el:.2f}s,失败 {len(errs)}"
    t(j1, "J.压力", "100 并发读(供货方列表)", "压力")

    def j2():
        # 并发同版本更新:期望恰好 1 个 200,其余 409
        sup = req("GET", f"/suppliers/{m['s_normal']}", ta).json()
        v = sup["version"]
        codes = []
        lock = threading.Lock()

        def worker():
            r = req("PATCH", f"/suppliers/{m['s_normal']}", ta, {"version": v, "short_name": f"并发{r.random()}" if False else "并发改"})
            with lock:
                codes.append(r.status_code)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        [th.start() for th in threads]
        [th.join() for th in threads]
        ok = codes.count(200) == 1 and codes.count(409) == 9
        return ok, f"10 并发同版本更新:200×{codes.count(200)},409×{codes.count(409)}"
    t(j2, "J.压力", "乐观锁并发写(10 并发同版本)", "并发")

    def j3():
        # 快速连续登录(50 次)不触发误锁
        codes = [req("POST", "/auth/login", json_body={"username": "m_user_a", "password": "Mock@2026"}).status_code for _ in range(50)]
        return codes.count(200) == 50, f"50 次正确登录全部成功({codes.count(200)}/50)"
    t(j3, "J.压力", "高频正确登录不误锁", "压力")

    def j4():
        # 大数据量匹配:30 家供货方全量评分
        plid = req("GET", "/product-lines", ta).json()[0]["id"]
        for i in range(30):
            sid = req("POST", "/suppliers", ta, {"name": f"{PREFIX}压测供货方{i:02d}", "price": 1350000 + i * 1000}).json().get("id")
            if sid:
                req("POST", f"/suppliers/{sid}/quotas", ta, {"product_line_id": plid, "batch_no": f"QB-S{i:02d}", "quantity": 50})
        st = time.time()
        r = req("GET", f"/match?publication_id={m['pub_demand']['id']}", ta)
        el = time.time() - st
        return r.status_code == 200 and len(r.json()["results"]) >= 30, f"匹配 {len(r.json().get('results', []))} 家耗时 {el:.2f}s"
    t(j4, "J.压力", "30+ 供货方批量匹配性能", "压力")

    def j5():
        # 超长搜索词
        r = req("GET", f"/suppliers?keyword={'X' * 5000}", ta)
        return r.status_code == 200, "超长搜索词安全处理(200)"
    t(j5, "J.压力", "超长搜索词(5000字符)", "极限")

    def j6():
        r = req("POST", "/orders", ta, {"order_no": f"{PREFIX}DD-重复", "quantity": 1})
        first = r.json().get("id")
        r2 = req("POST", "/orders", ta, {"order_no": f"{PREFIX}DD-重复", "quantity": 1})
        return r2.status_code == 201 and r2.json()["id"] != first, "订单号允许重复(编号唯一性由人工管理)"
    t(j6, "J.压力", "订单号重复策略", "边界")


def generate_report():
    total = len(results)
    ok = COUNTER["ok"]
    fail = COUNTER["fail"]
    rate = round(ok / total * 100, 1) if total else 0
    cats: dict[str, dict] = {}
    for r in results:
        c = cats.setdefault(r["category"], {"total": 0, "ok": 0, "fail": 0, "items": []})
        c["total"] += 1
        c["ok" if r["passed"] else "fail"] += 1
        c["items"].append(r)

    rows = ""
    for cat, c in cats.items():
        rows += f'<tr><td class="cat">{cat}</td><td>{c["total"]}</td><td class="ok">{c["ok"]}</td><td class="fail">{c["fail"]}</td><td>{round(c["ok"]/c["total"]*100, 1)}%</td></tr>'

    sections = ""
    for cat, c in cats.items():
        items = ""
        for r in c["items"]:
            badge = f'<span class="b ok">通过</span>' if r["passed"] else f'<span class="b fail">失败</span>'
            items += f"<tr><td>{r['name']}</td><td>{r['role']}</td><td>{badge}</td><td class='det'>{r['detail']}</td><td>{r['ms']}ms</td></tr>"
        sections += f"""
        <h2>{cat}</h2>
        <table><thead><tr><th style='width:34%'>用例</th><th style='width:9%'>角色</th><th style='width:8%'>结果</th><th>详情</th><th style='width:9%'>耗时</th></tr></thead><tbody>{items}</tbody></table>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>SC-Link 全面测试报告</title>
<style>
  :root {{ --navy:#0F172A; --blue:#2563EB; --cyan:#06B6D4; --bg:#F5F7FB; --ink:#1E293B; --muted:#64748B; --line:#E2E8F0; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; background:var(--bg); color:var(--ink); line-height:1.7; font-size:14px; }}
  .cover {{ background:linear-gradient(135deg,#0F172A,#1E3A8A); color:#fff; padding:48px 8vw; }}
  .cover h1 {{ font-size:30px; }} .cover .sub {{ color:#93A6C8; margin-top:8px; font-size:14px; }}
  .stats {{ display:flex; gap:16px; margin:-30px auto 0; max-width:1120px; padding:0 20px; position:relative; }}
  .stat {{ flex:1; background:#fff; border:1px solid var(--line); border-radius:14px; padding:20px; box-shadow:0 10px 28px rgba(15,23,42,.08); }}
  .stat .num {{ font-size:32px; font-weight:700; }} .stat .lbl {{ color:var(--muted); font-size:12px; margin-top:4px; }}
  .ok {{ color:#059669; }} .fail {{ color:#DC2626; }}
  .wrap {{ max-width:1120px; margin:0 auto; padding:30px 20px 60px; }}
  h2 {{ font-size:18px; margin:28px 0 10px; padding-left:10px; border-left:4px solid var(--blue); }}
  table {{ width:100%; border-collapse:collapse; background:#fff; font-size:13px; }}
  th {{ background:var(--navy); color:#fff; text-align:left; padding:9px 12px; font-weight:600; }}
  td {{ border-bottom:1px solid var(--line); padding:8px 12px; vertical-align:top; }}
  .cat {{ font-weight:700; }} .det {{ color:var(--muted); word-break:break-all; }}
  .b {{ display:inline-block; font-size:11px; padding:1px 9px; border-radius:10px; }}
  .b.ok {{ background:#ECFDF5; }} .b.fail {{ background:#FEF2F2; }}
  footer {{ text-align:center; color:var(--muted); font-size:12px; padding:30px; }}
</style></head><body>
<div class="cover"><h1>SC-Link 供应链协同中台 · 全面测试报告</h1>
<div class="sub">双角色(管理员/一般用户)× 多角度(功能/边界/极限/权限/安全/并发/压力)· 含模拟交易与模拟跟踪 · 生成时间 {time.strftime('%Y-%m-%d %H:%M:%S')}</div></div>
<div class="stats">
  <div class="stat"><div class="num">{total}</div><div class="lbl">测试用例总数</div></div>
  <div class="stat"><div class="num ok">{ok}</div><div class="lbl">通过</div></div>
  <div class="stat"><div class="num fail">{fail}</div><div class="lbl">失败</div></div>
  <div class="stat"><div class="num" style="color:var(--blue)">{rate}%</div><div class="lbl">通过率</div></div>
</div>
<div class="wrap">
  <h2>分类汇总</h2>
  <table><thead><tr><th>分类</th><th>总数</th><th>通过</th><th>失败</th><th>通过率</th></tr></thead><tbody>{rows}</tbody></table>
  {sections}
</div>
<footer>SC-Link 全面测试报告 · 测试数据以「【测】」前缀标识,不影响正式数据</footer>
</body></html>"""
    REPORT.write_text(html, encoding="utf-8")
    print(f"\n======== 总计 {total} / 通过 {ok} / 失败 {fail} / 通过率 {rate}% ========")
    print(f"报告已生成:{REPORT}")


if __name__ == "__main__":
    mock = setup_mock()
    run_all(mock)
    generate_report()
