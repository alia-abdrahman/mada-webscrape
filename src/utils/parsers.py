from __future__ import annotations

from bs4 import BeautifulSoup, Tag


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def clean_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.split())


def parse_table(table: Tag) -> list[dict[str, str]]:
    headers = [clean_text(th.get_text()) for th in table.select("thead th")]
    if not headers:
        first_row = table.find("tr")
        if first_row is None:
            return []
        headers = [clean_text(cell.get_text()) for cell in first_row.find_all(["th", "td"])]

    rows: list[dict[str, str]] = []
    for tr in table.select("tbody tr") or table.find_all("tr")[1:]:
        cells = [clean_text(td.get_text()) for td in tr.find_all(["td", "th"])]
        if not cells:
            continue
        rows.append(dict(zip(headers, cells)))
    return rows
