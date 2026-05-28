# mada-webscrape

Web scraping pipeline against three Malaysian government data sources, persisted to MongoDB. Each site requires a **different scraping technique** — the project is an exercise in choosing the right tool per page rather than defaulting to the same one.

```
publicinfobanjir   →  flood        →  2,725 docs / run    (hidden JSON endpoint)
met_cuaca          →  weather      →     16 docs / run    (JS-rendered, backing JSON)
jupem_water_level  →  water_level  →    564 docs / run    (Livewire AJAX after WAF block)
                                       ───────────────
                                       3,305 docs / run
```

---

## What this project demonstrates

- **Diagnose before you code.** Each site was inspected with `curl` and `grep` before any scraper code was written. Two of the three were JS-rendered, but turned out to have HTTP-accessible JSON endpoints — no headless browser needed.
- **Switch tools when the page tells you to.** On the third site (JUPEM), the planned Selenium approach was abandoned mid-implementation when the title `"The URL you requested has been blocked"` showed up in the rendered page — the site's WAF was actively blocking headless Chrome. Pivoted to reverse-engineering the site's **Livewire AJAX protocol** via pure HTTP and never needed a browser.
- **Validate at the boundary.** Every record is pushed through a `pydantic` model before being inserted into Mongo. Empty strings, `-9999` error sentinels, and missing sensor fields are normalized to `null` at parse time, not in the database.

---

## Per-site approach

### 1. `publicinfobanjir.water.gov.my` — flood monitoring

The landing page renders an empty `<ul>` and fills it with JavaScript. Looking at the page source revealed an undocumented JSON endpoint:

```
/wp-content/themes/enlighten/data/latestreadingstrendabc.json
```

A single GET returns **2,725 stations × 40 fields** — every flood/rainfall monitoring station in all 16 Malaysian states. Selenium was dropped entirely for this site.

Sample record after parsing:

```json
{
  "station_id": "27281",
  "station_name": "Sg. Durian Burung di Durian Burung (F2)",
  "state": "KEDAH",
  "river": "Sg. Durian Burung",
  "basin": "Sungai Kedah",
  "water_level_m": 45.28,
  "water_level_status": "Danger",
  "water_level_threshold_m": 42.48,
  "water_level_exceeded_by_m": 2.8,
  "water_level_trend": "Rising",
  "water_level_observed_at": "2026-05-27T14:15:00Z",
  "rainfall_status": "No Rainfall"
}
```

### 2. `met.gov.my` — current weather + 3-hour forecasts

The homepage has a `CUACA SEMASA` carousel populated via `fetch('/json/cuaca_semasa/data.json')`. Grepped for `fetch` in the page source, found the endpoint, hit it directly. 16 weather stations (one per state) with 19-slot rainfall forecasts in 10-minute increments.

Condition icons are encoded in filename patterns (`icon-cerah-outline-dark.svg` → `cerah` = clear), so a tiny helper extracts the condition slug from the icon path.

### 3. `jupem.gov.my` — tide predictions (the interesting one)

The tide-prediction page is built with **Livewire** (Laravel's reactive frontend). Each of the 22 coastal stations has its own data, switchable via button clicks that fire AJAX.

First attempt was Selenium: load the page, click each station button, parse the rendered tables. **The site's WAF blocked headless Chrome** — the page returned `"The URL you requested has been blocked"`. Plain `curl` worked fine, though, so the WAF only flags browser-like clients.

Pivoted to talking to Livewire directly over HTTP:

1. `GET /ms/staps` — extract the CSRF token (`window.livewire_token`) and the staps component's `fingerprint` + `serverMemo` from the embedded `wire:initial-data` JSON
2. For each of stations 2–22, `POST /livewire/message/staps.staps` with a `callMethod` update invoking `selectedStesen(id, slug)`
3. Each response's `serverMemo.data` contains the new station's tide table — extracted directly without ever rendering HTML

Result: **22 stations, 564 tide predictions, ~45 seconds, zero browser overhead.**

---

## Project structure

```
mada-webscrape/
├── config/
│   └── settings.py              # pydantic-settings, loads .env
├── src/
│   ├── main.py                  # CLI: --site <name> | --all
│   ├── scrapers/
│   │   ├── base_scraper.py      # abstract lifecycle: open → fetch → parse → save → close
│   │   ├── publicinfobanjir.py  # JSON endpoint
│   │   ├── met_cuaca.py         # JSON endpoint
│   │   └── jupem_water_level.py # Livewire AJAX
│   ├── db/
│   │   ├── mongo_client.py      # connection singleton
│   │   └── repositories.py      # insert_flood / insert_weather / insert_water_level
│   ├── models/                  # pydantic record schemas per source
│   └── utils/
│       ├── driver_factory.py    # Selenium (kept as optional fallback)
│       ├── logger.py
│       └── parsers.py           # BeautifulSoup helpers
├── requirements.txt
├── .env.example
└── README.md
```

The `BaseScraper` lifecycle (`open → fetch → parse → save → close`) is the only abstraction shared across sites. `open` and `close` are no-ops by default — only scrapers that need Selenium override them.

---

## Setup

```bash
# 1. Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. MongoDB (via Docker)
docker run -d --name mada-mongo -p 27017:27017 \
  -v mada-mongo-data:/data/db \
  --restart unless-stopped \
  mongo:7

# 3. Config
cp .env.example .env
# default settings point to mongodb://localhost:27017 — no edits needed for local dev
```

---

## Run

```bash
# one site at a time
python -m src.main --site publicinfobanjir
python -m src.main --site met_cuaca
python -m src.main --site jupem_water_level

# all three sequentially
python -m src.main --all
```

Re-running **appends** to the collections so historical observations accumulate — `(station, scraped_at)` pairs are preserved. Switch to upserts in `src/db/repositories.py` if you'd rather keep one document per station.

---

## Query the data

```bash
docker exec -it mada-mongo mongosh mada
```

```js
// Stations currently in danger status
db.flood.find(
  { water_level_status: "Danger" },
  { station_name: 1, state: 1, water_level_m: 1, water_level_trend: 1 }
)

// Cities reporting rain right now
db.weather.find(
  { condition_now: "hujan" },
  { station: 1, state: 1, temperature_c: 1 }
)

// Highest predicted tide this week, per station
db.water_level.aggregate([
  { $group: { _id: "$station_name", peak_cm: { $max: "$height_cm" } } },
  { $sort: { peak_cm: -1 } }
])
```

---

## Tech stack

- **Python 3.9+** — `requests`, `beautifulsoup4`, `pydantic`, `pydantic-settings`, `python-dotenv`
- **Selenium + webdriver-manager** — kept as optional fallback in `BaseScraper`; not used by any of the three current scrapers
- **MongoDB 7** — collections per source (`flood`, `weather`, `water_level`)
- **Docker** — containerized Mongo

---

## Notes & gotchas

- **`publicinfobanjir`** — about 148 stations have no `sensor_type` value and ~445 stations have `Error` status. These are real upstream data quality issues; we store as-is and let downstream queries filter.
- **`met_cuaca`** — Ipoh occasionally reports `0°C`. This is an upstream sensor issue, stored as-is. Filter with `temperature_c > 5` if needed.
- **`jupem`** — tide predictions are precomputed by JUPEM; the data only changes when their published schedule updates (typically weekly). A daily cron is more than enough.

---

## License

MIT.
