"""
test_scraper.py — Unit tests for scraper.py
============================================
Tests cover:
- Helper functions (_clean_html, _truncate, _empty_job)
- LinkedInScraper with mocked HTML response
- HimalayasScraper with mocked HTTP
- JobicyScraper with mocked HTTP
- RemotiveScraper with mocked HTTP
- ArbeitnowScraper with mocked HTTP
- JobAggregator deduplication, sorting and execution
"""
from __future__ import annotations

import pytest
import responses as resp_mock

from scraper import (
    LinkedInScraper,
    UnstopScraper,
    HimalayasScraper,
    JobicyScraper,
    RemotiveScraper,
    ArbeitnowScraper,
    JobAggregator,
    _clean_html,
    _empty_job,
    _truncate,
)


# ── Helper function tests ─────────────────────────────────────────────────────

class TestCleanHtml:
    def test_strips_tags(self):
        assert _clean_html("<p>Hello <b>World</b></p>") == "Hello World"

    def test_decodes_html_entities(self):
        assert _clean_html("&amp; &quot;") == "& \""

    def test_collapses_whitespace(self):
        assert _clean_html("foo   \n\t  bar") == "foo bar"

    def test_empty_string_returns_empty(self):
        assert _clean_html("") == ""

    def test_none_input_returns_empty(self):
        assert _clean_html(None) == ""  # type: ignore[arg-type]


class TestTruncate:
    def test_short_string_unchanged(self):
        assert _truncate("Hello", max_chars=300) == "Hello"

    def test_long_string_gets_ellipsis(self):
        long = "word " * 100
        result = _truncate(long, max_chars=50)
        assert len(result) <= 50
        assert result.endswith("…")


class TestEmptyJob:
    def test_returns_dict_with_all_keys(self):
        job = _empty_job()
        required = {"title", "company", "location", "url", "source",
                    "date_posted", "job_type", "tags", "description", "salary"}
        assert required == set(job.keys())

    def test_all_values_are_empty_strings(self):
        job = _empty_job()
        assert all(v == "" for v in job.values())


# ── LinkedInScraper tests ──────────────────────────────────────────────────────

class TestLinkedInScraper:
    @resp_mock.activate
    def test_fetch_returns_matching_jobs(self, linkedin_api_response):
        resp_mock.add(
            resp_mock.GET,
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
            body=linkedin_api_response,
            status=200,
        )
        scraper = LinkedInScraper(keyword="react", location="India")
        jobs = scraper.fetch()

        assert len(jobs) == 1
        job = jobs[0]
        assert job["title"] == "React Developer"
        assert job["company"] == "Infosys"
        assert job["source"] == "LinkedIn"
        assert job["location"] == "Bengaluru, Karnataka, India"


# ── UnstopScraper tests ────────────────────────────────────────────────────────

class TestUnstopScraper:
    @resp_mock.activate
    def test_fetch_returns_matching_jobs(self, unstop_api_response):
        resp_mock.add(
            resp_mock.GET,
            "https://unstop.com/api/public/opportunity/search-result",
            json=unstop_api_response,
            status=200,
        )
        scraper = UnstopScraper(keyword="developer", location="India")
        jobs = scraper.fetch()

        # Fetches for both "jobs" and "internships" (so 2 total)
        assert len(jobs) == 2
        job = jobs[0]
        assert job["title"] == "Full-Stack Developer"
        assert job["company"] == "Persist Ventures"
        assert job["source"] == "Unstop"
        assert job["location"] == "Mumbai, Maharashtra, India"


# ── HimalayasScraper tests ─────────────────────────────────────────────────────

class TestHimalayasScraper:
    @resp_mock.activate
    def test_fetch_returns_matching_jobs(self, himalayas_api_response):
        resp_mock.add(
            resp_mock.GET,
            "https://himalayas.app/jobs/api",
            json=himalayas_api_response,
            status=200,
        )
        scraper = HimalayasScraper(keyword="react", location="India")
        jobs = scraper.fetch()

        assert len(jobs) == 1
        job = jobs[0]
        assert job["title"] == "React Developer"
        assert job["company"] == "Acme Corp"
        assert job["source"] == "Himalayas"
        assert job["location"] == "India"
        assert job["salary"] == "USD 80,000–100,000/annual"


# ── JobicyScraper tests ────────────────────────────────────────────────────────

