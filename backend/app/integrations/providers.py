from typing import Protocol
from dataclasses import dataclass

@dataclass
class ProviderRecord:
    country: str
    city: str
    visa_type: str
    availability_status: str
    freshness_label: str = 'last_known'

class DataProvider(Protocol):
    name: str
    def fetch_statuses(self) -> list[ProviderRecord]: ...

class MockProvider:
    name = 'mock_provider'
    def fetch_statuses(self) -> list[ProviderRecord]:
        return [ProviderRecord(country='FR', city='Paris', visa_type='TOURIST', availability_status='LIMITED')]

class ManualProvider:
    name = 'manual_provider'
    def __init__(self, rows: list[dict]):
        self.rows = rows
    def fetch_statuses(self) -> list[ProviderRecord]:
        return [ProviderRecord(**r) for r in self.rows]
