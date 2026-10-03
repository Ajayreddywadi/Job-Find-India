import abc
import logging
from typing import Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from config.settings import DEFAULT_TIMEOUT
from config.cities import normalize_city, CITY_STATE_MAP, _is_indian_query
from models.job import Job

# Custom exception hierarchy
class ScraperError(Exception):
    """Base exception for all scrapers."""
    pass

class ScraperFetchError(ScraperError):
    """Raised when an HTTP request fails or times out."""
    pass

class ScraperParsingError(ScraperError):
    """Raised when parsing target HTML or JSON fails."""
    pass

# Create global shared session with thread-safe exponential backoff retry adapter
def _create_shared_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": "JobVacancyScraper/2.0 (educational system)"
    })
    return session

SHARED_SESSION = _create_shared_session()

class BaseScraper(abc.ABC):
    """Abstract base class for all job scrapers."""

    source_name: str = "Unknown"

    def __init__(
        self,
        keyword: str,
        location: str = "",
        timeout: int = DEFAULT_TIMEOUT,
        session: requests.Session = SHARED_SESSION,
    ) -> None:
        self.keyword = keyword.strip()
        self.timeout = timeout
        self._session = session  # Dependency Injection of requests Session
        self._logger = logging.getLogger(self.__class__.__name__)

        raw_loc = location.strip()
        self.location_raw = raw_loc
        self.location = raw_loc
        self.location_canonical = normalize_city(raw_loc)
        self.location_state = CITY_STATE_MAP.get(self.location_canonical, "")
        self._is_indian = _is_indian_query(self.location_canonical)

    @abc.abstractmethod
    def fetch(self) -> list[Job]:
        """Fetch job listings and return them as a list of Job TypedDicts."""
        pass

    def _get(self, url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
        """Perform a GET request using the shared session."""
        try:
            response = self._session.get(url, params=params, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            self._logger.warning("Timeout after %ss for %s", self.timeout, url)
        except requests.exceptions.ConnectionError:
            self._logger.warning("Connection error for %s", url)
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "Unknown"
            self._logger.warning("HTTP %s for %s", status, url)
        except Exception as exc:
            self._logger.error("Unexpected error for %s: %s", url, exc)
        return None

    def _keyword_matches(self, text: str) -> bool:
        """Helper to match keywords (Tiers match)."""
        if not self.keyword:
            return True
        text_lower = text.lower()
        kw = self.keyword.lower()

        if kw in text_lower:
            return True

        tokens = [t for t in re_split_tokens(kw) if len(t) > 2]
        if not tokens:
            return True

        if all(t in text_lower for t in tokens):
            return True

        primary = max(tokens, key=len)
        return primary in text_lower

    def _location_matches(self, job_location: str) -> bool:
        """Location filter logic."""
        import re
        import difflib
        from config.cities import CITY_ALIASES, CANONICAL_TO_ALIASES
        from config.settings import FUZZY_THRESHOLD
        from utils.helpers import _is_non_indian_restricted

        loc_lower = job_location.lower()
        search_can = self.location_canonical

        if not search_can:
            return not _is_non_indian_restricted(job_location)

        _REMOTE_QUERIES = {"remote", "worldwide", "anywhere", "global", "international", "wfh", "work from home"}
        if search_can in _REMOTE_QUERIES:
            return not _is_non_indian_restricted(job_location)

        if search_can == "india":
            return not _is_non_indian_restricted(job_location)

        if self._is_indian:
            if _is_non_indian_restricted(job_location):
                return False

            if search_can in loc_lower:
                return True

            aliases = CANONICAL_TO_ALIASES.get(search_can, [])
            if any(alias in loc_lower for alias in aliases):
                return True

            if self.location_state and self.location_state in loc_lower:
                return True

            loc_tokens = re.split(r"[\s,;|/()]+", loc_lower)
            for tok in loc_tokens:
                tok = tok.strip()
                if len(tok) < 3:
                    continue
                ratio = difflib.SequenceMatcher(None, search_can, tok).ratio()
                if ratio >= FUZZY_THRESHOLD:
                    return True
                for alias in aliases:
                    r2 = difflib.SequenceMatcher(None, alias, tok).ratio()
                    if r2 >= FUZZY_THRESHOLD:
                        return True

            _REMOTE_FRIENDLY = {"worldwide", "remote", "india", "apac", "asia", "anywhere", "global"}
            if any(r in loc_lower for r in _REMOTE_FRIENDLY):
                return True

            return False

        if search_can in loc_lower:
            return True
        return not _is_non_indian_restricted(job_location)

# Helper to split tokens
def re_split_tokens(text: str) -> list[str]:
    import re
    return re.split(r"[\s\-_/().]+", text)
