import json
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from ..models.entities import VisaRoute, AppointmentStatus, AuditLog, AdminTask
from .freshness_service import compute_is_stale, stale_minutes, compute_priority, confidence_score
from .notification_service import notify

PRIORITY = {"fallback": 1, "automated": 2, "admin": 3}


def list_routes(db: Session):
    rows = db.scalars(select(VisaRoute)).all()
    return [{"country": r.country, "city": r.city, "visa_type": r.visa_type, "check_interval_minutes": r.check_interval_minutes} for r in rows]


def _ensure_task_for_stale(db: Session, country: str, city: str, visa_type: str, priority: str):
    existing = db.scalar(select(AdminTask).where(
        AdminTask.country == country,
        AdminTask.city == city,
        AdminTask.visa_type == visa_type,
        AdminTask.status.in_(['pending', 'in_progress'])
    ))
    if existing:
        return
    due = datetime.now(timezone.utc) + timedelta(hours=4 if priority == 'high' else 12)
    db.add(AdminTask(country=country, city=city, visa_type=visa_type, task_type='verify', priority=priority, status='pending', due_at=due))


def serialize_status(db: Session, r: AppointmentStatus):
    mins = stale_minutes(r.last_updated)
    stale = compute_is_stale(r.last_updated)
    priority = compute_priority(r.country, mins) if stale else 'low'
    out = {
        "country": r.country, "city": r.city, "visa_type": r.visa_type,
        "availability_status": r.availability_status,
        "next_available_date": r.next_available_date,
        "notes": r.notes,
        "freshness_label": r.freshness_label,
        "source_type": r.source_type,
        "last_updated": r.last_updated,
        "is_stale": stale,
        "priority": priority,
        "confidence_score": confidence_score(r.source_type),
        "minutes_since_update": round(mins, 1),
    }
    if stale:
        _ensure_task_for_stale(db, r.country, r.city, r.visa_type, priority)
    return out


def _notify_stale_batch(items: list[dict]):
    stale_items = [i for i in items if i.get('is_stale')]
    if not stale_items:
        return
    payload = [{"country": s['country'], "city": s['city'], "visa_type": s['visa_type'], "minutes_since_update": s['minutes_since_update']} for s in stale_items]
    notify('stale_data_batch', f'{len(stale_items)} stale visa records detected', {'items': payload})


def get_status(db: Session, country: str, visa_type: str | None):
    q = select(AppointmentStatus).where(AppointmentStatus.country == country.upper())
    if visa_type:
        q = q.where(AppointmentStatus.visa_type == visa_type.upper())
    rows = db.scalars(q).all()
    data = [serialize_status(db, r) for r in rows]
    db.commit()
    _notify_stale_batch(data)
    return data


def get_all_status(db: Session):
    data = [serialize_status(db, r) for r in db.scalars(select(AppointmentStatus)).all()]
    db.commit()
    _notify_stale_batch(data)
    return data


def get_tasks(db: Session):
    rows = db.scalars(select(AdminTask).order_by(AdminTask.created_at.desc())).all()
    return [{"id": t.id, "country": t.country, "city": t.city, "visa_type": t.visa_type, "task_type": t.task_type, "priority": t.priority, "status": t.status, "created_at": t.created_at, "due_at": t.due_at} for t in rows]


def complete_task(db: Session, task_id: int, actor: str):
    task = db.scalar(select(AdminTask).where(AdminTask.id == task_id))
    if not task:
        return None
    old = task.status
    task.status = 'completed'
    db.add(AuditLog(actor=actor, action='complete_task', target_key=f'task:{task_id}', old_value=old, new_value='completed'))
    db.commit()
    return {"id": task.id, "status": task.status}


def upsert_status(db: Session, payload: dict, actor: str, source_type: str):
    key_country = payload["country"].upper(); key_city = payload["city"]; key_visa = payload["visa_type"].upper()
    row = db.scalar(select(AppointmentStatus).where(AppointmentStatus.country==key_country, AppointmentStatus.city==key_city, AppointmentStatus.visa_type==key_visa))
    new_pri = PRIORITY.get(source_type, 1)
    if row:
        old = serialize_status(db, row)
        if PRIORITY.get(row.source_type, 1) > new_pri:
            return serialize_status(db, row), False
        row.availability_status = payload["availability_status"]
        row.next_available_date = payload.get("next_available_date")
        row.notes = payload.get("notes")
        row.freshness_label = "verified" if source_type == "admin" else "last_known"
        row.source_type = source_type
        row.last_updated = datetime.now(timezone.utc)
        newv = serialize_status(db, row)
        db.add(AuditLog(actor=actor, action='update_status', target_key=f'{key_country}:{key_city}:{key_visa}', old_value=json.dumps(old, default=str), new_value=json.dumps(newv, default=str)))
    else:
        row = AppointmentStatus(country=key_country, city=key_city, visa_type=key_visa, availability_status=payload['availability_status'], next_available_date=payload.get('next_available_date'), notes=payload.get('notes'), source_type=source_type, freshness_label='verified' if source_type=='admin' else 'last_known')
        db.add(row); db.flush()
        db.add(AuditLog(actor=actor, action='create_status', target_key=f'{key_country}:{key_city}:{key_visa}', old_value=None, new_value=json.dumps(serialize_status(db, row), default=str)))
    db.commit()
    return serialize_status(db, row), True


def last_updated(db: Session):
    return db.scalar(select(func.max(AppointmentStatus.last_updated)))
