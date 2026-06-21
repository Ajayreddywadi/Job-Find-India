"""
scraper.py
==========
Multi-source job vacancy scraper — powered by LinkedIn, Unstop, Himalayas,
Jobicy, Remotive, and Arbeitnow.

Architecture
------------
BaseScraper (ABC)
    ├── LinkedInScraper   — LinkedIn public guest search
    ├── UnstopScraper     — Unstop jobs & internships API
    ├── HimalayasScraper  — https://himalayas.app/jobs/api  (95k+ jobs)
    ├── JobicyScraper     — https://jobicy.com/api/v2/remote-jobs
    ├── RemotiveScraper   — https://remotive.com/api/remote-jobs
    └── ArbeitnowScraper  — https://www.arbeitnow.com/api/job-board-api

JobAggregator
    Uses ThreadPoolExecutor to run all scrapers concurrently, then
    merges, deduplicates, and returns a unified list of job dicts.
    Includes smart city-fallback: exact city → nearby cities → state →
    Remote → India when no results are found.

Unified Job Schema
------------------
{
    "title":       str   — Job title
    "company":     str   — Company name
    "location":    str   — City/country or "Remote"
    "url":         str   — Direct link to listing
    "source":      str   — Scraper name e.g. "Himalayas"
    "date_posted": str   — ISO-8601 date string or ""
    "job_type":    str   — "Full-time" | "Remote" | "Part-time" | "Contract" | ""
    "tags":        str   — Comma-separated category/skill tags
    "description": str   — Short text snippet (max 300 chars)
    "salary":      str   — e.g. "USD 60,000-90,000/year" or ""
}

Author : Job Vacancy Scraper Project
Version: 2.0.0
Updated: 2026-06-16
"""

from __future__ import annotations

import abc
import datetime
import difflib
import html
import logging
import re
import textwrap
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("scraper")

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_TIMEOUT: int = 20          # seconds per HTTP request
MAX_WORKERS: int = 6               # concurrent scraper threads
MAX_RESULTS_PER_SOURCE: int = 50   # cap results per source
FUZZY_THRESHOLD: float = 0.82      # min similarity for fuzzy city match

# ── City Normalisation Data ───────────────────────────────────────────────────

# All aliases → canonical lowercase city name.
# Canonical name is what scrapers store internally; display is title-cased.
CITY_ALIASES: dict[str, str] = {
    # Bengaluru / Bangalore
    "bangalore":         "bengaluru",
    "bengaluru":         "bengaluru",
    "bengalore":         "bengaluru",
    "blr":               "bengaluru",
    # Mumbai / Bombay
    "mumbai":            "mumbai",
    "bombay":            "mumbai",
    "mum":               "mumbai",
    # Delhi / New Delhi
    "delhi":             "delhi",
    "new delhi":         "delhi",
    "ncr":               "delhi",
    # Gurugram / Gurgaon
    "gurugram":          "gurugram",
    "gurgaon":           "gurugram",
    # Hyderabad
    "hyderabad":         "hyderabad",
    "hyd":               "hyderabad",
    "secunderabad":      "hyderabad",
    # Chennai / Madras
    "chennai":           "chennai",
    "madras":            "chennai",
    # Kolkata / Calcutta
    "kolkata":           "kolkata",
    "calcutta":          "kolkata",
    # Mysuru / Mysore
    "mysuru":            "mysuru",
    "mysore":            "mysuru",
    "mysor":             "mysuru",
    "mysur":             "mysuru",
    # Kochi / Cochin
    "kochi":             "kochi",
    "cochin":            "kochi",
    "ernakulam":         "kochi",
    # Thiruvananthapuram / Trivandrum
    "thiruvananthapuram": "thiruvananthapuram",
    "trivandrum":        "thiruvananthapuram",
    "tvm":               "thiruvananthapuram",
    # Visakhapatnam / Vizag
    "visakhapatnam":     "visakhapatnam",
    "vizag":             "visakhapatnam",
    "vishakhapatnam":    "visakhapatnam",
    # Bhubaneswar
    "bhubaneswar":       "bhubaneswar",
    "bbsr":              "bhubaneswar",
    # Other common aliases
    "pune":              "pune",
    "poona":             "pune",
    "noida":             "noida",
    "ahmedabad":         "ahmedabad",
    "amdavad":           "ahmedabad",
    "jaipur":            "jaipur",
    "pink city":         "jaipur",
    "lucknow":           "lucknow",
    "chandigarh":        "chandigarh",
    "indore":            "indore",
    "coimbatore":        "coimbatore",
    "cbe":               "coimbatore",
    "nagpur":            "nagpur",
    "bhopal":            "bhopal",
    "surat":             "surat",
    "patna":             "patna",
    "vadodara":          "vadodara",
    "baroda":            "vadodara",
    "madurai":           "madurai",
    "tiruchirappalli":   "tiruchirappalli",
    "trichy":            "tiruchirappalli",
    "salem":             "salem",
    "tirunelveli":       "tirunelveli",
    "erode":             "erode",
    "vijayawada":        "vijayawada",
    "guntur":            "guntur",
    "tirupati":          "tirupati",
    "warangal":          "warangal",
    "mangaluru":         "mangaluru",
    "mangalore":         "mangaluru",
    "hubli":             "hubballi",
    "hubballi":          "hubballi",
    "hubli-dharwad":     "hubballi",
    "belagavi":          "belagavi",
    "belgaum":           "belagavi",
    "ranchi":            "ranchi",
    "jamshedpur":        "jamshedpur",
    "guwahati":          "guwahati",
    "gauhati":           "guwahati",
    "dehradun":          "dehradun",
    "ghaziabad":         "ghaziabad",
    "faridabad":         "faridabad",
    "meerut":            "meerut",
    "agra":              "agra",
    "varanasi":          "varanasi",
    "banaras":           "varanasi",
    "kashi":             "varanasi",
    "jodhpur":           "jodhpur",
    "udaipur":           "udaipur",
    "amritsar":          "amritsar",
    "ludhiana":          "ludhiana",
    "raipur":            "raipur",
    "nashik":            "nashik",
    "aurangabad":        "aurangabad",
    "puducherry":        "puducherry",
    "pondicherry":       "puducherry",
    "kolhapur":          "kolhapur",
    "solapur":           "solapur",
    "kozhikode":         "kozhikode",
    "calicut":           "kozhikode",
    "thrissur":          "thrissur",
    "kollam":            "kollam",
    "kannur":            "kannur",
    "gwalior":           "gwalior",
    "jabalpur":          "jabalpur",
    "ujjain":            "ujjain",
    "rajkot":            "rajkot",
    "gandhinagar":       "gandhinagar",
    "panaji":            "panaji",
    "panjim":            "panaji",
    "srinagar":          "srinagar",
    "jammu":             "jammu",
    "shimla":            "shimla",
    # Special values
    "remote":            "remote",
    "wfh":               "remote",
    "work from home":    "remote",
    "anywhere":          "remote",
    "india":             "india",
    "pan india":         "india",
    "all india":         "india",
    "nationwide":        "india",
}

