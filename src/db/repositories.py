from __future__ import annotations

from typing import Iterable

from config import settings

from .mongo_client import get_db


def _insert_many(collection_name: str, records: Iterable[dict]) -> int:
    records = list(records)
    if not records:
        return 0
    result = get_db()[collection_name].insert_many(records)
    return len(result.inserted_ids)


def insert_flood(records: Iterable[dict]) -> int:
    return _insert_many(settings.flood_collection, records)


def insert_weather(records: Iterable[dict]) -> int:
    return _insert_many(settings.weather_collection, records)


def insert_water_level(records: Iterable[dict]) -> int:
    return _insert_many(settings.water_level_collection, records)
