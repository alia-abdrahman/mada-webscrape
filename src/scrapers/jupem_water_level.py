from __future__ import annotations

import json
import re
from datetime import datetime
from html import unescape
from typing import Any

import requests

from config import settings
from src.db.repositories import insert_water_level
from src.models.water_level_record import WaterLevelRecord

from .base_scraper import BaseScraper

STATIONS: list[tuple[int, str, str]] = [
    (1, "pulau-langkawi", "Pulau Langkawi"),
    (2, "pulau-pinang", "Pulau Pinang"),
    (3, "lumut", "Lumut"),
    (4, "pelabuhan-kelang", "Pelabuhan Kelang"),
    (5, "tanjung-keling", "Tanjung Keling"),
    (6, "kukup", "Kukup"),
    (7, "johor-bahru", "Johor Bahru"),
    (8, "tanjung-sedili", "Tanjung Sedili"),
    (9, "pulau-tioman", "Pulau Tioman"),
    (10, "tanjung-gelang", "Tanjung Gelang"),
    (11, "cendering", "Cendering"),
    (12, "geting", "Geting"),
    (13, "pulau-lakei", "Pulau Lakei"),
    (14, "sejingkat", "Sejingkat"),
    (15, "bintulu", "Bintulu"),
    (16, "miri", "Miri"),
    (17, "kota-kinabalu", "Kota Kinabalu"),
    (18, "kudat", "Kudat"),
    (19, "sandakan", "Sandakan"),
    (20, "lahad-datu", "Lahad Datu"),
    (21, "tawau", "Tawau"),
    (22, "labuan", "Labuan"),
]

STESEN_KEYS = ("stesen", "stesen1", "stesen2", "stesen3", "stesen4", "stesen5", "stesen6")

CSRF_RE = re.compile(r"window\.livewire_token\s*=\s*'([^']+)'")
INITIAL_DATA_RE = re.compile(r'wire:initial-data="([^"]+)"')


class JupemWaterLevelScraper(BaseScraper):
    name = "jupem_water_level"

    def __init__(self) -> None:
        super().__init__()
        self.session: requests.Session | None = None

    @property
    def page_url(self) -> str:
        return settings.jupem_water_level_url.rstrip("/") + settings.jupem_staps_path

    @property
    def livewire_url(self) -> str:
        return settings.jupem_water_level_url.rstrip("/") + "/livewire/message/staps.staps"

    def open(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        })

    def close(self) -> None:
        if self.session is not None:
            self.session.close()
            self.session = None

    def fetch(self) -> list[dict[str, Any]]:
        assert self.session is not None
        self.log.info("loading %s", self.page_url)
        resp = self.session.get(self.page_url, timeout=settings.default_timeout)
        resp.raise_for_status()
        html = resp.text

        csrf_match = CSRF_RE.search(html)
        if not csrf_match:
            raise RuntimeError("could not find Livewire CSRF token")
        csrf = csrf_match.group(1)

        initial = self._extract_initial_data(html)
        if initial is None:
            raise RuntimeError("could not find staps.staps component initial data")

        fingerprint = initial["fingerprint"]
        server_memo = initial["serverMemo"]

        all_records: list[dict[str, Any]] = []

        first_id, first_slug, first_name = STATIONS[0]
        first_data = server_memo["data"]
        self.log.info("station 1/%d - %s", len(STATIONS), first_name)
        all_records.extend(self._extract_records(first_data, first_id, first_slug, first_name))

        for idx, (station_id, slug, name) in enumerate(STATIONS[1:], start=2):
            self.log.info("station %d/%d - %s", idx, len(STATIONS), name)
            server_memo = self._call_livewire(
                csrf=csrf,
                fingerprint=fingerprint,
                server_memo=server_memo,
                method="selectedStesen",
                params=[station_id, slug],
            )
            data = server_memo.get("data") or {}
            all_records.extend(self._extract_records(data, station_id, slug, name))

        return all_records

    def _extract_initial_data(self, html: str) -> dict | None:
        for raw in INITIAL_DATA_RE.findall(html):
            try:
                obj = json.loads(unescape(raw))
            except json.JSONDecodeError:
                continue
            if obj.get("fingerprint", {}).get("name") == "staps.staps":
                return obj
        return None

    def _call_livewire(
        self,
        csrf: str,
        fingerprint: dict[str, Any],
        server_memo: dict[str, Any],
        method: str,
        params: list[Any],
    ) -> dict[str, Any]:
        assert self.session is not None
        payload = {
            "fingerprint": fingerprint,
            "serverMemo": server_memo,
            "updates": [{
                "type": "callMethod",
                "payload": {
                    "id": f"{method}-{params[0]}",
                    "method": method,
                    "params": params,
                },
            }],
        }
        resp = self.session.post(
            self.livewire_url,
            headers={
                "X-CSRF-TOKEN": csrf,
                "X-Livewire": "true",
                "Content-Type": "application/json",
                "Accept": "text/html, application/xhtml+xml",
                "Referer": self.page_url,
            },
            json=payload,
            timeout=settings.default_timeout,
        )
        resp.raise_for_status()
        body = resp.json()
        merged = dict(server_memo)
        merged.update(body.get("serverMemo") or {})
        data = dict(merged.get("data") or {})
        data.update((body.get("serverMemo") or {}).get("data") or {})
        merged["data"] = data
        return merged

    def _extract_records(
        self,
        data: dict[str, Any],
        station_id: int,
        slug: str,
        name: str,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for key in STESEN_KEYS:
            entries = data.get(key) or []
            for entry in entries:
                try:
                    tide_at = datetime(
                        int(entry["STAP_TAHUN"]),
                        int(entry["STAP_BULAN"]),
                        int(entry["STAP_TARIKH"]),
                        int(entry["STAP_JAM"]),
                        int(entry["STAP_MINIT"]),
                    )
                    height_cm = int(entry["STAP_KETINGGIAN"])
                except (KeyError, TypeError, ValueError):
                    continue
                rows.append({
                    "station_id": station_id,
                    "station_slug": slug,
                    "station_name": name,
                    "tide_at": tide_at,
                    "height_cm": height_cm,
                })
        return rows

    def parse(self, raw: object) -> list[dict]:
        assert isinstance(raw, list)
        records: list[dict] = []
        for row in raw:
            try:
                records.append(WaterLevelRecord(**row).model_dump())
            except Exception as exc:
                self.log.warning("skipping row %s: %s", row, exc)
        return records

    def save(self, records: list[dict]) -> int:
        return insert_water_level(records)
