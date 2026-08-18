from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_admin
from ..entities import (
    Communication,
    MiddleLayer,
    OverseasChain,
    ProductLine,
    Supplier,
    SupplierQuota,
)
from ..models import User
from ..schemas_entities import (
    ChainIn,
    ChainOut,
    ChainUpdate,
    CommunicationIn,
    CommunicationOut,
    MiddleIn,
    MiddleOut,
    MiddleUpdate,
    ProductLineIn,
    ProductLineOut,
    QuotaIn,
    QuotaOut,
    QuotaUpdate,
    SupplierIn,
    SupplierOut,
    SupplierUpdate,
)
from ..services.audit import write_audit
from ..services.visibility import apply_visibility, can_access_entity

router = APIRouter(tags=["entities"])

QUOTA_STATUSES = ("available", "locked", "used_up", "expired")


def _entity_or_404(db: Session, cls, entity_id: int, user: User, entity_type: str):
    obj = db.get(cls, entity_id)
    if obj is None or not can_access_entity(db, user, entity_type, obj.owner_id):
        raise HTTPException(status_code=404, detail="记录不存在或无权访问")
    return obj


def _check_version(obj, version: int) -> None:
    if obj.version != version:
        raise HTTPException(
            status_code=409,
            detail="数据已被他人更新(当前版本 v%d,你基于 v%d 编辑),请刷新后重试" % (obj.version, version),
        )


def _snapshot(obj, fields: list[str]) -> dict:
    return {f: getattr(obj, f) for f in fields}


# ================= 产品线 =================
@router.get("/product-lines", response_model=list[ProductLineOut])
def list_product_lines(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ProductLine).order_by(ProductLine.id).all()