# City → state (lowercase), used for state-level fallback matching
CITY_STATE_MAP: dict[str, str] = {
    # Karnataka
    "bengaluru":      "karnataka",
    "mysuru":         "karnataka",
    "mangaluru":      "karnataka",
    "hubballi":       "karnataka",
    "belagavi":       "karnataka",
    "davangere":      "karnataka",
    "ballari":        "karnataka",
    # Maharashtra
    "mumbai":         "maharashtra",
    "pune":           "maharashtra",
    "nagpur":         "maharashtra",
    "nashik":         "maharashtra",
    "aurangabad":     "maharashtra",
    "solapur":        "maharashtra",
    "kolhapur":       "maharashtra",
    # Delhi / NCR
    "delhi":          "delhi",
    "noida":          "uttar pradesh",
    "ghaziabad":      "uttar pradesh",
    "gurugram":       "haryana",
    "faridabad":      "haryana",
    # Telangana
    "hyderabad":      "telangana",
    "warangal":       "telangana",
    "nizamabad":      "telangana",
    "karimnagar":     "telangana",
    # Tamil Nadu
    "chennai":        "tamil nadu",
    "coimbatore":     "tamil nadu",
    "madurai":        "tamil nadu",
    "tiruchirappalli":"tamil nadu",
    "salem":          "tamil nadu",
    "tirunelveli":    "tamil nadu",
    "erode":          "tamil nadu",
    # Kerala
    "kochi":          "kerala",
    "thiruvananthapuram": "kerala",
    "kozhikode":      "kerala",
    "thrissur":       "kerala",
    "kollam":         "kerala",
    "kannur":         "kerala",
    # Gujarat
    "ahmedabad":      "gujarat",
    "surat":          "gujarat",
    "vadodara":       "gujarat",
    "rajkot":         "gujarat",
    "gandhinagar":    "gujarat",
    # Rajasthan
    "jaipur":         "rajasthan",
    "jodhpur":        "rajasthan",
    "udaipur":        "rajasthan",
    "kota":           "rajasthan",
    "ajmer":          "rajasthan",
    # Andhra Pradesh
    "visakhapatnam":  "andhra pradesh",
    "vijayawada":     "andhra pradesh",
    "guntur":         "andhra pradesh",
    "tirupati":       "andhra pradesh",
    "kakinada":       "andhra pradesh",
    # West Bengal
    "kolkata":        "west bengal",
    # Punjab
    "amritsar":       "punjab",
    "ludhiana":       "punjab",
    "jalandhar":      "punjab",
    # Chandigarh
    "chandigarh":     "chandigarh",
    # Madhya Pradesh
    "indore":         "madhya pradesh",
    "bhopal":         "madhya pradesh",
    "gwalior":        "madhya pradesh",
    "jabalpur":       "madhya pradesh",
    "ujjain":         "madhya pradesh",
    # Uttar Pradesh
    "lucknow":        "uttar pradesh",
    "agra":           "uttar pradesh",
    "varanasi":       "uttar pradesh",
    "meerut":         "uttar pradesh",
    # Odisha
    "bhubaneswar":    "odisha",
    # Bihar
    "patna":          "bihar",
    # Jharkhand
    "ranchi":         "jharkhand",
    "jamshedpur":     "jharkhand",
    "dhanbad":        "jharkhand",
    # Assam
    "guwahati":       "assam",
    # Uttarakhand
    "dehradun":       "uttarakhand",
    "haridwar":       "uttarakhand",
    # Chhattisgarh
    "raipur":         "chhattisgarh",
    "bhilai":         "chhattisgarh",
    # Goa
    "panaji":         "goa",
    "margao":         "goa",
    # Haryana
    "gurugram":       "haryana",
    "faridabad":      "haryana",
}

