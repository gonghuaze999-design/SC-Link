from sqlalchemy.orm import Session

from ..entities import DataShare
from ..models import User

# 实体类别 → 共享范围关键字
ENTITY_SCOPE = {
    "supplier": "supplier",
    "chain": "supplier",
    "quota": "supplier",
    "customer": "customer",
    "verification": "customer",
    "middle": "middle",
    "communication": "communication",
}


def scope_of(entity_type: str) -> str:
    if entity_type == "communication":
        return "communication"
    return ENTITY_SCOPE.get(entity_type, "")


def visible_owner_ids(db: Session, user: User, entity_type: str) -> tuple[set[int], bool]:
    """返回 (可见的 owner 集合, 是否全局可见)。管理员全局可见。"""
    if user.role == "admin":
        return set(), True
    owners = {user.id}
    shares = (
        db.query(DataShare)
        .filter(
            DataShare.status == "active",
            (DataShare.requester_id == user.id) | (DataShare.target_id == user.id),
        )
        .all()
    )
    scope = scope_of(entity_type)
    for s in shares:
        other = s.target_id if s.requester_id == user.id else s.requester_id
        scopes = s.scopes or []
        if "all" in scopes or scope in scopes:
            owners.add(other)
    return owners, False


def apply_visibility(query, entity_cls, db: Session, user: User, entity_type: str):
    owners, is_admin = visible_owner_ids(db, user, entity_type)
    if is_admin:
        return query
    return query.filter(entity_cls.owner_id.in_(owners))


def can_access_entity(db: Session, user: User, entity_type: str, owner_id: int) -> bool:
    owners, is_admin = visible_owner_ids(db, user, entity_type)
    return is_admin or owner_id in owners
