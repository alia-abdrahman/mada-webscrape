from __future__ import annotations

import argparse
import sys

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.jupem_water_level import JupemWaterLevelScraper
from src.scrapers.met_cuaca import MetCuacaScraper
from src.scrapers.publicinfobanjir import PublicInfoBanjirScraper
from src.utils.logger import get_logger

SCRAPERS: dict[str, type[BaseScraper]] = {
    PublicInfoBanjirScraper.name: PublicInfoBanjirScraper,
    MetCuacaScraper.name: MetCuacaScraper,
    JupemWaterLevelScraper.name: JupemWaterLevelScraper,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="mada-webscrape runner")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--site", choices=sorted(SCRAPERS.keys()))
    group.add_argument("--all", action="store_true")
    args = parser.parse_args()

    log = get_logger("main")
    targets = list(SCRAPERS.values()) if args.all else [SCRAPERS[args.site]]

    total = 0
    for scraper_cls in targets:
        log.info("running %s", scraper_cls.name)
        total += scraper_cls().run()

    log.info("done, inserted %d records total", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
