"""
test_exporter.py — Unit tests for exporter.py
==============================================
Tests cover:
- DataFrame construction from job dicts
- CSV byte generation
- Excel byte generation
- File output (CSV and Excel saved to disk)
- Empty job list handling
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import pytest

from exporter import COLUMN_ORDER, DISPLAY_NAMES, DataExporter


@pytest.fixture
def exporter(tmp_path) -> DataExporter:
    """DataExporter instance writing to a temporary directory."""
    return DataExporter(output_dir=str(tmp_path))


class TestBuildDataFrame:
    def test_returns_empty_df_for_no_jobs(self, exporter):
        df = exporter._build_dataframe([])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_correct_column_count(self, exporter, sample_jobs):
        df = exporter._build_dataframe(sample_jobs)
        assert len(df.columns) == len(COLUMN_ORDER)

    def test_columns_renamed_to_display_names(self, exporter, sample_job):
        df = exporter._build_dataframe([sample_job])
        for col in df.columns:
            assert col in DISPLAY_NAMES.values()

    def test_no_nan_values(self, exporter, sample_jobs):
        df = exporter._build_dataframe(sample_jobs)
        assert not df.isnull().any().any()

    def test_row_count_matches_input(self, exporter, sample_jobs):
        df = exporter._build_dataframe(sample_jobs)
        assert len(df) == len(sample_jobs)


class TestToCsv:
    def test_creates_file(self, exporter, sample_jobs, tmp_path):
        path = exporter.to_csv(sample_jobs, "test.csv")
        assert path.exists()
        assert path.suffix == ".csv"

    def test_file_has_correct_rows(self, exporter, sample_jobs, tmp_path):
        path = exporter.to_csv(sample_jobs, "test.csv")
        df = pd.read_csv(path, encoding="utf-8-sig")
        assert len(df) == len(sample_jobs)

    def test_file_has_display_column_names(self, exporter, sample_job, tmp_path):
        path = exporter.to_csv([sample_job], "test.csv")
        df = pd.read_csv(path, encoding="utf-8-sig")
        assert "Job Title" in df.columns
        assert "Company" in df.columns

    def test_empty_jobs_creates_header_only_file(self, exporter, tmp_path):
        path = exporter.to_csv([], "empty.csv")
        df = pd.read_csv(path, encoding="utf-8-sig")
        assert len(df) == 0
        assert len(df.columns) > 0


class TestToExcel:
    def test_creates_xlsx_file(self, exporter, sample_jobs, tmp_path):
        path = exporter.to_excel(sample_jobs, "test.xlsx")
        assert path.exists()
        assert path.suffix == ".xlsx"

    def test_file_has_correct_rows(self, exporter, sample_jobs, tmp_path):
        path = exporter.to_excel(sample_jobs, "test.xlsx")
        df = pd.read_excel(path)
        assert len(df) == len(sample_jobs)

    def test_empty_jobs_creates_header_only_file(self, exporter, tmp_path):
        path = exporter.to_excel([], "empty.xlsx")
        df = pd.read_excel(path)
        assert len(df) == 0


class TestToBytesCsv:
    def test_returns_bytes(self, exporter, sample_jobs):
        result = exporter.to_bytes_csv(sample_jobs)
        assert isinstance(result, bytes)

    def test_bytes_are_valid_csv(self, exporter, sample_jobs):
        raw = exporter.to_bytes_csv(sample_jobs)
        df = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig")
        assert len(df) == len(sample_jobs)

    def test_empty_jobs_returns_header_only_csv(self, exporter):
        raw = exporter.to_bytes_csv([])
        df = pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig")
        assert len(df) == 0


class TestToBytesExcel:
    def test_returns_bytes(self, exporter, sample_jobs):
        result = exporter.to_bytes_excel(sample_jobs)
        assert isinstance(result, bytes)

    def test_bytes_are_valid_xlsx(self, exporter, sample_jobs):
        raw = exporter.to_bytes_excel(sample_jobs)
        df = pd.read_excel(io.BytesIO(raw))
        assert len(df) == len(sample_jobs)

    def test_empty_jobs_returns_valid_xlsx(self, exporter):
        raw = exporter.to_bytes_excel([])
        df = pd.read_excel(io.BytesIO(raw))
        assert len(df) == 0


class TestOutputDirectory:
    def test_creates_output_dir_if_not_exists(self, tmp_path):
        new_dir = tmp_path / "new_subdir" / "exports"
        exporter = DataExporter(output_dir=str(new_dir))
        assert new_dir.exists()

    def test_returns_path_object(self, exporter, sample_job):
        path = exporter.to_csv([sample_job])
        assert isinstance(path, Path)
