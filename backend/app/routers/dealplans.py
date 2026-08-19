from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..entities import DealFlow, DealNode, DealPlan
from ..models import User
from ..schemas_entities import (
    DealFlowIn,
    DealNodeIn,
    DealPlanIn,
    DealPlanOut,
    DealPlanUpdate,
)
from ..services.audit import write_audit
from ..services.deal_calc import compute
from ..services.locking import conditional_update
from ..services.visibility import apply_visibility

router = APIRouter(tags=["dealplans"])

PLAN_FIELDS = [
    "title", "order_id", "product_line_id", "quantity", "upstream_price",
    "downstream_price", "currency", "payment_mode", "wrapped_price", "wrapped_spread",
    "supplier_fee_fixed", "upfront_percent", "lc_agent_middle",
    "lc_deposit_percent", "lc_fee_percent", "status",
]

FLOW_TYPES = ("payment", "guarantee", "lc_issue", "margin", "upfront_fee", "supplier_return", "lc_fee", "goods", "other")
BASE_OPTIONS = ("downstream_total", "upstream_total", "spread", "wrapped_spread", "middle_wrapped")


def _plan_or_404(db: Session, plan_id: int, user: User) -> DealPlan:
    from ..services.visibility import can_access_entity

    obj = db.get(DealPlan, plan_id)
    if obj is None or not can_access_entity(db, user, "supplier", obj.owner_id):
        raise HTTPException(status_code=404, detail="方案不存在或无权访问")
    return obj


@router.get("/deal-plans", response_model=list[DealPlanOut])
def list_plans(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 交易方案与订单同属成交域:跟随共享可见性(含共享范围),管理员全局可见
    q = apply_visibility(db.query(DealPlan), DealPlan, db, user, "supplier")
    return q.order_by(DealPlan.id.desc()).all()


@router.post("/deal-plans", response_model=DealPlanOut, status_code=201)
def create_plan(body: DealPlanIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = DealPlan(**body.model_dump(), owner_id=user.id, last_editor_id=user.id)
    db.add(plan)
    db.flush()
    write_audit(db, request, user, "create", "deal_plan", str(plan.id), new_value=body.model_dump(), detail=f"创建交易方案「{body.title}」")
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/deal-plans/{plan_id}", response_model=DealPlanOut)
def get_plan(plan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _plan_or_404(db, plan_id, user)


@router.patch("/deal-plans/{plan_id}", response_model=DealPlanOut)
def update_plan(plan_id: int, body: DealPlanUpdate, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = _plan_or_404(db, plan_id, user)
    changes = body.model_dump(exclude_unset=True)
    changes.pop("version", None)
    old = {f: getattr(plan, f) for f in PLAN_FIELDS}
    ok = conditional_update(db, DealPlan, plan.id, body.version, changes, user.id)
    if not ok:
        raise HTTPException(status_code=409, detail=f"数据已被他人更新(当前 v{plan.version}),请刷新后重试")
    new = {**old, **changes}
    write_audit(db, request, user, "update", "deal_plan", str(plan.id), old_value=old, new_value=new, detail=f"更新交易方案「{plan.title}」")
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/deal-plans/{plan_id}")
def delete_plan(plan_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = _plan_or_404(db, plan_id, user)
    old = {"title": plan.title}
    write_audit(db, request, user, "delete", "deal_plan", str(plan.id), old_value=old, detail=f"删除交易方案「{plan.title}」")
    db.query(DealFlow).filter(DealFlow.plan_id == plan.id).delete()
    db.query(DealNode).filter(DealNode.plan_id == plan.id).delete()
    db.delete(plan)
    db.commit()
    return {"ok": True}


# ---------- 节点 ----------
@router.get("/deal-plans/{plan_id}/nodes")
def list_nodes(plan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _plan_or_404(db, plan_id, user)
    return db.query(DealNode).filter(DealNode.plan_id == plan_id).order_by(DealNode.seq, DealNode.id).all()


@router.post("/deal-plans/{plan_id}/nodes", status_code=201)
def create_node(plan_id: int, body: DealNodeIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _plan_or_404(db, plan_id, user)
    node = DealNode(plan_id=plan_id, **body.model_dump())
    db.add(node)
    db.flush()
    write_audit(db, request, user, "create", "deal_node", str(node.id), new_value=body.model_dump(), detail=f"方案#{plan_id} 新增节点 {body.name}({body.role})")
    db.commit()
    db.refresh(node)
    return node


@router.delete("/deal-nodes/{node_id}")
def delete_node(node_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    node = db.get(DealNode, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="节点不存在")
    _plan_or_404(db, node.plan_id, user)
    write_audit(db, request, user, "delete", "deal_node", str(node.id), old_value={"name": node.name}, detail=f"删除节点 {node.name}")
    db.query(DealFlow).filter((DealFlow.from_node_id == node.id) | (DealFlow.to_node_id == node.id)).delete()
    db.delete(node)
    db.commit()
    return {"ok": True}


# ---------- 动作流 ----------
@router.get("/deal-plans/{plan_id}/flows")
def list_flows(plan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _plan_or_404(db, plan_id, user)
    return db.query(DealFlow).filter(DealFlow.plan_id == plan_id).order_by(DealFlow.seq, DealFlow.id).all()


@router.post("/deal-plans/{plan_id}/flows", status_code=201)
def create_flow(plan_id: int, body: DealFlowIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _plan_or_404(db, plan_id, user)
    if body.flow_type not in FLOW_TYPES:
        raise HTTPException(status_code=400, detail="动作类型不合法")
    if body.base not in BASE_OPTIONS:
        raise HTTPException(status_code=400, detail="比例基数不合法")
    flow = DealFlow(plan_id=plan_id, **body.model_dump())
    db.add(flow)
    db.flush()
    write_audit(db, request, user, "create", "deal_flow", str(flow.id), new_value=body.model_dump(), detail=f"方案#{plan_id} 新增动作「{body.label}」")
    db.commit()
    db.refresh(flow)
    return flow


@router.patch("/deal-flows/{flow_id}")
def update_flow(flow_id: int, body: DealFlowIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    flow = db.get(DealFlow, flow_id)
    if flow is None:
        raise HTTPException(status_code=404, detail="动作不存在")
    _plan_or_404(db, flow.plan_id, user)
    if body.flow_type not in FLOW_TYPES or body.base not in BASE_OPTIONS:
        raise HTTPException(status_code=400, detail="类型或基数不合法")
    old = {"seq": flow.seq, "label": flow.label}
    for f, v in body.model_dump().items():
        setattr(flow, f, v)
    write_audit(db, request, user, "update", "deal_flow", str(flow.id), old_value=old, new_value=body.model_dump(), detail=f"更新动作「{body.label}」")
    db.commit()
    db.refresh(flow)
    return flow


@router.delete("/deal-flows/{flow_id}")
def delete_flow(flow_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    flow = db.get(DealFlow, flow_id)
    if flow is None:
        raise HTTPException(status_code=404, detail="动作不存在")
    _plan_or_404(db, flow.plan_id, user)
    write_audit(db, request, user, "delete", "deal_flow", str(flow.id), old_value={"label": flow.label}, detail=f"删除动作「{flow.label}」")
    db.delete(flow)
    db.commit()
    return {"ok": True}


@router.get("/deal-plans/{plan_id}/compute")
def compute_plan(plan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = _plan_or_404(db, plan_id, user)
    nodes = db.query(DealNode).filter(DealNode.plan_id == plan_id).all()
    flows = db.query(DealFlow).filter(DealFlow.plan_id == plan_id).all()
    return compute(plan, nodes, flows)
