"""原子乐观锁:条件更新,杜绝并发下的检查-后-写竞态"""
from sqlalchemy import update
from sqlalchemy.orm import Session


def conditional_update(db: Session, cls, obj_id: int, version: int, changes: dict, user_id: int) -> bool:
    """WHERE id=? AND version=? 原子更新,version+1;返回是否恰好影响 1 行"""
    result = db.execute(
        update(cls)
        .where(cls.id == obj_id, cls.version == version)
        .values(**changes, version=cls.version + 1, last_editor_id=user_id)
    )
    return result.rowcount == 1
