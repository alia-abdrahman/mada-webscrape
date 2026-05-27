from __future__ import annotations

from datetime import datetime
from typing import Any

import requests

from config import settings
from src.db.repositories import insert_flood
from src.models.flood_record import FloodRecord

from .base_scraper import BaseScraper

ERROR_SENTINEL = "-9999"
DATETIME_FMT = "%d/%m/%Y %H:%M"


def _to_float(value: str | None) -> float | None:
    if value is None or value == "" or value == ERROR_SENTINEL:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), DATETIME_FMT)
    except ValueError:
        return None


def _clean_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _has_wl_sensor(sensor_type: str | None) -> bool:
    return bool(sensor_type) and "WL" in sensor_type

def _has_rf_sensor(sensor_type: str | None) -> bool:
    return bool(sensor_type) and "RF" in sensor_type


class PublicInfoBanjirScraper(BaseScraper):
    name = "publicinfobanjir"

    @property
    def url(self) -> str:
        return settings.publicinfobanjir_url.rstrip("/") + settings.publicinfobanjir_json_path

    def fetch(self) -> list[dict[str, Any]]:
        self.log.info("fetching %s", self.url)
        response = requests.get(
            self.url,
            headers={"User-Agent": "Mozilla/5.0 (mada-webscrape)"},
            timeout=settings.default_timeout,
        )
        response.raise_for_status()
        return response.json()

    def parse(self, raw: object) -> list[dict]:
        assert isinstance(raw, list)
        records: list[dict] = []
        for row in raw:
            record = self._row_to_record(row)
            if record is not None:
                records.append(record.model_dump())
        return records

    def _row_to_record(self, row: dict[str, Any]) -> FloodRecord | None:
        station_id = _clean_str(row.get("a"))
        station_name = _clean_str(row.get("b"))
        state = _clean_str(row.get("f"))
        if not station_id or not station_name or not state:
            return None

        sensor_type = _clean_str(row.get("i"))

        wl_fields: dict[str, Any] = {}
        if _has_wl_sensor(sensor_type):
            wl_fields = {
                "water_level_m": _to_float(row.get("m")),
                "water_level_status": _clean_str(row.get("n")),
                "water_level_threshold_m": _to_float(row.get("o")),
                "water_level_exceeded_by_m": _to_float(row.get("p")),
                "water_level_trend": _clean_str(row.get("s")),
                "water_level_observed_at": _to_datetime(row.get("q")),
            }

        rf_fields: dict[str, Any] = {}
        if _has_rf_sensor(sensor_type):
            rf_fields = {
                "rainfall_status": _clean_str(row.get("x")),
                "rainfall_observed_at": _to_datetime(row.get("y")),
            }

        return FloodRecord(
            station_id=station_id,
            station_name=station_name,
            state=state.rstrip(),
            district=_clean_str(row.get("e")),
            river=_clean_str(row.get("g")),
            basin=_clean_str(row.get("h")),
            latitude=_to_float(row.get("c")),
            longitude=_to_float(row.get("d")),
            sensor_type=sensor_type,
            **wl_fields,
            **rf_fields,
        )

    def save(self, records: list[dict]) -> int:
        return insert_flood(records)
