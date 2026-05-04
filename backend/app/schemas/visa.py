from pydantic import BaseModel
from datetime import datetime

class VisaStatusOut(BaseModel):
    country: str
    city: str
    visa_type: str
    availability_status: str
    freshness_label: str
    last_updated: datetime

class Envelope(BaseModel):
    success: bool
    data: dict | list
    error: str | None = None
    meta: dict | None = None
