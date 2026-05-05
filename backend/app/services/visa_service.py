from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..models.entities import SlotEvent

async def list_routes(db: AsyncSession):
    rows = (await db.execute(select(SlotEvent))).scalars().all()
    # Unique routes by country/center
    routes = {}
    for r in rows:
        key = (r.country, r.center)
        if key not in routes:
            routes[key] = {"country": r.country, "center": r.center, "visa_type": r.visa_type}
    return list(routes.values())

async def get_status(db: AsyncSession, origin: str, destination: str | None):
    q = select(SlotEvent).where(SlotEvent.country == origin.upper())
    if destination:
        q = q.where(SlotEvent.center == destination.upper())
    rows = (await db.execute(q)).scalars().all()
    return rows

async def last_updated(db: AsyncSession):
    return (await db.execute(select(func.max(SlotEvent.last_updated)))).scalar()
