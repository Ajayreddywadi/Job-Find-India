import re
from typing import Any

from scrapers.base import BaseScraper
from scrapers.registry import register_scraper
from config.settings import MAX_RESULTS_PER_SOURCE
from utils.helpers import _clean_html, _truncate, _empty_job
from models.job import Job

@register_scraper
class JobicyScraper(BaseScraper):
    """Scraper for Jobicy (https://jobicy.com/api/v2/remote-jobs)."""

    source_name = "Jobicy"
    _API_URL    = "https://jobicy.com/api/v2/remote-jobs"

    def fetch(self) -> list[Job]:
        self._logger.info("Fetching from Jobicy (keyword=%r)", self.keyword)
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
        results: list[Job] = []

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