# Nearby city chains: when city has 0 results, try these in order
NEARBY_CITIES: dict[str, list[str]] = {
    "mysuru":            ["bengaluru", "karnataka", "remote", "india"],
    "mangaluru":         ["bengaluru", "karnataka", "remote", "india"],
    "hubballi":          ["bengaluru", "karnataka", "remote", "india"],
    "belagavi":          ["pune", "bengaluru", "karnataka", "remote", "india"],
    "noida":             ["delhi", "gurugram", "uttar pradesh", "remote", "india"],
    "gurugram":          ["delhi", "noida", "haryana", "remote", "india"],
    "ghaziabad":         ["delhi", "noida", "uttar pradesh", "remote", "india"],
    "faridabad":         ["delhi", "gurugram", "haryana", "remote", "india"],
    "warangal":          ["hyderabad", "telangana", "remote", "india"],
    "visakhapatnam":     ["hyderabad", "andhra pradesh", "remote", "india"],
    "vijayawada":        ["hyderabad", "andhra pradesh", "remote", "india"],
    "coimbatore":        ["chennai", "bengaluru", "tamil nadu", "remote", "india"],
    "madurai":           ["chennai", "tamil nadu", "remote", "india"],
    "tiruchirappalli":   ["chennai", "coimbatore", "tamil nadu", "remote", "india"],
    "kochi":             ["thiruvananthapuram", "bengaluru", "kerala", "remote", "india"],
    "thiruvananthapuram":["kochi", "kerala", "remote", "india"],
    "kozhikode":         ["kochi", "kerala", "remote", "india"],
    "nagpur":            ["pune", "mumbai", "maharashtra", "remote", "india"],
    "nashik":            ["pune", "mumbai", "maharashtra", "remote", "india"],
    "aurangabad":        ["pune", "mumbai", "maharashtra", "remote", "india"],
    "surat":             ["ahmedabad", "mumbai", "gujarat", "remote", "india"],
    "vadodara":          ["ahmedabad", "gujarat", "remote", "india"],
    "rajkot":            ["ahmedabad", "gujarat", "remote", "india"],
    "gandhinagar":       ["ahmedabad", "gujarat", "remote", "india"],
    "jaipur":            ["delhi", "noida", "rajasthan", "remote", "india"],
    "jodhpur":           ["jaipur", "rajasthan", "remote", "india"],
    "udaipur":           ["jaipur", "rajasthan", "remote", "india"],
    "chandigarh":        ["delhi", "noida", "punjab", "remote", "india"],
    "amritsar":          ["chandigarh", "delhi", "punjab", "remote", "india"],
    "ludhiana":          ["chandigarh", "delhi", "punjab", "remote", "india"],
    "lucknow":           ["noida", "delhi", "uttar pradesh", "remote", "india"],
    "agra":              ["noida", "delhi", "uttar pradesh", "remote", "india"],
    "varanasi":          ["patna", "lucknow", "uttar pradesh", "remote", "india"],
    "indore":            ["bhopal", "pune", "madhya pradesh", "remote", "india"],
    "bhopal":            ["indore", "nagpur", "madhya pradesh", "remote", "india"],
    "gwalior":           ["noida", "bhopal", "madhya pradesh", "remote", "india"],
    "raipur":            ["nagpur", "bhopal", "chhattisgarh", "remote", "india"],
    "patna":             ["kolkata", "bihar", "remote", "india"],
    "ranchi":            ["kolkata", "jharkhand", "remote", "india"],
    "jamshedpur":        ["kolkata", "jharkhand", "remote", "india"],
    "bhubaneswar":       ["kolkata", "odisha", "remote", "india"],
    "guwahati":          ["kolkata", "assam", "remote", "india"],
    "dehradun":          ["noida", "delhi", "uttarakhand", "remote", "india"],
    "panaji":            ["mumbai", "pune", "goa", "remote", "india"],
    "srinagar":          ["delhi", "jammu", "remote", "india"],
    "jammu":             ["delhi", "chandigarh", "remote", "india"],
}

# All known Indian locations (cities + states) — used for "is this an Indian query?"
_ALL_INDIAN_LOCATIONS: set[str] = set(CITY_ALIASES.keys()) | set(CITY_STATE_MAP.keys()) | {
    "india", "remote", "karnataka", "maharashtra", "delhi", "uttar pradesh",
    "haryana", "telangana", "andhra pradesh", "tamil nadu", "kerala", "gujarat",
    "rajasthan", "west bengal", "punjab", "chandigarh", "madhya pradesh",
    "odisha", "bihar", "jharkhand", "assam", "uttarakhand", "chhattisgarh",
    "goa", "himachal pradesh", "jammu and kashmir", "north east", "north india",
    "south india",
}


# ── City Utility Functions ────────────────────────────────────────────────────

def normalize_city(raw: str) -> str:
    """Return lowercase canonical city name for a raw input string.

    Applies exact alias lookup first, then falls back to fuzzy matching
    against the alias keys at ≥ FUZZY_THRESHOLD similarity.
    """
    if not raw:
        return ""
    lower = raw.strip().lower()

    # Direct alias hit
    if lower in CITY_ALIASES:
        return CITY_ALIASES[lower]

    # Fuzzy match against alias keys (handles typos like "mysor", "mysur")
    matches = difflib.get_close_matches(lower, CITY_ALIASES.keys(), n=1, cutoff=FUZZY_THRESHOLD)
    if matches:
        return CITY_ALIASES[matches[0]]

    # If no alias hit, return as-is (lowercase)
    return lower


