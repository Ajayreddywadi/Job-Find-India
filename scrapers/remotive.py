from typing import Any

from scrapers.base import BaseScraper
from scrapers.registry import register_scraper
from config.settings import MAX_RESULTS_PER_SOURCE
from utils.helpers import _clean_html, _truncate, _empty_job
from models.job import Job

@register_scraper
class RemotiveScraper(BaseScraper):
    """Scraper for Remotive (https://remotive.com/api/remote-jobs)."""

    source_name = "Remotive"
    _API_URL    = "https://remotive.com/api/remote-jobs"

    def fetch(self) -> list[Job]:
        self._logger.info("Fetching from Remotive (keyword=%r)", self.keyword)
        params: dict[str, Any] = {
            "search": self.keyword,
            "limit": MAX_RESULTS_PER_SOURCE,
        }
        data = self._get(self._API_URL, params=params)
        if not isinstance(data, dict):
            return []

        jobs_raw: list[dict] = data.get("jobs", []) or []
        results: list[Job] = []

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
