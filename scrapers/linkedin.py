from typing import Any
from bs4 import BeautifulSoup

from scrapers.base import BaseScraper
from scrapers.registry import register_scraper
from config.settings import MAX_RESULTS_PER_SOURCE
from utils.helpers import _truncate, _empty_job
from models.job import Job

@register_scraper
class LinkedInScraper(BaseScraper):
    """Scraper for LinkedIn via public guest search API."""

    source_name = "LinkedIn"
    _API_URL    = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    def fetch(self) -> list[Job]:
        self._logger.info("Fetching from LinkedIn (keyword=%r, location=%r)", self.keyword, self.location)
        results: list[Job] = []
        loc = self.location or "India"
        params: dict[str, Any] = {
            "keywords": self.keyword,
            "location": loc,
            "start": 0,
        }
        # Avoid thread state pollution by using dynamic headers in request get instead of mutating session
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
