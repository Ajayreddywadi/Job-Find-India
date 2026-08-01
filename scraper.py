# scraper.py (facade/backward compatibility wrapper)
# Forwarding all exports from config, utils, scrapers, and services packages.

from config.settings import (
    DEFAULT_TIMEOUT,
    MAX_WORKERS,
    MAX_RESULTS_PER_SOURCE,
    FUZZY_THRESHOLD,
)
from config.cities import (
    CITY_ALIASES,
    CITY_STATE_MAP,
    NEARBY_CITIES,
    _ALL_INDIAN_LOCATIONS,
    normalize_city,
    _is_indian_query,
)
from utils.helpers import (
    _clean_html,
    _truncate,
    _empty_job,
    _is_non_indian_restricted,
)
from scrapers.base import (
    BaseScraper,
    ScraperError,
    ScraperFetchError,
    ScraperParsingError,
)
from scrapers.linkedin import LinkedInScraper
from scrapers.unstop import UnstopScraper
from scrapers.himalayas import HimalayasScraper
from scrapers.jobicy import JobicyScraper
from scrapers.remotive import RemotiveScraper
from scrapers.arbeitnow import ArbeitnowScraper
from services.search_service import JobAggregator

__all__ = [
    "DEFAULT_TIMEOUT",
    "MAX_WORKERS",
    "MAX_RESULTS_PER_SOURCE",
    "FUZZY_THRESHOLD",
    "CITY_ALIASES",
    "CITY_STATE_MAP",
    "NEARBY_CITIES",
    "_ALL_INDIAN_LOCATIONS",
    "normalize_city",
    "_is_indian_query",
    "_clean_html",
    "_truncate",
    "_empty_job",
    "_is_non_indian_restricted",
    "BaseScraper",
    "ScraperError",
    "ScraperFetchError",
    "ScraperParsingError",
    "LinkedInScraper",
    "UnstopScraper",
    "HimalayasScraper",
    "JobicyScraper",
    "RemotiveScraper",
    "ArbeitnowScraper",
    "JobAggregator",
]
