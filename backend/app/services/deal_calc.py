"""交易链路测算引擎:收支、截流资金峰值、价差、居间前置、代开证成本"""
from ..entities import DealFlow, DealNode


def flow_amount(f: DealFlow, totals: dict) -> float:
    """动作金额:固定值或百分比×基数"""
    if f.amount_type == "percent" and f.percent is not None:
        base = float(totals.get(f.base or "downstream_total", 0) or 0)
        return base * float(f.percent) / 100
    return float(f.amount or 0)


def compute(plan, nodes: list[DealNode], flows: list[DealFlow]) -> dict:
    qty = plan.quantity or 0
    upstream_total = (float(plan.upstream_price) if plan.upstream_price else 0) * qty
    downstream_total = (float(plan.downstream_price) if plan.downstream_price else 0) * qty
    spread = downstream_total - upstream_total
    # 包裹价差:单台价差(万元/台,用户直接输入)× 数量 = 总额;拆分 = 上游居间定额 + 中间层包裹收益
    wrapped_spread_total = float(plan.wrapped_spread or 0) * qty
    if wrapped_spread_total == 0 and plan.wrapped_price is not None and plan.upstream_price:
        wrapped_spread_total = (float(plan.wrapped_price) - float(plan.upstream_price)) * qty
    fixed = float(plan.supplier_fee_fixed or 0)
    middle_wrapped = max(wrapped_spread_total - fixed, 0.0)
    upfront_amount = 0.0
    if plan.upfront_percent is not None:
        upfront_amount = middle_wrapped * float(plan.upfront_percent) / 100
    totals = {
        "downstream_total": downstream_total,
        "upstream_total": upstream_total,
        "spread": spread,
        "wrapped_spread": round(wrapped_spread_total, 2),
        "middle_wrapped": round(middle_wrapped, 2),
    }

    node_map = {n.id: n for n in nodes}
    stats = {n.id: {"receive": 0.0, "paid": 0.0, "held_peak": 0.0, "held_final": 0.0, "flows": []} for n in nodes}
    balance = {n.id: 0.0 for n in nodes}

    sorted_flows = sorted(flows, key=lambda x: (x.seq, x.id))
    for f in sorted_flows:
        amt = flow_amount(f, totals)
        fr, to = f.from_node_id, f.to_node_id
        if fr in node_map and fr != to:
            stats[fr]["paid"] += amt
            balance[fr] -= amt
            stats[fr]["held_peak"] = max(stats[fr]["held_peak"], max(-balance[fr], 0.0))
        if to in node_map and to != fr:
            stats[to]["receive"] += amt
            balance[to] += amt
            stats[to]["held_peak"] = max(stats[to]["held_peak"], balance[to])
        stats.setdefault(fr, None)
        for nid in (fr, to):
            if nid in stats and stats[nid] is not None:
                stats[nid]["flows"].append(
                    {
                        "id": f.id, "seq": f.seq, "type": f.flow_type, "label": f.label,
                        "amount": round(amt, 2), "from": fr, "to": to,
                    }
                )

    for nid in balance:
        stats[nid]["held_final"] = round(max(balance[nid], 0.0), 2)

    # 中间层三收益点
    middle_metrics = []
    for n in sorted(nodes, key=lambda x: x.seq):
        if n.role != "middle":
            continue
        s = stats[n.id]
        upfront = sum(x["amount"] for x in s["flows"] if x["type"] in ("upfront_fee", "fee"))
        # 代开证/开保函中间层:收益 = 代开费用(交银行) + 收益(定额或比例),保证金为押金不计收益
        def _amt(fixed_v, percent_v, base_key):
            if percent_v is not None:
                return float(totals.get(base_key or "downstream_total", 0)) * float(percent_v) / 100
            return float(fixed_v or 0)

        fee_amount = _amt(n.fee_fixed, n.fee_percent, n.fee_base)
        income_amount = _amt(n.income_fixed, n.income_percent, n.income_base)
        deposit_amount = float(n.deposit_fixed or 0)
        if deposit_amount == 0 and plan.lc_deposit_percent is not None:
            deposit_amount = downstream_total * float(plan.lc_deposit_percent) / 100

        middle_metrics.append(
            {
                "node_id": n.id,
                "name": n.name,
                "purpose": n.purpose or "交易居间",
                "receive_total": round(s["receive"], 2),
                "paid_total": round(s["paid"], 2),
                "held_peak": round(s["held_peak"], 2),
                "held_final": round(s["held_final"], 2),
                "upfront_fee": round(upfront, 2),
                # 包裹价差构成(测算值,万元)
                "wrapped_spread_total": round(wrapped_spread_total, 2),
                "supplier_fee_fixed": round(fixed, 2),
                "middle_wrapped": round(middle_wrapped, 2),
                "upfront_amount": round(upfront_amount, 2),
                "upfront_remain": round(middle_wrapped - upfront_amount, 2),
                # 代开证/开保函收益模型(万元)
                "fee_amount": round(fee_amount, 2),
                "income_amount": round(income_amount, 2),
                "deposit": round(deposit_amount, 2),
            }
        )

    # 代开证成本(保证金+开证费)
    lc_cost = None
    if plan.payment_mode.startswith("信用证") and plan.lc_deposit_percent is not None or plan.lc_fee_percent is not None:
        deposit = downstream_total * (float(plan.lc_deposit_percent or 0)) / 100
        fee = downstream_total * (float(plan.lc_fee_percent or 0)) / 100
        lc_cost = {"deposit": round(deposit, 2), "fee": round(fee, 2), "total": round(deposit + fee, 2)}

    return {
        "totals": {k: round(v, 2) for k, v in totals.items()},
        "spread": round(spread, 2),
        "nodes": [
            {
                "node_id": n.id, "role": n.role, "name": n.name, "seq": n.seq,
                "receive_total": round(stats[n.id]["receive"], 2),
                "paid_total": round(stats[n.id]["paid"], 2),
                "net": round(stats[n.id]["receive"] - stats[n.id]["paid"], 2),
                "held_peak": round(stats[n.id]["held_peak"], 2),
                "held_final": round(stats[n.id]["held_final"], 2),
            }
            for n in sorted(nodes, key=lambda x: x.seq)
        ],
        "middle_metrics": middle_metrics,
        "lc_cost": lc_cost,
    }
