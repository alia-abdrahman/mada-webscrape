from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WaterLevelRecord(BaseModel):
    station_id: int
    station_slug: str
    station_name: str
    tide_at: datetime
    height_cm: int
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = "jupem_water_level"
