from typing import Any

from scrapers.base import BaseScraper
from scrapers.registry import register_scraper
from config.settings import MAX_RESULTS_PER_SOURCE
from utils.helpers import _truncate, _empty_job
from models.job import Job

@register_scraper
class UnstopScraper(BaseScraper):
    """Scraper for Unstop (https://unstop.com/api/public/opportunity/search-result)."""

    source_name = "Unstop"
    _API_URL    = "https://unstop.com/api/public/opportunity/search-result"

    def fetch(self) -> list[Job]:
        self._logger.info("Fetching from Unstop (keyword=%r, location=%r)", self.keyword, self.location)
        results: list[Job] = []
        opportunity_types = ["jobs", "internships"]
        # Avoid thread state pollution by using dynamic headers in request get instead of mutating session
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
