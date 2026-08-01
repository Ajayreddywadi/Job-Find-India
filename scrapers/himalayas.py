import datetime
from typing import Any

from scrapers.base import BaseScraper
from scrapers.registry import register_scraper
from config.settings import MAX_RESULTS_PER_SOURCE
from utils.helpers import _clean_html, _truncate, _empty_job
from models.job import Job

@register_scraper
class HimalayasScraper(BaseScraper):
    """Scraper for Himalayas (https://himalayas.app/jobs/api)."""

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

    def fetch(self) -> list[Job]:
        self._logger.info("Fetching from Himalayas (keyword=%r)", self.keyword)
        results: list[Job] = []
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
