# mada-webscrape

Web scraper for three Malaysian government data sources, persisted to MongoDB.

## Sources

- `publicinfobanjir` — flood info
- `met-cuaca` — weather
- `jupem-water-level` — water levels

## Stack

- BeautifulSoup + Selenium
- MongoDB (via pymongo)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in MONGO_URI etc.
```

## Run

```bash
python -m src.main --site publicinfobanjir
python -m src.main --site met_cuaca
python -m src.main --site jupem_water_level
python -m src.main --all
```
