from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FloodRecord(BaseModel):
    station_id: str
    station_name: str
    state: str
    district: str | None = None
    river: str | None = None
    basin: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    sensor_type: str | None = None

    water_level_m: float | None = None
    water_level_status: str | None = None
    water_level_threshold_m: float | None = None
    water_level_exceeded_by_m: float | None = None
    water_level_trend: str | None = None
    water_level_observed_at: datetime | None = None

    rainfall_status: str | None = None
    rainfall_observed_at: datetime | None = None

    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = "publicinfobanjir"