def _is_indian_query(city_canonical: str) -> bool:
    """Return True if the normalised city is a known Indian location."""
    return (
        city_canonical in _ALL_INDIAN_LOCATIONS
        or city_canonical in CITY_STATE_MAP
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_html(raw: str) -> str:
    """Strip HTML tags and normalise whitespace."""
    decoded = html.unescape(raw or "")
    no_tags = re.sub(r"<[^>]+>", " ", decoded)
    return re.sub(r"\s+", " ", no_tags).strip()


def _truncate(text: str, max_chars: int = 300) -> str:
    return textwrap.shorten(text, width=max_chars, placeholder="…")


def _empty_job() -> dict[str, str]:
    return {
        "title":       "",
        "company":     "",
        "location":    "",
        "url":         "",
        "source":      "",
        "date_posted": "",
        "job_type":    "",
        "tags":        "",
        "description": "",
        "salary":      "",
    }


def _is_non_indian_restricted(location: str) -> bool:
    """Check if the job location is restricted to a non-Indian country/region."""
    loc_lower = (location or "").lower().strip()
    if not loc_lower:
        return False

    # If it explicitly contains India or worldwide/global remote indicators, it's open to India.
    _INDIA_FRIENDLY = {"india", "worldwide", "global", "anywhere", "apac", "asia"}
    if any(f in loc_lower for f in _INDIA_FRIENDLY):
        return False

    # Check for known restricted countries/regions/cities
    restricted_words = [
        "germany", "deutschland", "berlin", "munich", "frankfurt", "hamburg",
        "united states", "usa", "america", "united kingdom", "london", "canada",
        "france", "paris", "netherlands", "amsterdam", "sweden", "stockholm",
        "europe", "european", "latam", "spain", "italy", "poland", "romania",
        "swiss", "switzerland", "austria", "belgium", "denmark", "norway", "finland",
        "australia", "sydney", "melbourne", "singapore", "japan", "tokyo"
    ]
    for word in restricted_words:
        if word in loc_lower:
            return True

    # Standalone words check
    if re.search(r'\b(us|uk|uae)\b', loc_lower):
        return True

    return False


# ── Abstract Base Scraper ─────────────────────────────────────────────────────

class BaseScraper(abc.ABC):
    """Abstract base class for all job scrapers."""

    source_name: str = "Unknown"

    def __init__(
        self,
        keyword: str,
        location: str = "",
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.keyword  = keyword.strip()
        self.timeout  = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": "JobVacancyScraper/2.0 (educational project)"}
        )
        self._logger = logging.getLogger(self.__class__.__name__)

        # Normalise and store the canonical location
        raw_loc = location.strip()
        self.location_raw       = raw_loc                  # original string (e.g. "Mysore")
        self.location           = raw_loc                  # kept for LinkedIn/Unstop API params
        self.location_canonical = normalize_city(raw_loc)  # e.g. "mysuru"
        self.location_state     = CITY_STATE_MAP.get(self.location_canonical, "")
        self._is_indian         = _is_indian_query(self.location_canonical)

        self._logger.debug(
            "Location normalised: %r → canonical=%r, state=%r, indian=%s",
            raw_loc, self.location_canonical, self.location_state, self._is_indian,
        )

    @abc.abstractmethod
    def fetch(self) -> list[dict[str, str]]:
        """Fetch job listings and return them as a list of unified dicts."""

    def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """Perform a GET request and return parsed JSON."""
        try:
            response = self._session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            self._logger.warning("Timeout after %ss for %s", self.timeout, url)
        except requests.exceptions.ConnectionError:
            self._logger.warning("Connection error for %s", url)
        except requests.exceptions.HTTPError as exc:
            self._logger.warning("HTTP %s for %s", exc.response.status_code, url)
        except Exception as exc:
            self._logger.error("Unexpected error for %s: %s", url, exc)
        return None

    def _keyword_matches(self, text: str) -> bool:
        """Three-tier keyword matcher (case-insensitive).

        1. Exact phrase  — "react developer" in "senior react developer"
        2. All tokens    — every word >2 chars must appear individually
                           so "react developer" finds "Senior React Engineer"
        3. Primary token — the longest word as a last-resort broad match
        """
        if not self.keyword:
            return True
        text_lower = text.lower()
        kw = self.keyword.lower()

        # Tier 1 – exact phrase
        if kw in text_lower:
            return True

        # Tokenise: strip punctuation, keep words > 2 chars
        tokens = [t for t in re.split(r"[\s\-_/().]+", kw) if len(t) > 2]
        if not tokens:
            return True

        # Tier 2 – all tokens present
        if all(t in text_lower for t in tokens):
            return True

        # Tier 3 – longest token (usually the key technology word)
        primary = max(tokens, key=len)
        return primary in text_lower

    def _location_matches(self, job_location: str) -> bool:
        """Smart, multi-tier location filter.

        Tier 0 — No search location → accept everything except non-Indian.
        Tier 1 — Broad/remote query ("remote", "india", "worldwide") → accept
                 anything that isn't non-Indian-restricted.
        Tier 2 — Specific Indian city:
                 a. Job location contains the canonical city name (or alias).
                 b. Job location contains the state for that city.
                 c. Fuzzy match: any city-like word in the job location has
                    ≥ FUZZY_THRESHOLD similarity to the search city.
                 d. Job location is remote-friendly (worldwide, global, etc.)
        Tier 3 — If nothing matched → reject.
        """
        loc_lower   = job_location.lower()
        search_can  = self.location_canonical   # normalised search city

        # ── Tier 0: no location filter ────────────────────────────────────────
        if not search_can:
            return not _is_non_indian_restricted(job_location)

        # ── Remote/worldwide queries ───────────────────────────────────────────
        _REMOTE_QUERIES = {"remote", "worldwide", "anywhere", "global",
                           "international", "wfh", "work from home"}
        if search_can in _REMOTE_QUERIES:
            return not _is_non_indian_restricted(job_location)

        # ── Broad India query ──────────────────────────────────────────────────
        if search_can == "india":
            return not _is_non_indian_restricted(job_location)

        # ── Specific city query ────────────────────────────────────────────────
        if self._is_indian:
            # Reject non-Indian restricted jobs outright
            if _is_non_indian_restricted(job_location):
                return False

            # a. Direct substring: canonical city name in job location
            if search_can in loc_lower:
                return True

            # b. Any alias of the search city appears in the job location
            for alias, canon in CITY_ALIASES.items():
                if canon == search_can and alias in loc_lower:
                    return True

            # c. State-level match: job location mentions the same state
            if self.location_state and self.location_state in loc_lower:
                return True

            # d. Fuzzy match: split job location into tokens, fuzzy-compare each
            loc_tokens = re.split(r"[\s,;|/()]+", loc_lower)
            for tok in loc_tokens:
                tok = tok.strip()
                if len(tok) < 3:
                    continue
                # Check similarity against the canonical city
                ratio = difflib.SequenceMatcher(None, search_can, tok).ratio()
                if ratio >= FUZZY_THRESHOLD:
                    return True
                # Also check against all aliases for that city
                for alias, canon in CITY_ALIASES.items():
                    if canon == search_can:
                        r2 = difflib.SequenceMatcher(None, alias, tok).ratio()
                        if r2 >= FUZZY_THRESHOLD:
                            return True

            # e. Remote-friendly job location is always acceptable for Indian city queries
            _REMOTE_FRIENDLY = {"worldwide", "remote", "india", "apac", "asia",
                                 "anywhere", "global"}
            if any(r in loc_lower for r in _REMOTE_FRIENDLY):
                return True

            return False

        # ── Non-Indian / unrecognised location ────────────────────────────────
        # Direct substring match
        if search_can in loc_lower:
            return True
        return not _is_non_indian_restricted(job_location)


# ── Concrete Scrapers ─────────────────────────────────────────────────────────

class HimalayasScraper(BaseScraper):
    """Scraper for Himalayas (https://himalayas.app/jobs/api).

    95 000+ curated remote / hybrid jobs. No API key.
    Supports keyword search, pagination, location restrictions,
    salary ranges, and company logos.
    """

    source_name = "Himalayas"
    _API_URL    = "https://himalayas.app/jobs/api"

    _TYPE_MAP: dict[str, str] = {
        "fullTime":   "Full-time",
        "full-time":  "Full-time",
        "partTime":   "Part-time",
        "part-time":  "Part-time",
        "contract":   "Contract",
        "freelance":  "Freelance",
        "internship": "Internship",
    }

    def fetch(self) -> list[dict[str, str]]:
        self._logger.info("Fetching from Himalayas (keyword=%r)", self.keyword)
        results: list[dict[str, str]] = []
        offset = 0
        batch  = 50

        while len(results) < MAX_RESULTS_PER_SOURCE:
            params: dict[str, Any] = {
                "q":      self.keyword,
                "limit":  batch,
                "offset": offset,
            }
            data = self._get(self._API_URL, params=params)
            if not isinstance(data, dict):
                break

            jobs_page: list[dict] = data.get("jobs", []) or []
            if not jobs_page:
                break

            for raw in jobs_page:
                title    = raw.get("title", "")
                company  = raw.get("companyName", "")
                url      = raw.get("applicationLink", raw.get("guid", ""))
                full_desc = _clean_html(raw.get("description", ""))
                cats: list[str] = raw.get("categories", []) or []
                emp_type = raw.get("employmentType", "") or ""
                pub_timestamp = raw.get("pubDate")
                if isinstance(pub_timestamp, (int, float)):
                    try:
                        pub_date = datetime.datetime.fromtimestamp(pub_timestamp).strftime('%Y-%m-%d')
                    except Exception:
                        pub_date = ""
                else:
                    pub_date = str(pub_timestamp or "")[:10]

                # Location from locationRestrictions list
                loc_list: list[str] = raw.get("locationRestrictions", []) or []
                location = ", ".join(loc_list) if loc_list else "Worldwide"

                # Salary
                mn  = raw.get("minSalary") or 0
                mx  = raw.get("maxSalary") or 0
                cur = raw.get("currency", "USD") or "USD"
                per = raw.get("salaryPeriod", "") or ""
                salary = ""
                if mn and mx:
                    salary = f"{cur} {mn:,}–{mx:,}/{per}" if per else f"{cur} {mn:,}–{mx:,}"
                elif mn:
                    salary = f"{cur} {mn:,}+"

                job_type = self._TYPE_MAP.get(emp_type, emp_type or "Full-time")

                searchable = f"{title} {company} {' '.join(cats)} {full_desc}"
                if not self._keyword_matches(searchable):
                    continue
                if not self._location_matches(location):
                    continue

                job = _empty_job()
                job["title"]       = title
                job["company"]     = company
                job["location"]    = location
                job["url"]         = url
                job["source"]      = self.source_name
                job["date_posted"] = pub_date
                job["job_type"]    = job_type
                job["tags"]        = ", ".join(cats[:8])
                job["description"] = _truncate(full_desc)
                job["salary"]      = salary
                results.append(job)

                if len(results) >= MAX_RESULTS_PER_SOURCE:
                    break

            total = data.get("totalCount", 0)
            offset += batch
            if offset >= min(total, MAX_RESULTS_PER_SOURCE * 2):
                break

        self._logger.info("Himalayas: returned %d jobs", len(results))
        return results


class JobicyScraper(BaseScraper):
    """Scraper for Jobicy (https://jobicy.com/api/v2/remote-jobs).

    Hand-picked remote tech jobs. Free, no API key. Supports tag-based
    keyword search.
    """

    source_name = "Jobicy"
    _API_URL    = "https://jobicy.com/api/v2/remote-jobs"

    def fetch(self) -> list[dict[str, str]]:
        self._logger.info("Fetching from Jobicy (keyword=%r)", self.keyword)
        # Use the longest meaningful token as the search tag
        tokens  = [t for t in re.split(r"[\s\-_/().]+", self.keyword.lower()) if len(t) > 2]
        primary = max(tokens, key=len) if tokens else self.keyword

        params: dict[str, Any] = {
            "count": MAX_RESULTS_PER_SOURCE,
            "tag":   primary,
        }
        data = self._get(self._API_URL, params=params)
        if not isinstance(data, dict):
            return []

        jobs_raw: list[dict] = data.get("jobs", []) or []
        results: list[dict[str, str]] = []

        for raw in jobs_raw:
            title   = raw.get("jobTitle", "")
            company = raw.get("companyName", "")
            url     = raw.get("url", "")
            geo     = raw.get("jobGeo", "Worldwide") or "Worldwide"
            types   = raw.get("jobType", []) or []
            full_desc = _clean_html(raw.get("jobDescription", raw.get("jobExcerpt", "")))
            pub     = (raw.get("pubDate", "") or "")[:10]
            inds: list[str] = raw.get("jobIndustry", []) or []

            job_type = types[0] if types else "Full-time"

            searchable = f"{title} {company} {' '.join(inds)} {full_desc}"
            if not self._keyword_matches(searchable):
                continue
            if not self._location_matches(geo):
                continue

            job = _empty_job()
            job["title"]       = title
            job["company"]     = company
            job["location"]    = geo
            job["url"]         = url
            job["source"]      = self.source_name
            job["date_posted"] = pub
            job["job_type"]    = job_type
            job["tags"]        = ", ".join(inds[:8])
            job["description"] = _truncate(full_desc)
            results.append(job)

            if len(results) >= MAX_RESULTS_PER_SOURCE:
                break

        self._logger.info("Jobicy: returned %d jobs", len(results))
        return results


class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn via public guest search API."""

    source_name = "LinkedIn"
    _API_URL    = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    def fetch(self) -> list[dict[str, str]]:
        self._logger.info("Fetching from LinkedIn (keyword=%r, location=%r)", self.keyword, self.location)
        results: list[dict[str, str]] = []
        loc = self.location or "India"
        params: dict[str, Any] = {
            "keywords": self.keyword,
            "location": loc,
            "start": 0,
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            response = self._session.get(self._API_URL, params=params, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            html_content = response.text
        except Exception as exc:
            self._logger.warning("Error fetching from LinkedIn: %s", exc)
            return []

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        list_items = soup.find_all("li")

        for li in list_items:
            h3 = li.find("h3")
            if not h3:
                continue
            title = h3.text.strip()

            h4 = li.find("h4")
            company = h4.text.strip() if h4 else "Unknown"

            loc_span = li.find("span", class_="job-search-card__location")
            location = loc_span.text.strip() if loc_span else "Remote"

            time_tag = li.find("time")
            pub_date = time_tag.get("datetime", "") if time_tag else ""
            if pub_date:
                pub_date = pub_date[:10]

            a_tag = li.find("a", class_="base-card__full-link")
            url = a_tag.get("href", "") if a_tag else ""

            desc = f"Apply directly on LinkedIn. Position: {title} at {company}."
            searchable = f"{title} {company} {location} {desc}"
            if not self._keyword_matches(searchable):
                continue
            if not self._location_matches(location):
                continue

            job = _empty_job()
            job["title"]       = title
            job["company"]     = company
            job["location"]    = location
            job["url"]         = url
            job["source"]      = self.source_name
            job["date_posted"] = pub_date
            job["job_type"]    = "Full-time"
            job["tags"]        = "LinkedIn, Careers"
            job["description"] = desc
            results.append(job)

            if len(results) >= MAX_RESULTS_PER_SOURCE:
                break

        self._logger.info("LinkedIn: returned %d jobs", len(results))
        return results


class RemotiveScraper(BaseScraper):
    """Scraper for Remotive (https://remotive.com/api/remote-jobs)."""

    source_name = "Remotive"
    _API_URL    = "https://remotive.com/api/remote-jobs"

    def fetch(self) -> list[dict[str, str]]:
        self._logger.info("Fetching from Remotive (keyword=%r)", self.keyword)
        params: dict[str, Any] = {
            "search": self.keyword,
            "limit": MAX_RESULTS_PER_SOURCE,
        }
        data = self._get(self._API_URL, params=params)
        if not isinstance(data, dict):
            return []

        jobs_raw: list[dict] = data.get("jobs", []) or []
        results: list[dict[str, str]] = []

        for raw in jobs_raw:
            title   = raw.get("title", "")
            company = raw.get("company_name", "")
            url     = raw.get("url", "")
            location = raw.get("candidate_required_location", "Worldwide") or "Worldwide"
            pub_date = (raw.get("publication_date", "") or "")[:10]
            salary   = raw.get("salary", "")
            emp_type = raw.get("job_type", "")
            cats     = raw.get("tags", []) or []

            full_desc = _clean_html(raw.get("description", ""))
            desc      = _truncate(full_desc)

            searchable = f"{title} {company} {' '.join(cats)} {full_desc}"
            if not self._keyword_matches(searchable):
                continue
            if not self._location_matches(location):
                continue

            job = _empty_job()
            job["title"]       = title
            job["company"]     = company
            job["location"]    = location
            job["url"]         = url
            job["source"]      = self.source_name
            job["date_posted"] = pub_date
            job["job_type"]    = emp_type.capitalize() if emp_type else "Full-time"
            job["tags"]        = ", ".join(cats[:8])
            job["description"] = desc
            job["salary"]      = salary
            results.append(job)

            if len(results) >= MAX_RESULTS_PER_SOURCE:
                break

        self._logger.info("Remotive: returned %d jobs", len(results))
        return results


class UnstopScraper(BaseScraper):
    """Scraper for Unstop (https://unstop.com/api/public/opportunity/search-result)."""

    source_name = "Unstop"
    _API_URL    = "https://unstop.com/api/public/opportunity/search-result"

    def fetch(self) -> list[dict[str, str]]:
        self._logger.info("Fetching from Unstop (keyword=%r, location=%r)", self.keyword, self.location)
        results: list[dict[str, str]] = []
        opportunity_types = ["jobs", "internships"]
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        for opp_type in opportunity_types:
            params: dict[str, Any] = {
                "opportunity": opp_type,
                "oppstatus": "open",
                "page": 1,
                "keyword": self.keyword,
            }
            try:
                response = self._session.get(self._API_URL, params=params, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                self._logger.warning("Error fetching from Unstop (%s): %s", opp_type, exc)
                continue

            jobs_raw = data.get("data", {}).get("data", []) or []
            for raw in jobs_raw:
                title = raw.get("title", "")
                org = raw.get("organisation", {}) or {}
                company = org.get("name", "Unknown")
                url = raw.get("seo_url", "")

                # Reconstruct location
                loc_list = raw.get("locations", []) or []
                if loc_list and isinstance(loc_list, list):
                    loc_parts = []
                    for l in loc_list:
                        if isinstance(l, dict):
                            city = l.get("city")
                            state = l.get("state")
                            country = l.get("country")
                            part = ", ".join(filter(None, [city, state, country]))
                            if part:
                                loc_parts.append(part)
                    location = "; ".join(loc_parts) if loc_parts else "India"
                else:
                    location = "India"

                pub_date = (raw.get("created_at", "") or "")[:10]

                # Job details and skills tags
                skills_list = raw.get("required_skills", []) or []
                skills = [s.get("name") for s in skills_list if isinstance(s, dict) and isinstance(s.get("name"), str)]

                desc = f"Apply on Unstop. Job opportunity by {company}. Title: {title}."
                if skills:
                    desc += f" Required skills: {', '.join(skills)}."

                searchable = f"{title} {company} {location} {desc}"
                if not self._keyword_matches(searchable):
                    continue
                if not self._location_matches(location):
                    continue

                job = _empty_job()
                job["title"]       = title
                job["company"]     = company
                job["location"]    = location
                job["url"]         = url
                job["source"]      = self.source_name
                job["date_posted"] = pub_date
                job["job_type"]    = "Full-time" if opp_type == "jobs" else "Internship"
                job["tags"]        = ", ".join(skills[:8]) if skills else "Unstop, Careers"
                job["description"] = _truncate(desc)
                results.append(job)

                if len(results) >= MAX_RESULTS_PER_SOURCE:
                    break

        self._logger.info("Unstop: returned %d jobs", len(results))
        return results


class ArbeitnowScraper(BaseScraper):
    """Scraper for Arbeitnow (https://www.arbeitnow.com/api/job-board-api)."""

    source_name = "Arbeitnow"
    _API_URL    = "https://www.arbeitnow.com/api/job-board-api"

    def fetch(self) -> list[dict[str, str]]:
        self._logger.info("Fetching from Arbeitnow (keyword=%r)", self.keyword)
        results: list[dict[str, str]] = []
        url = self._API_URL

        while url and len(results) < MAX_RESULTS_PER_SOURCE:
            data = self._get(url)
            if not isinstance(data, dict):
                break

            jobs_page: list[dict] = data.get("data", []) or []
            if not jobs_page:
                break

            for raw in jobs_page:
                title    = raw.get("title", "")
                company  = raw.get("company_name", "")
                url_job  = raw.get("url", "")
                loc_val = raw.get("location", "")
                is_remote = raw.get("remote", False)
                if is_remote:
                    location = f"{loc_val} (Remote)" if loc_val else "Remote"
                else:
                    location = loc_val or "Germany"
                pub_date = datetime.datetime.fromtimestamp(raw.get("created_at", 0)).strftime('%Y-%m-%d') if raw.get("created_at") else ""
                job_types = raw.get("job_types", []) or []
                job_type  = job_types[0].capitalize() if job_types else "Full-time"
                cats      = raw.get("tags", []) or []

                full_desc = _clean_html(raw.get("description", ""))
                desc      = _truncate(full_desc)

                searchable = f"{title} {company} {' '.join(cats)} {full_desc}"
                if not self._keyword_matches(searchable):
                    continue
                # Arbeitnow is a German-focused board. If the search location is not explicitly Germany/Europe,
                # filter out Arbeitnow jobs unless they explicitly mention India or worldwide/global indicators.
                search_loc_lower = self.location.lower()
                if not any(x in search_loc_lower for x in ["germany", "deutschland", "europe", "munich", "berlin", "hamburg", "frankfurt"]):
                    loc_lower = location.lower()
                    if not any(x in loc_lower for x in ["india", "worldwide", "global", "anywhere"]):
                        continue
                if not self._location_matches(location):
                    continue

                job = _empty_job()
                job["title"]       = title
                job["company"]     = company
                job["location"]    = location
                job["url"]         = url_job
                job["source"]      = self.source_name
                job["date_posted"] = pub_date
                job["job_type"]    = job_type
                job["tags"]        = ", ".join(cats[:8])
                job["description"] = desc
                results.append(job)

                if len(results) >= MAX_RESULTS_PER_SOURCE:
                    break

            # Only do one page
            break

        self._logger.info("Arbeitnow: returned %d jobs", len(results))
        return results


# ── Job Aggregator ────────────────────────────────────────────────────────────

class JobAggregator:
    """Orchestrates multiple scrapers concurrently and returns merged results.

    Smart city fallback order (when no results found for exact city):
        exact city → nearby cities (per NEARBY_CITIES map) → state → Remote → India
    """

    def __init__(
        self,
        keyword: str,
        location: str = "",
        timeout: int = DEFAULT_TIMEOUT,
        max_workers: int = MAX_WORKERS,
    ) -> None:
        self.keyword    = keyword
        self.location   = location
        self.timeout    = timeout
        self.max_workers = max_workers
        self._logger    = logging.getLogger("JobAggregator")

        # Canonical form of the requested location
        self._canonical_loc = normalize_city(location)

    def _build_scrapers(self, location: str) -> list[BaseScraper]:
        classes = [LinkedInScraper, UnstopScraper, HimalayasScraper,
                   JobicyScraper, RemotiveScraper, ArbeitnowScraper]
        return [
            cls(keyword=self.keyword, location=location, timeout=self.timeout)
            for cls in classes
        ]

    @staticmethod
    def _deduplicate(jobs: list[dict[str, str]]) -> list[dict[str, str]]:
        seen: set[str] = set()
        unique: list[dict[str, str]] = []
        for job in jobs:
            key = job.get("url", "").strip()
            if not key or key not in seen:
                unique.append(job)
                if key:
                    seen.add(key)
        return unique

    def _run_scrapers(self, location: str) -> list[dict[str, str]]:
        """Run all scrapers for a given location and return deduplicated results."""
        scrapers  = self._build_scrapers(location)
        all_jobs: list[dict[str, str]] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_scraper = {
                executor.submit(scraper.fetch): scraper.source_name
                for scraper in scrapers
            }
            for future in as_completed(future_to_scraper):
                source = future_to_scraper[future]
                try:
                    jobs = future.result()
                    self._logger.info("%s finished: %d jobs", source, len(jobs))
                    all_jobs.extend(jobs)
                except Exception as exc:
                    self._logger.error("%s raised an exception: %s", source, exc)

        return self._deduplicate(all_jobs)

    def _sort(self, jobs: list[dict[str, str]]) -> list[dict[str, str]]:
        def sort_key(job: dict[str, str]) -> tuple[str, str]:
            return (job.get("date_posted", "") or "", job.get("source", ""))
        return sorted(jobs, key=sort_key, reverse=True)

    def run(self) -> dict[str, Any]:
        """Run the full aggregation with smart city fallback.

        Returns a dict with:
            jobs            : list of job dicts
            fallback_used   : bool — True if a fallback location was used
            fallback_message: str  — human-readable explanation, or ""
            searched_location: str — the actual location that produced results
        """
        canonical = self._canonical_loc
        original_loc = self.location

        self._logger.info(
            "Starting aggregation — keyword=%r, location=%r (canonical=%r)",
            self.keyword, original_loc, canonical,
        )

        # ── Step 1: Search with the exact (normalised) location ───────────────
        # For the first attempt we pass the *original* location string so that
        # LinkedIn / Unstop get a human-readable city name for their API params.
        results = self._run_scrapers(original_loc)
        self._logger.info("Aggregation complete (primary): %d unique jobs", len(results))

        if results:
            return {
                "jobs":             self._sort(results),
                "fallback_used":    False,
                "fallback_message": "",
                "searched_location": original_loc,
            }

        # ── Step 2: Nearby city fallback ──────────────────────────────────────
        nearby_chain = NEARBY_CITIES.get(canonical, [])

        # Build a default chain for any Indian city not in NEARBY_CITIES
        state = CITY_STATE_MAP.get(canonical, "")
        if not nearby_chain and _is_indian_query(canonical) and canonical not in {"india", "remote"}:
            nearby_chain = []
            if state:
                nearby_chain.append(state)
            nearby_chain += ["remote", "india"]

        tried: list[str] = [canonical]

        for fallback_loc in nearby_chain:
            if fallback_loc in tried:
                continue
            tried.append(fallback_loc)

            self._logger.info(
                "No results for %r — trying fallback location: %r",
                original_loc, fallback_loc,
            )
            fallback_results = self._run_scrapers(fallback_loc)
            if fallback_results:
                # Build a human-readable fallback message
                display_original = original_loc.title() if original_loc else canonical.title()

                if fallback_loc in ("remote", "india"):
                    display_fallback = fallback_loc.title()
                    msg = (
                        f"No jobs found in {display_original}. "
                        f"Showing {display_fallback} opportunities instead."
                    )
                elif state and fallback_loc == state:
                    msg = (
                        f"No jobs found in {display_original}. "
                        f"Showing nearby {state.title()} and Remote opportunities instead."
                    )
                else:
                    display_fallback = fallback_loc.title()
                    msg = (
                        f"No jobs found in {display_original}. "
                        f"Showing nearby {display_fallback} opportunities instead."
                    )

                self._logger.info(
                    "Fallback succeeded for %r → %r: %d jobs",
                    original_loc, fallback_loc, len(fallback_results),
                )
                return {
                    "jobs":             self._sort(fallback_results),
                    "fallback_used":    True,
                    "fallback_message": msg,
                    "searched_location": fallback_loc,
                }

        # ── Step 3: Absolute fallback — India-wide ────────────────────────────
        if "india" not in tried:
            self._logger.info("All fallbacks exhausted — trying India-wide search")
            india_results = self._run_scrapers("India")
            if india_results:
                display_original = original_loc.title() if original_loc else canonical.title()
                return {
                    "jobs":             self._sort(india_results),
                    "fallback_used":    True,
                    "fallback_message": (
                        f"No jobs found in {display_original}. "
                        f"Showing India-wide opportunities instead."
                    ),
                    "searched_location": "India",
                }

        # ── No results at all ─────────────────────────────────────────────────
        self._logger.info("Aggregation complete: 0 unique jobs after all fallbacks")
        return {
            "jobs":             [],
            "fallback_used":    False,
            "fallback_message": "",
            "searched_location": original_loc,
        }
