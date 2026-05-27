from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class WeatherRecord(BaseModel):
    station_code: str
    station: str
    state: str
    temperature_c: float | None = None
    condition_now: str | None = None
    forecast: dict[str, str] = Field(default_factory=dict)
    observed_at: datetime | None = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = "met_cuaca"
