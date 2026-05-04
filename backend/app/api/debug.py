import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..database.session import get_db
from ..core.security import RoleChecker

router = APIRouter(prefix="/api/debug", tags=["debug"])
admin_only = RoleChecker(["admin"])

@router.get("/logs")
async def get_logs(_ = Depends(admin_only)):
    """
    Returns the last 500 lines of the production log file.
    """
    log_file = "vixa_production.log"
    if not os.path.exists(log_file):
        return {"message": "Log file not found."}
    
    with open(log_file, "r") as f:
        lines = f.readlines()
        return {"logs": lines[-500:]}
