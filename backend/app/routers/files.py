import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..entities import MiddleLayer, Order, OverseasChain, StoredFile, Supplier
from ..entities import Customer
from ..models import User
from ..services.audit import write_audit
from ..services.visibility import can_access_entity

router = APIRouter(prefix="/files", tags=["files"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".pdf", ".mp4", ".mov"}
VIDEO_EXT = {".mp4", ".mov"}
MAX_VIDEO = 200 * 1024 * 1024
MAX_OTHER = 20 * 1024 * 1024

ENTITY_CLASSES = {
    "supplier": Supplier,
    "customer": Customer,
    "middle": MiddleLayer,
    "chain": OverseasChain,
    "order": Order,
}


@router.post("")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    entity_type: str = Form(""),
    entity_id: int = Form(0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "")[1].lower()[:10]
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="不支持的文件格式(支持 jpg/png/webp/pdf/mp4/mov)")
    limit = MAX_VIDEO if ext in VIDEO_EXT else MAX_OTHER
    entity_type = entity_type or request.query_params.get("entity_type", "")
    entity_id = entity_id or int(request.query_params.get("entity_id", 0) or 0)

    stored = uuid.uuid4().hex + ext
    path = UPLOAD_DIR / stored
    size = 0
    with path.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                path.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail="文件超出大小限制(视频 200MB,其他 20MB)")
            out.write(chunk)

    rec = StoredFile(
        stored_name=stored,
        original_name=file.filename or "",
        uploader_id=user.id,
        entity_type=entity_type,
        entity_id=entity_id,
        size=size,
    )
    db.add(rec)
    db.flush()
    write_audit(db, request, user, "create", "file", str(rec.id), new_value={"name": file.filename, "size": size}, detail=f"上传文件 {file.filename}")
    db.commit()
    db.refresh(rec)
    return {"id": rec.id, "stored_name": stored, "original_name": file.filename, "size": size}


@router.get("/{stored_name}")
def download_file(
    stored_name: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    safe_name = Path(stored_name).name
    rec = db.query(StoredFile).filter(StoredFile.stored_name == safe_name).first()
    if rec is None:
        raise HTTPException(status_code=404, detail="文件不存在")

    allowed = user.role == "admin" or rec.uploader_id == user.id
    if not allowed and rec.entity_type in ENTITY_CLASSES:
        obj = db.get(ENTITY_CLASSES[rec.entity_type], rec.entity_id)
        if obj is not None:
            allowed = can_access_entity(db, user, rec.entity_type, obj.owner_id)
    if not allowed:
        raise HTTPException(status_code=403, detail="无权下载该文件")

    path = UPLOAD_DIR / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="文件已丢失")
    write_audit(db, request, user, "download", "file", str(rec.id), detail=f"下载文件 {rec.original_name}")
    db.commit()
    return FileResponse(path, filename=rec.original_name)