class TestJobicyScraper:
    @resp_mock.activate
    def test_fetch_returns_matching_jobs(self, jobicy_api_response):
        resp_mock.add(
            resp_mock.GET,
            "https://jobicy.com/api/v2/remote-jobs",
            json=jobicy_api_response,
            status=200,
        )
        scraper = JobicyScraper(keyword="python", location="Worldwide")
        jobs = scraper.fetch()

        assert len(jobs) == 1
        job = jobs[0]
        assert job["title"] == "Python Developer"
        assert job["company"] == "Tech Ltd"
        assert job["source"] == "Jobicy"
        assert job["location"] == "Worldwide"


# ── RemotiveScraper tests ──────────────────────────────────────────────────────

class TestRemotiveScraper:
    @resp_mock.activate
    def test_fetch_returns_matching_jobs(self, remotive_api_response):
        resp_mock.add(
            resp_mock.GET,
            "https://remotive.com/api/remote-jobs",
            json=remotive_api_response,
            status=200,
        )
        scraper = RemotiveScraper(keyword="django", location="India")
        jobs = scraper.fetch()

        assert len(jobs) == 1
        job = jobs[0]
        assert job["title"] == "Django Engineer"
        assert job["company"] == "WebShop"
        assert job["source"] == "Remotive"
        assert job["location"] == "India"
        assert job["salary"] == "USD 70,000/year"


# ── ArbeitnowScraper tests ─────────────────────────────────────────────────────

class TestArbeitnowScraper:
    @resp_mock.activate
    def test_fetch_returns_matching_jobs(self, arbeitnow_api_response):
        resp_mock.add(
            resp_mock.GET,
            "https://www.arbeitnow.com/api/job-board-api",
            json=arbeitnow_api_response,
            status=200,
        )
        scraper = ArbeitnowScraper(keyword="backend", location="Germany")
        jobs = scraper.fetch()

        assert len(jobs) == 1
        job = jobs[0]
        assert job["title"] == "Backend Developer"
        assert job["company"] == "TechStart"
        assert job["source"] == "Arbeitnow"
        assert job["location"] == "Berlin, Germany (Remote)"


# ── JobAggregator tests ────────────────────────────────────────────────────────

class TestJobAggregator:
    def test_deduplicate_removes_duplicate_urls(self, sample_jobs):
        agg = JobAggregator(keyword="python")
        unique = agg._deduplicate(sample_jobs)
        assert len(unique) == 2

    def test_build_scrapers_returns_six(self):
        agg = JobAggregator(keyword="react")
        scrapers = agg._build_scrapers()
        assert len(scrapers) == 6
        sources = {s.source_name for s in scrapers}
        assert sources == {"LinkedIn", "Unstop", "Himalayas", "Jobicy", "Remotive", "Arbeitnow"}

    @resp_mock.activate
    def test_run_returns_sorted_by_date_desc(
        self,
        linkedin_api_response,
        unstop_api_response,
        himalayas_api_response,
        jobicy_api_response,
        remotive_api_response,
        arbeitnow_api_response
    ):
        resp_mock.add(
            resp_mock.GET,
            "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
            body=linkedin_api_response,
            status=200,
        )
        resp_mock.add(
            resp_mock.GET,
            "https://unstop.com/api/public/opportunity/search-result",
            json=unstop_api_response,
            status=200,
        )
        resp_mock.add(
            resp_mock.GET,
            "https://himalayas.app/jobs/api",
            json=himalayas_api_response,
            status=200,
        )
        resp_mock.add(
            resp_mock.GET,
            "https://jobicy.com/api/v2/remote-jobs",
            json=jobicy_api_response,
            status=200,
        )
        resp_mock.add(
            resp_mock.GET,
            "https://remotive.com/api/remote-jobs",
            json=remotive_api_response,
            status=200,
        )
        resp_mock.add(
            resp_mock.GET,
            "https://www.arbeitnow.com/api/job-board-api",
            json=arbeitnow_api_response,
            status=200,
        )

        # Set keyword to a broad term so all mocked jobs match
        agg = JobAggregator(keyword="developer", location="India")
        jobs = agg.run()
        
        assert len(jobs) > 0
        dates = [j["date_posted"] for j in jobs if j["date_posted"]]
        assert dates == sorted(dates, reverse=True)
