from scrapers.base import BaseScraper, SHARED_SESSION
from scrapers.registry import SCRAPER_REGISTRY, register_scraper
from scrapers.himalayas import HimalayasScraper
from scrapers.jobicy import JobicyScraper
from scrapers.linkedin import LinkedInScraper
from scrapers.remotive import RemotiveScraper
from scrapers.unstop import UnstopScraper
from scrapers.arbeitnow import ArbeitnowScraper

__all__ = [
    "BaseScraper",
    "SHARED_SESSION",
    "SCRAPER_REGISTRY",
    "register_scraper",
    "HimalayasScraper",
    "JobicyScraper",
    "LinkedInScraper",
    "RemotiveScraper",
    "UnstopScraper",
    "ArbeitnowScraper",
]
