from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from scrapers.base import BaseScraper

SCRAPER_REGISTRY: list[Type["BaseScraper"]] = []

def register_scraper(cls: Type["BaseScraper"]) -> Type["BaseScraper"]:
    """Class decorator to register a concrete scraper dynamically."""
    if cls not in SCRAPER_REGISTRY:
        SCRAPER_REGISTRY.append(cls)
    return cls
