import datetime
from scrapers.base import BaseScraper
from scrapers.registry import register_scraper
from config.settings import MAX_RESULTS_PER_SOURCE
from utils.helpers import _clean_html, _truncate, _empty_job
from models.job import Job

@register_scraper
class ArbeitnowScraper(BaseScraper):
    """Scraper for Arbeitnow (https://www.arbeitnow.com/api/job-board-api)."""

    source_name = "Arbeitnow"
    _API_URL    = "https://www.arbeitnow.com/api/job-board-api"

    def fetch(self) -> list[Job]:
        self._logger.info("Fetching from Arbeitnow (keyword=%r)", self.keyword)
        results: list[Job] = []
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
