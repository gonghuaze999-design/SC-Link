from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..entities import Publication
from ..models import User
from ..schemas_entities import (
    ParseRequest,
    PublicationIn,
    PublicationOut,
    PublicationUpdate,
)
from ..services.ai_gateway import ai_enabled, extract_publication_fields
from ..services.audit import write_audit

router = APIRouter(prefix="/publications", tags=["publications"])


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _visible_q(db: Session, q, user: User):
    if user.role == "admin":
        return q
    return q.filter((Publication.visibility == "public") | (Publication.user_id == user.id))


@router.get("", response_model=list[PublicationOut])
def list_publications(
    type: str = "",
    status: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Publication)
    q = _visible_q(db, q, user)
    if type:
        q = q.filter(Publication.type == type)
    if status:
        q = q.filter(Publication.status == status)
    rows = q.order_by(Publication.id.desc()).limit(200).all()
    return rows


@router.post("", response_model=PublicationOut, status_code=201)
def create_publication(
    body: PublicationIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.validity_until and body.validity_until < _today():
        raise HTTPException(status_code=400, detail="有效期不能早于今天")
    if body.product_line_id is not None:
        from ..entities import ProductLine

        if db.get(ProductLine, body.product_line_id) is None:
            raise HTTPException(status_code=400, detail="产品线不存在")
    pub = Publication(**body.model_dump(), user_id=user.id)
    db.add(pub)
    db.flush()
    write_audit(db, request, user, "create", "publication", str(pub.id), new_value=body.model_dump(), detail=f"发布看板「{body.title}」({body.type}/{body.visibility})")
    db.commit()
    db.refresh(pub)
    return pub


@router.patch("/{pub_id}", response_model=PublicationOut)
def update_publication(
    pub_id: int,
    body: PublicationUpdate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pub = db.get(Publication, pub_id)
    if pub is None or (pub.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="发布不存在或无权操作")
    changes = body.model_dump(exclude_unset=True)
    old = {"title": pub.title, "status": pub.status, "visibility": pub.visibility, "validity_until": str(pub.validity_until)}
    for f, v in changes.items():
        setattr(pub, f, v)
    new = {"title": pub.title, "status": pub.status, "visibility": pub.visibility, "validity_until": str(pub.validity_until)}
    write_audit(db, request, user, "update", "publication", str(pub.id), old_value=old, new_value=new, detail=f"更新看板「{pub.title}」")
    db.commit()
    db.refresh(pub)
    return pub


@router.delete("/{pub_id}")
def delete_publication(pub_id: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    pub = db.get(Publication, pub_id)
    if pub is None or (pub.user_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=404, detail="发布不存在或无权操作")
    old = {"title": pub.title, "type": pub.type}
    write_audit(db, request, user, "delete", "publication", str(pub.id), old_value=old, detail=f"删除看板「{pub.title}」")
    db.delete(pub)
    db.commit()
    return {"ok": True}


@router.post("/parse")
def parse_publication(body: ParseRequest, user: User = Depends(get_current_user)):
    if not ai_enabled():
        raise HTTPException(status_code=400, detail="未配置 Gemini API key,暂不可用(AI 网关已就绪)")
    result = extract_publication_fields(body.text)
    if result is None:
        raise HTTPException(status_code=502, detail="AI 解析失败,请稍后重试或改为手动填写")
    return result
