from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..entities import CapitalVerification, Customer
from ..models import User
from ..schemas_entities import (
    CustomerIn,
    CustomerOut,
    CustomerUpdate,
    VerificationIn,
    VerificationOut,
    VerificationReview,
)
from ..services.audit import write_audit
from ..services.visibility import apply_visibility, can_access_entity

router = APIRouter(tags=["customers"])

CUSTOMER_FIELDS = [
    "name", "credit_code", "reg_location", "established_at", "registered_capital", "industry",
    "contacts", "remark", "license_file", "account_info", "invoice_info", "intent_modes",
    "intent_products", "intent_quantity", "budget_range", "expected_deal_at", "goods_preference",
    "customer_type", "purpose", "decision_chain", "payment_habit", "risk_preference",
    "value_grade", "tags",
]

VERIFY_TYPES = ("video", "balance_photo", "bank_certificate", "guarantee_letter")


def _customer_or_404(db: Session, customer_id: int, user: User) -> Customer:
    obj = db.get(Customer, customer_id)
    if obj is None or not can_access_entity(db, user, "customer", obj.owner_id):
        raise HTTPException(status_code=404, detail="记录不存在或无权访问")
    return obj


def _check_version(obj, version: int) -> None:
    if obj.version != version:
        raise HTTPException(
            status_code=409,
            detail="数据已被他人更新(当前版本 v%d,你基于 v%d 编辑),请刷新后重试" % (obj.version, version),
        )


@router.get("/customers", response_model=list[CustomerOut])
def list_customers(
    keyword: str = "",
    verified: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Customer)
    q = apply_visibility(q, Customer, db, user, "customer")
    if keyword:
        q = q.filter(Customer.name.like(f"%{keyword}%"))
    if verified:
        sub_ids = (
            db.query(CapitalVerification.customer_id)
            .filter(CapitalVerification.review_status == "approved")
            .subquery()
        )
        if verified == "yes":
            q = q.filter(Customer.id.in_(sub_ids))
        else:
            q = q.filter(~Customer.id.in_(sub_ids))
    return q.order_by(Customer.updated_at.desc()).all()


@router.post("/customers", response_model=CustomerOut, status_code=201)
def create_customer(body: CustomerIn, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    obj = Customer(**body.model_dump(), owner_id=user.id, last_editor_id=user.id)
    db.add(obj)
    db.flush()
    write_audit(db, request, user, "create", "customer", str(obj.id), new_value=body.model_dump(), detail=f"创建客户 {body.name}")
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/customers/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _customer_or_404(db, customer_id, user)


@router.patch("/customers/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: int,
    body: CustomerUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    obj = _customer_or_404(db, customer_id, user)
    _check_version(obj, body.version)
    changes = body.model_dump(exclude_unset=True)
    changes.pop("version", None)
    old = {f: getattr(obj, f) for f in CUSTOMER_FIELDS}
    for f, v in changes.items():
        setattr(obj, f, v)
    obj.version += 1
    obj.last_editor_id = user.id
    new = {f: getattr(obj, f) for f in CUSTOMER_FIELDS}
    write_audit(db, request, user, "update", "customer", str(obj.id), old_value=old, new_value=new, detail=f"更新客户 {obj.name}")
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    obj = _customer_or_404(db, customer_id, user)
    old = {f: getattr(obj, f) for f in CUSTOMER_FIELDS}
    write_audit(db, request, user, "delete", "customer", str(obj.id), old_value=old, detail=f"删除客户 {obj.name}")
    db.query(CapitalVerification).filter(CapitalVerification.customer_id == obj.id).delete()
    db.delete(obj)
    db.commit()
    return {"ok": True}


# ================= 验资材料 =================
@router.get("/customers/{customer_id}/verifications", response_model=list[VerificationOut])
def list_verifications(customer_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _customer_or_404(db, customer_id, user)
    return (
        db.query(CapitalVerification)
        .filter(CapitalVerification.customer_id == customer_id)
        .order_by(CapitalVerification.id.desc())
        .all()
    )


@router.post("/customers/{customer_id}/verifications", response_model=VerificationOut, status_code=201)
def create_verification(
    customer_id: int,
    body: VerificationIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _customer_or_404(db, customer_id, user)
    if body.verify_type not in VERIFY_TYPES:
        raise HTTPException(status_code=400, detail="验资方式不合法")
    obj = CapitalVerification(**body.model_dump(), customer_id=customer_id, uploaded_by=user.id)
    db.add(obj)
    db.flush()
    write_audit(db, request, user, "create", "verification", str(obj.id), new_value=body.model_dump(), detail=f"客户#{customer_id} 上传验资材料({body.verify_type})")
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/verifications/{vid}", response_model=VerificationOut)
def review_verification(
    vid: int,
    body: VerificationReview,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    obj = db.get(CapitalVerification, vid)
    if obj is None:
        raise HTTPException(status_code=404, detail="材料不存在")
    cust = db.get(Customer, obj.customer_id)
    if cust is None or not can_access_entity(db, user, "customer", cust.owner_id):
        raise HTTPException(status_code=404, detail="记录不存在或无权访问")
    obj.review_status = body.review_status
    obj.review_note = body.review_note
    obj.reviewed_by = user.id
    obj.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    write_audit(db, request, user, "update", "verification", str(obj.id), old_value={"review_status": "pending"}, new_value={"review_status": body.review_status, "note": body.review_note}, detail=f"验资终审:{body.review_status}")
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/verifications/{vid}")
def delete_verification(vid: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    obj = db.get(CapitalVerification, vid)
    if obj is None:
        raise HTTPException(status_code=404, detail="材料不存在")
    cust = db.get(Customer, obj.customer_id)
    if cust is None or not can_access_entity(db, user, "customer", cust.owner_id):
        raise HTTPException(status_code=404, detail="记录不存在或无权访问")
    old = {"verify_type": obj.verify_type, "file_name": obj.file_name}
    write_audit(db, request, user, "delete", "verification", str(obj.id), old_value=old, detail=f"删除验资材料 {obj.file_name}")
    db.delete(obj)
    db.commit()
    return {"ok": True}
