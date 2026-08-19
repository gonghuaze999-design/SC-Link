"""定时任务:配额状态自动流转、看板到期自动关停(每小时)。"""
from datetime import date, datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from .database import SessionLocal
from .entities import Publication, SupplierQuota

_scheduler: BackgroundScheduler | None = None


def _today() -> date:
    return datetime.now(timezone.utc).date()


def refresh_quotas() -> None:
    db = SessionLocal()
    try:
        today = _today()
        for q in db.query(SupplierQuota).all():
            new_status = None
            if q.used_quantity >= q.quantity > 0:
                new_status = "used_up"
            elif q.quota_end_at and q.quota_end_at < today:
                new_status = "expired"
            elif q.status in ("used_up", "expired") and not (
                q.quota_end_at and q.quota_end_at < today
            ):
                new_status = "available"
            if new_status and new_status != q.status:
                q.status = new_status
        db.commit()
    finally:
        db.close()


def close_expired_publications() -> None:
    db = SessionLocal()
    try:
        today = _today()
        rows = (
            db.query(Publication)
            .filter(Publication.status == "active", Publication.validity_until.isnot(None))
            .all()
        )
        for p in rows:
            if p.validity_until and p.validity_until < today:
                p.status = "closed"
        db.commit()
    finally:
        db.close()


def run_duty_job() -> None:
    from .services.duty import run_duty_all

    run_duty_all()


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    sched = BackgroundScheduler(timezone="Asia/Shanghai")
    sched.add_job(refresh_quotas, "interval", hours=1, id="refresh_quotas", coalesce=True)
    sched.add_job(close_expired_publications, "interval", hours=1, id="close_pubs", coalesce=True)
    sched.add_job(run_duty_job, "interval", hours=1, id="duty_robot", coalesce=True, max_instances=1)
    sched.start()
    _scheduler = sched
