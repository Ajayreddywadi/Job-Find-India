"""
conftest.py — Shared pytest fixtures for Job Vacancy Scraper.
Loaded automatically by pytest for all test modules in this package.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def sample_job() -> dict:
    """A single valid job dict matching the unified schema."""
    return {
        "title":       "React Developer",
        "company":     "Acme Corp",
        "location":    "Remote",
        "url":         "https://example.com/job/1",
        "source":      "TestSource",
        "date_posted": "2026-06-16",
        "job_type":    "Remote",
        "tags":        "react, frontend",
        "description": "Build things with React.",
        "salary":      "",
    }


@pytest.fixture
def sample_jobs(sample_job) -> list[dict]:
    """A list of three jobs — one duplicate URL, one different source."""
    job2 = sample_job.copy()
    job2.update(
        {
            "url":     "https://example.com/job/2",
            "source":  "OtherSource",
            "company": "Beta Ltd",
            "tags":    "python, backend",
            "job_type": "Full-time",
        }
    )
    job3 = sample_job.copy()  # duplicate of sample_job (same URL)
    return [sample_job, job2, job3]


@pytest.fixture
def linkedin_api_response() -> str:
    """Fake HTML response from LinkedIn Guest API search page."""
    return """
    <li>
      <div class="base-search-card">
        <a class="base-card__full-link" href="https://example.com/job/linkedin-1"></a>
        <h3 class="base-search-card__title">React Developer</h3>
        <h4 class="base-search-card__subtitle">Infosys</h4>
        <span class="job-search-card__location">Bengaluru, Karnataka, India</span>
        <time class="job-search-card__listdate" datetime="2026-06-16">Today</time>
      </div>
    </li>
    """


@pytest.fixture
def himalayas_api_response() -> dict:
    """Fake Himalayas API payload."""
    return {
        "jobs": [
            {
                "title": "React Developer",
                "companyName": "Acme Corp",
                "applicationLink": "https://example.com/job/1",
                "description": "<p>Build things with React.</p>",
                "categories": ["Software-Engineering", "Frontend"],
                "employmentType": "fullTime",
                "pubDate": 1781589585,
                "locationRestrictions": ["India"],
                "minSalary": 80000,
                "maxSalary": 100000,
                "currency": "USD",
                "salaryPeriod": "annual",
            }
        ],
        "totalCount": 1
    }


@pytest.fixture
def jobicy_api_response() -> dict:
    """Fake Jobicy API payload."""
    return {
        "jobs": [
            {
                "jobTitle": "Python Developer",
                "companyName": "Tech Ltd",
                "url": "https://example.com/job/2",
                "jobDescription": "Build things with Python.",
                "jobGeo": "Worldwide",
                "jobType": ["Full-Time"],
                "pubDate": "2026-06-16T07:07:22+00:00",
                "jobIndustry": ["Software Development"]
            }
        ]
    }


@pytest.fixture
def remotive_api_response() -> dict:
    """Fake Remotive API payload."""
    return {
        "jobs": [
            {
                "id": "3001",
                "url": "https://example.com/job/3",
                "title": "Django Engineer",
                "company_name": "WebShop",
                "publication_date": "2026-06-16T12:00:00Z",
                "candidate_required_location": "India",
                "job_type": "full_time",
                "tags": ["python", "django", "backend"],
                "description": "<p>Build websites with Django.</p>",
                "salary": "USD 70,000/year"
            }
        ]
    }


@pytest.fixture
def arbeitnow_api_response() -> dict:
    """Fake Arbeitnow API payload."""
    return {
        "data": [
            {
                "title": "Backend Developer",
                "company_name": "TechStart",
                "location": "Berlin, Germany",
                "remote": True,
                "url": "https://example.com/job/4",
                "tags": ["golang", "docker"],
                "job_types": ["Full-time"],
                "description": "Work on cloud infrastructure.",
                "created_at": 1781589585
            }
        ]
    }


@pytest.fixture
def unstop_api_response() -> dict:
    """Fake Unstop API payload."""
    return {
        "data": {
            "data": [
                {
                    "title": "Full-Stack Developer",
                    "organisation": {
                        "name": "Persist Ventures"
                    },
                    "seo_url": "https://unstop.com/jobs/full-stack-developer-persist-ventures-1700050",
                    "locations": [
                        {
                            "city": "Mumbai",
                            "state": "Maharashtra",
                            "country": "India"
                        }
                    ],
                    "created_at": "2026-06-16T12:00:00Z",
                    "required_skills": [
                        {"name": "React"},
                        {"name": "Node.js"}
                    ]
                }
            ]
        }
    }
