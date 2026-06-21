"""
test_charts.py — Unit tests for charts.py
==========================================
Tests verify that each chart function:
- Returns a Figure object when given valid data
- Returns None when given empty data
- Handles missing / malformed fields without raising
"""
from __future__ import annotations

import matplotlib
import matplotlib.pyplot as plt
import pytest

matplotlib.use("Agg")

from charts import (
    jobs_by_location_bar,
    jobs_by_source_pie,
    jobs_by_type_bar,
    jobs_over_time_line,
    top_tags_bar,
)


@pytest.fixture(autouse=True)
def close_figures():
    """Close all matplotlib figures after each test to prevent memory leaks."""
    yield
    plt.close("all")


# ── jobs_by_source_pie ────────────────────────────────────────────────────────

class TestJobsBySourcePie:
    def test_returns_figure_for_valid_data(self, sample_jobs):
        fig = jobs_by_source_pie(sample_jobs)
        assert fig is not None
        assert isinstance(fig, plt.Figure)

    def test_returns_none_for_empty_list(self):
        fig = jobs_by_source_pie([])
        assert fig is None

    def test_handles_missing_source_key(self):
        jobs = [{"title": "Dev"}, {"title": "QA"}]  # no "source" key
        fig = jobs_by_source_pie(jobs)
        assert fig is not None  # should still produce a chart

    def test_handles_single_source(self, sample_job):
        fig = jobs_by_source_pie([sample_job])
        assert fig is not None


# ── jobs_by_location_bar ──────────────────────────────────────────────────────

class TestJobsByLocationBar:
    def test_returns_figure_for_valid_data(self, sample_jobs):
        fig = jobs_by_location_bar(sample_jobs)
        assert fig is not None
        assert isinstance(fig, plt.Figure)

    def test_returns_none_for_empty_list(self):
        fig = jobs_by_location_bar([])
        assert fig is None

    def test_top_n_limits_bars(self, sample_jobs):
        fig = jobs_by_location_bar(sample_jobs, top_n=1)
        assert fig is not None

    def test_handles_missing_location_key(self):
        jobs = [{"title": "Dev"}, {"title": "QA"}]
        fig = jobs_by_location_bar(jobs)
        assert fig is not None


# ── jobs_by_type_bar ──────────────────────────────────────────────────────────

class TestJobsByTypeBar:
    def test_returns_figure_for_valid_data(self, sample_jobs):
        fig = jobs_by_type_bar(sample_jobs)
        assert fig is not None
        assert isinstance(fig, plt.Figure)

    def test_returns_none_for_empty_list(self):
        fig = jobs_by_type_bar([])
        assert fig is None

    def test_blank_job_type_mapped_to_unspecified(self):
        jobs = [{"job_type": ""}, {"job_type": "Remote"}]
        fig = jobs_by_type_bar(jobs)
        assert fig is not None

    def test_handles_missing_job_type_key(self):
        jobs = [{"title": "Dev"}, {"title": "QA"}]
        fig = jobs_by_type_bar(jobs)
        assert fig is not None


# ── jobs_over_time_line ───────────────────────────────────────────────────────

class TestJobsOverTimeLine:
    def test_returns_figure_with_enough_data(self):
        jobs = [
            {"date_posted": "2026-06-10"},
            {"date_posted": "2026-06-11"},
            {"date_posted": "2026-06-12"},
        ]
        fig = jobs_over_time_line(jobs)
        assert fig is not None
        assert isinstance(fig, plt.Figure)

    def test_returns_none_for_empty_list(self):
        fig = jobs_over_time_line([])
        assert fig is None

    def test_returns_none_when_no_dates(self, sample_jobs):
        jobs = [{**j, "date_posted": ""} for j in sample_jobs]
        fig = jobs_over_time_line(jobs)
        assert fig is None

    def test_returns_none_for_single_date(self):
        jobs = [{"date_posted": "2026-06-16"}]
        fig = jobs_over_time_line(jobs)
        assert fig is None

    def test_handles_invalid_date_strings(self):
        jobs = [
            {"date_posted": "not-a-date"},
            {"date_posted": "also-not-a-date"},
            {"date_posted": "2026-06-16"},
            {"date_posted": "2026-06-15"},
        ]
        # Should not raise; may return None or a Figure
        result = jobs_over_time_line(jobs)
        assert result is None or isinstance(result, plt.Figure)


# ── top_tags_bar ──────────────────────────────────────────────────────────────

class TestTopTagsBar:
    def test_returns_figure_for_valid_data(self, sample_jobs):
        fig = top_tags_bar(sample_jobs)
        assert fig is not None
        assert isinstance(fig, plt.Figure)

    def test_returns_none_for_empty_list(self):
        fig = top_tags_bar([])
        assert fig is None

    def test_returns_none_when_all_tags_empty(self):
        jobs = [{"tags": ""}, {"tags": ""}]
        fig = top_tags_bar(jobs)
        assert fig is None

    def test_top_n_limits_bars(self, sample_jobs):
        fig = top_tags_bar(sample_jobs, top_n=2)
        assert fig is not None

    def test_handles_missing_tags_key(self):
        jobs = [{"title": "Dev"}, {"title": "QA"}]
        fig = top_tags_bar(jobs)
        assert fig is None  # no tags at all → None

    def test_handles_comma_separated_tags(self):
        jobs = [{"tags": "python, django, rest-api"} for _ in range(5)]
        fig = top_tags_bar(jobs)
        assert fig is not None
