from abc import ABC, abstractmethod

from src.utils.logger import get_logger


class BaseScraper(ABC):
    name: str = "base"
    url: str = ""

    def __init__(self) -> None:
        self.log = get_logger(self.name)

    def open(self) -> None:
        """Initialise resources. Override if a driver/session is needed."""

    def close(self) -> None:
        """Tear down resources. Override if a driver/session was opened."""

    @abstractmethod
    def fetch(self) -> object:
        """Retrieve raw data — HTML string, JSON dict/list, whatever the site exposes."""

    @abstractmethod
    def parse(self, raw: object) -> list[dict]:
        """Turn raw data into a list of validated record dicts."""

    @abstractmethod
    def save(self, records: list[dict]) -> int:
        """Persist records to Mongo. Returns inserted count."""

    def run(self) -> int:
        try:
            self.open()
            raw = self.fetch()
            records = self.parse(raw)
            self.log.info("parsed %d records", len(records))
            inserted = self.save(records)
            self.log.info("inserted %d records", inserted)
            return inserted
        finally:
            self.close()
