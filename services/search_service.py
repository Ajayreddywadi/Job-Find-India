import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from config.settings import DEFAULT_TIMEOUT, MAX_WORKERS
from config.cities import (
    CITY_STATE_MAP,
    NEARBY_CITIES,
    CANONICAL_TO_ALIASES,
    normalize_city,
    _is_indian_query,
)
from models.job import Job
from scrapers.base import BaseScraper
from scrapers.registry import SCRAPER_REGISTRY
from services.validator import validate_request, validate_job
from metrics import METRICS

# Ensure all scrapers are registered by importing scrapers package
import scrapers

class JobAggregator:
    """Orchestrates multiple scrapers concurrently and returns merged results."""

    def __init__(
        self,
        keyword: str,
        location: str = "",
        timeout: int = DEFAULT_TIMEOUT,
        max_workers: int = MAX_WORKERS,
    ) -> None:
        # Perform parameter validation
        validate_request(keyword, location)

        self.keyword    = keyword
        self.location   = location
        self.timeout    = timeout
        self.max_workers = max_workers
        self._logger    = logging.getLogger("JobAggregator")

        # Canonical form of the requested location
        self._canonical_loc = normalize_city(location)

    def _build_scrapers(self, location: str) -> list[BaseScraper]:
        """Build scraper instances from registry."""
        return [
            cls(keyword=self.keyword, location=location, timeout=self.timeout)
            for cls in SCRAPER_REGISTRY
        ]

    @staticmethod
    def _deduplicate(jobs: list[Job]) -> list[Job]:
        seen: set[str] = set()
        unique: list[Job] = []
        for job in jobs:
            key = job.get("url", "").strip()
            if not key or key not in seen:
                unique.append(job)
                if key:
                    seen.add(key)
        return unique

    def _run_scrapers(self, location: str) -> list[Job]:
        """Run all scrapers for a given location and return deduplicated results."""
        scrapers  = self._build_scrapers(location)
        all_jobs: list[Job] = []

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
                    METRICS.record_jobs(source, len(jobs))
                except Exception as exc:
                    self._logger.error("%s raised an exception: %s", source, exc)
                    METRICS.record_error(source)

        # Filter out invalid jobs and deduplicate
        validated_jobs = [job for job in all_jobs if validate_job(job)]
        return self._deduplicate(validated_jobs)

    def _sort(self, jobs: list[Job]) -> list[Job]:
        # Pass 1: Sort by date descending (newest first) and source descending
        def pass1_key(job: Job) -> tuple[str, str]:
            return (job.get("date_posted", "") or "", job.get("source", "") or "")
        sorted_by_date = sorted(jobs, key=pass1_key, reverse=True)

        # Pass 2: Stable sort by location priority (Priority 1 first)
        def pass2_key(job: Job) -> int:
            loc_lower = (job.get("location", "") or "").lower()
            search_can = self._canonical_loc

            if not search_can or search_can.lower() in {"india", "remote", "worldwide", "anywhere"}:
                return 1

            search_can_lower = search_can.lower()

            # Priority 1: Exact searched city (canonical or alias)
            if search_can_lower in loc_lower:
                return 1
            aliases = CANONICAL_TO_ALIASES.get(search_can_lower, [])
            if any(alias in loc_lower for alias in aliases):
                return 1

            # Priority 2: Same state
            state = CITY_STATE_MAP.get(search_can_lower, "")
            if state and state in loc_lower:
                return 2

            # Priority 3: Nearby city (fallback)
            nearby = NEARBY_CITIES.get(search_can_lower, [])
            for n_city in nearby:
                n_city_lower = n_city.lower()
                if n_city_lower in loc_lower:
                    return 3
                n_aliases = CANONICAL_TO_ALIASES.get(n_city_lower, [])
                if any(alias in loc_lower for alias in n_aliases):
                    return 3

            # Priority 4: Remote / Anywhere
            _REMOTE_KEYWORDS = {"remote", "anywhere", "worldwide", "global", "apac", "asia"}
            if any(r in loc_lower for r in _REMOTE_KEYWORDS):
                return 4

            # Priority 5: India-wide
            if "india" in loc_lower:
                return 5

            return 6

        sorted_by_loc = sorted(sorted_by_date, key=pass2_key)

        # Pass 3: Stable sort by keyword relevance (Relevance 1 first)
        def pass3_key(job: Job) -> int:
            import re
            title_lower = (job.get("title", "") or "").lower()
            kw_clean = self.keyword.strip().lower()

            if "devops" in kw_clean:
                if "devops engineer" in title_lower:
                    return 1
                if "devops" in title_lower:
                    return 2
                if "site reliability engineer" in title_lower or re.search(r'\bsre\b', title_lower):
                    return 3
                if "platform engineer" in title_lower:
                    return 4
                if "cloud engineer" in title_lower:
                    return 5
                if "kubernetes engineer" in title_lower:
                    return 6
                if "infrastructure engineer" in title_lower:
                    return 7
                if "software engineer" in title_lower or "software developer" in title_lower or "developer" in title_lower:
                    return 8
                if "engineering manager" in title_lower or "manager" in title_lower:
                    return 9
                return 10
            else:
                if kw_clean in title_lower:
                    return 1
                words = kw_clean.split()
                if words and all(w in title_lower for w in words):
                    return 2
                if words and any(w in title_lower for w in words):
                    return 3
                return 4

        return sorted(sorted_by_loc, key=pass3_key)

    def run(self) -> dict[str, Any]:
        """Run the full aggregation with smart city fallback."""
        METRICS.record_request()
        canonical = self._canonical_loc
        original_loc = self.location

        self._logger.info(
            "Starting aggregation — keyword=%r, location=%r (canonical=%r)",
            self.keyword, original_loc, canonical,
        )

        results = self._run_scrapers(original_loc)
        self._logger.info("Aggregation complete (primary): %d unique jobs", len(results))

        if results:
            return {
                "jobs":             self._sort(results),
                "fallback_used":    False,
                "fallback_message": "",
                "searched_location": original_loc,
            }

        nearby_chain = NEARBY_CITIES.get(canonical, [])
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

        self._logger.info("Aggregation complete: 0 unique jobs after all fallbacks")
        return {
            "jobs":             [],
            "fallback_used":    False,
            "fallback_message": "",
            "searched_location": original_loc,
        }
