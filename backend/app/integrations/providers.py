from typing import Protocol
from dataclasses import dataclass

@dataclass
class ProviderRecord:
    country: str
    city: str
    visa_type: str
    availability_status: str
    next_available_date: str | None = None
    notes: str | None = None
    freshness_label: str = 'last_known'

class DataProvider(Protocol):
    name: str
    source_type: str
    def fetch_statuses(self) -> list[ProviderRecord]: ...

class MockProvider:
    name = 'mock_provider'
    source_type = 'fallback'
    def fetch_statuses(self) -> list[ProviderRecord]:
        return [ProviderRecord(country='GB', city='London', visa_type='TOURIST', availability_status='LIMITED', notes='seed fallback')]

class SafePublicProvider:
    name = 'safe_public_provider'
    source_type = 'automated'
    def fetch_statuses(self) -> list[ProviderRecord]:
        # Placeholder for public endpoint ingestion only (no captcha/login bypass)
        return []
