from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import requests

from config import settings
from src.db.repositories import insert_weather
from src.models.weather_record import WeatherRecord

from .base_scraper import BaseScraper

TEMP_RE = re.compile(r"-?\d+(?:\.\d+)?")
ICON_PREFIX = "icon-"
ICON_OUTLINE_SUFFIX = "-outline-dark"


def _parse_temperature(value: str | None) -> float | None:
    if not value:
        return None
    match = TEMP_RE.search(value)
    return float(match.group()) if match else None


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.replace(" UTC", "").strip()
    try:
        return datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _icon_to_condition(icon_path: str | None) -> str | None:
    if not icon_path:
        return None
    stem = icon_path.rsplit("/", 1)[-1].removesuffix(".svg")
    if stem.startswith(ICON_PREFIX):
        stem = stem[len(ICON_PREFIX):]
    if stem.endswith(ICON_OUTLINE_SUFFIX):
        stem = stem[: -len(ICON_OUTLINE_SUFFIX)]
    return stem or None


class MetCuacaScraper(BaseScraper):
    name = "met_cuaca"

    @property
    def url(self) -> str:
        return settings.met_cuaca_url.rstrip("/") + settings.met_cuaca_json_path

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

    def _row_to_record(self, row: dict[str, Any]) -> WeatherRecord | None:
        station_code = row.get("code")
        station = row.get("station")
        state = row.get("state")
        if not station_code or not station or not state:
            return None

        forecast = {
            time_label: condition
            for time_label, icon_path in (row.get("rainfall") or {}).items()
            if (condition := _icon_to_condition(icon_path)) is not None
        }

        return WeatherRecord(
            station_code=station_code,
            station=station,
            state=state,
            temperature_c=_parse_temperature(row.get("temp")),
            condition_now=_icon_to_condition(row.get("icon")),
            forecast=forecast,
            observed_at=_parse_timestamp(row.get("timestamp")),
        )

    def save(self, records: list[dict]) -> int:
        return insert_weather(records)