@router.post("/product-lines", response_model=ProductLineOut, status_code=201)
def create_product_line(
    body: ProductLineIn,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(ProductLine).filter(ProductLine.name == body.name).first():
        raise HTTPException(status_code=400, detail="产品线已存在")
    pl = ProductLine(**body.model_dump())
    db.add(pl)
    db.flush()
    write_audit(db, request, admin, "create", "product_line", str(pl.id), new_value=body.model_dump(), detail=f"创建产品线 {body.name}")
    db.commit()
    db.refresh(pl)
    return pl


# ================= 海外链路方 =================
CHAIN_FIELDS = ["name", "region", "contact_person", "contact_info", "description"]


@router.get("/chains", response_model=list[ChainOut])
def list_chains(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(OverseasChain)
    q = apply_visibility(q, OverseasChain, db, user, "chain")
    return q.order_by(OverseasChain.id.desc()).all()


@router.post("/chains", response_model=ChainOut, status_code=201)
def create_chain(body: ChainIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    obj = OverseasChain(**body.model_dump(), owner_id=user.id, last_editor_id=user.id)
    db.add(obj)
    db.flush()
    write_audit(db, request, user, "create", "chain", str(obj.id), new_value=body.model_dump(), detail=f"创建链路方 {body.name}")
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/chains/{chain_id}", response_model=ChainOut)
def update_chain(
    chain_id: int,
    body: ChainUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    obj = _entity_or_404(db, OverseasChain, chain_id, user, "chain")
    _check_version(obj, body.version)
    changes = body.model_dump(exclude_unset=True)
    changes.pop("version", None)
    old = _snapshot(obj, CHAIN_FIELDS)
    for f, v in changes.items():
        setattr(obj, f, v)
    obj.version += 1
    obj.last_editor_id = user.id
    new = _snapshot(obj, CHAIN_FIELDS)
    write_audit(db, request, user, "update", "chain", str(obj.id), old_value=old, new_value=new, detail=f"更新链路方 {obj.name}")
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/chains/{chain_id}")
def delete_chain(chain_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    obj = _entity_or_404(db, OverseasChain, chain_id, user, "chain")
    if db.query(Supplier).filter(Supplier.chain_id == obj.id).count():
        raise HTTPException(status_code=400, detail="该链路方下存在供货方,无法删除")
    old = _snapshot(obj, CHAIN_FIELDS)
    write_audit(db, request, user, "delete", "chain", str(obj.id), old_value=old, detail=f"删除链路方 {obj.name}")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ================= 上游供货方 =================
SUPPLIER_FIELDS = [
    "name", "short_name", "reg_location", "credit_code", "established_at", "registered_capital",
    "equity_structure", "contacts", "remark", "chain_id", "chain_role", "parent_supplier_id",
    "procurement_modes", "goods_type", "price", "currency", "price_valid_until", "moq",
    "delivery_cycle", "payment_terms", "invoice_type", "guarantee_type", "guarantee_ratio",
    "guarantee_issuer", "guarantee_issuer_name", "guarantee_valid_until", "financing_capacity",
    "guarantee_notes", "coop_status", "deal_count", "deal_amount", "fulfillment_rate",
    "breach_count", "credit_rating", "risk_notes",
]


@router.get("/suppliers", response_model=list[SupplierOut])
def list_suppliers(
    keyword: str = "",
    goods_type: str = "",
    chain_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Supplier)
    q = apply_visibility(q, Supplier, db, user, "supplier")
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(Supplier.name.like(like) | Supplier.short_name.like(like))
    if goods_type:
        q = q.filter(Supplier.goods_type == goods_type)
    if chain_id:
        q = q.filter(Supplier.chain_id == chain_id)
    return q.order_by(Supplier.updated_at.desc()).all()


@router.post("/suppliers", response_model=SupplierOut, status_code=201)
def create_supplier(body: SupplierIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    obj = Supplier(**body.model_dump(), owner_id=user.id, last_editor_id=user.id)
    db.add(obj)
    db.flush()
    write_audit(db, request, user, "create", "supplier", str(obj.id), new_value=body.model_dump(), detail=f"创建供货方 {body.name}")
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/suppliers/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _entity_or_404(db, Supplier, supplier_id, user, "supplier")


@router.patch("/suppliers/{supplier_id}", response_model=SupplierOut)
def update_supplier(
    supplier_id: int,
    body: SupplierUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    obj = _entity_or_404(db, Supplier, supplier_id, user, "supplier")
    _check_version(obj, body.version)
    changes = body.model_dump(exclude_unset=True)
    changes.pop("version", None)
    old = _snapshot(obj, SUPPLIER_FIELDS)
    for f, v in changes.items():
        setattr(obj, f, v)
    obj.version += 1
    obj.last_editor_id = user.id
    new = _snapshot(obj, SUPPLIER_FIELDS)
    write_audit(db, request, user, "update", "supplier", str(obj.id), old_value=old, new_value=new, detail=f"更新供货方 {obj.name}")
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/suppliers/{supplier_id}")
def delete_supplier(supplier_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    obj = _entity_or_404(db, Supplier, supplier_id, user, "supplier")
    old = _snapshot(obj, SUPPLIER_FIELDS)
    write_audit(db, request, user, "delete", "supplier", str(obj.id), old_value=old, detail=f"删除供货方 {obj.name}")
    db.query(SupplierQuota).filter(SupplierQuota.supplier_id == obj.id).delete()
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ================= 批次配额 =================
@router.get("/suppliers/{supplier_id}/quotas", response_model=list[QuotaOut])
def list_quotas(supplier_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _entity_or_404(db, Supplier, supplier_id, user, "supplier")
    return db.query(SupplierQuota).filter(SupplierQuota.supplier_id == supplier_id).order_by(SupplierQuota.id.desc()).all()


@router.post("/suppliers/{supplier_id}/quotas", response_model=QuotaOut, status_code=201)
def create_quota(
    supplier_id: int,
    body: QuotaIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _entity_or_404(db, Supplier, supplier_id, user, "supplier")
    if body.status not in QUOTA_STATUSES:
        raise HTTPException(status_code=400, detail="配额状态不合法")
    obj = SupplierQuota(**body.model_dump(), supplier_id=supplier_id, created_by=user.id)
    db.add(obj)
    db.flush()
    write_audit(db, request, user, "create", "quota", str(obj.id), new_value=body.model_dump(), detail=f"新增配额 {body.batch_no or obj.id}(数量 {body.quantity})")
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/quotas/{quota_id}", response_model=QuotaOut)
def update_quota(
    quota_id: int,
    body: QuotaUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    obj = db.get(SupplierQuota, quota_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="配额不存在")
    sup = db.get(Supplier, obj.supplier_id)
    if sup is None or not can_access_entity(db, user, "supplier", sup.owner_id):
        raise HTTPException(status_code=404, detail="记录不存在或无权访问")
    changes = body.model_dump(exclude_unset=True)
    if changes.get("status") and changes["status"] not in QUOTA_STATUSES:
        raise HTTPException(status_code=400, detail="配额状态不合法")
    fields = ["product_line_id", "batch_no", "quantity", "used_quantity", "quota_start_at", "quota_end_at", "status", "remark"]
    old = _snapshot(obj, fields)
    for f, v in changes.items():
        setattr(obj, f, v)
    new = _snapshot(obj, fields)
    write_audit(db, request, user, "update", "quota", str(obj.id), old_value=old, new_value=new, detail=f"更新配额 {obj.batch_no}")
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/quotas/{quota_id}")
def delete_quota(quota_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    obj = db.get(SupplierQuota, quota_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="配额不存在")
    sup = db.get(Supplier, obj.supplier_id)
    if sup is None or not can_access_entity(db, user, "supplier", sup.owner_id):
        raise HTTPException(status_code=404, detail="记录不存在或无权访问")
    old = _snapshot(obj, ["batch_no", "quantity", "status"])
    write_audit(db, request, user, "delete", "quota", str(obj.id), old_value=old, detail=f"删除配额 {obj.batch_no}")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ================= 中间层 =================
MIDDLE_FIELDS = [
    "name", "credit_code", "entity_nature", "layer_no", "reg_location", "registered_capital",
    "contact_info", "purposes", "fee_rate", "settlement", "coop_status", "credit_rating",
    "risk_notes", "remark",
]


@router.get("/middles", response_model=list[MiddleOut])
def list_middles(keyword: str = "", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(MiddleLayer)
    q = apply_visibility(q, MiddleLayer, db, user, "middle")
    if keyword:
        q = q.filter(MiddleLayer.name.like(f"%{keyword}%"))
    return q.order_by(MiddleLayer.updated_at.desc()).all()


@router.post("/middles", response_model=MiddleOut, status_code=201)
def create_middle(body: MiddleIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    obj = MiddleLayer(**body.model_dump(), owner_id=user.id, last_editor_id=user.id)
    db.add(obj)
    db.flush()
    write_audit(db, request, user, "create", "middle", str(obj.id), new_value=body.model_dump(), detail=f"创建中间层 {body.name}")
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/middles/{middle_id}", response_model=MiddleOut)
def update_middle(
    middle_id: int,
    body: MiddleUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    obj = _entity_or_404(db, MiddleLayer, middle_id, user, "middle")
    _check_version(obj, body.version)
    changes = body.model_dump(exclude_unset=True)
    changes.pop("version", None)
    old = _snapshot(obj, MIDDLE_FIELDS)
    for f, v in changes.items():
        setattr(obj, f, v)
    obj.version += 1
    obj.last_editor_id = user.id
    new = _snapshot(obj, MIDDLE_FIELDS)
    write_audit(db, request, user, "update", "middle", str(obj.id), old_value=old, new_value=new, detail=f"更新中间层 {obj.name}")
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/middles/{middle_id}")
def delete_middle(middle_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    obj = _entity_or_404(db, MiddleLayer, middle_id, user, "middle")
    old = _snapshot(obj, MIDDLE_FIELDS)
    write_audit(db, request, user, "delete", "middle", str(obj.id), old_value=old, detail=f"删除中间层 {obj.name}")
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ================= 沟通记录(只增不改) =================
@router.get("/communications", response_model=list[CommunicationOut])
def list_communications(
    entity_type: str,
    entity_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if entity_type not in ("supplier", "customer", "middle"):
        raise HTTPException(status_code=400, detail="主体类型不合法")
    owner_id = None
    if entity_type == "supplier":
        obj = db.get(Supplier, entity_id)
    elif entity_type == "middle":
        obj = db.get(MiddleLayer, entity_id)
    else:
        from ..entities import Customer

        obj = db.get(Customer, entity_id)
    if obj is not None:
        owner_id = obj.owner_id
    if owner_id is None or not can_access_entity(db, user, entity_type, owner_id):
        raise HTTPException(status_code=404, detail="记录不存在或无权访问")
    return (
        db.query(Communication)
        .filter(Communication.entity_type == entity_type, Communication.entity_id == entity_id)
        .order_by(Communication.comm_time.desc(), Communication.id.desc())
        .all()
    )


@router.post("/communications", response_model=CommunicationOut, status_code=201)
def create_communication(
    body: CommunicationIn,
    request: Request,
    entity_type: str = "supplier",
    entity_id: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..entities import Customer

    if entity_type not in ("supplier", "customer", "middle"):
        raise HTTPException(status_code=400, detail="主体类型不合法")
    cls = {"supplier": Supplier, "customer": Customer, "middle": MiddleLayer}[entity_type]
    obj = db.get(cls, entity_id)
    if obj is None or not can_access_entity(db, user, entity_type, obj.owner_id):
        raise HTTPException(status_code=404, detail="记录不存在或无权访问")
    comm = Communication(
        entity_type=entity_type,
        entity_id=entity_id,
        comm_time=body.comm_time or datetime.now(timezone.utc).replace(tzinfo=None),
        channel=body.channel,
        participants=body.participants,
        content=body.content,
        next_step=body.next_step,
        follow_up_at=body.follow_up_at,
        attachment=body.attachment,
        created_by=user.id,
        created_by_name=user.display_name or user.username,
    )
    db.add(comm)
    db.flush()
    write_audit(db, request, user, "create", "communication", str(comm.id), new_value=body.model_dump(), detail=f"{entity_type}#{entity_id} 新增沟通记录")
    db.commit()
    db.refresh(comm)
    return comm
