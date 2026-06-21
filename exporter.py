"""
exporter.py — Job Vacancy Scraper
==================================
Handles CSV and Excel export of aggregated job result data.

Classes
-------
DataExporter
    .to_csv(jobs, filename)   → pathlib.Path
    .to_excel(jobs, filename) → pathlib.Path
    .to_bytes_csv(jobs)       → bytes   (for Streamlit download button)
    .to_bytes_excel(jobs)     → bytes   (for Streamlit download button)

Author : Job Vacancy Scraper Project
Version: 1.0.0
Updated: 2026-06-16
"""

from __future__ import annotations

import io
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# ── Column configuration ───────────────────────────────────────────────────────

COLUMN_ORDER = [
    "title",
    "company",
    "location",
    "job_type",
    "tags",
    "date_posted",
    "source",
    "url",
    "description",
]

DISPLAY_NAMES = {
    "title":       "Job Title",
    "company":     "Company",
    "location":    "Location",
    "job_type":    "Job Type",
    "tags":        "Tags",
    "date_posted": "Date Posted",
    "source":      "Source",
    "url":         "URL",
    "description": "Description",
}

# Max width for any Excel column (characters)
_MAX_COL_WIDTH = 60


class DataExporter:
    """Exports a list of job dicts to CSV or Excel files (or in-memory bytes)."""

    def __init__(self, output_dir: str = "data") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _build_dataframe(self, jobs: list[dict[str, str]]) -> pd.DataFrame:
        """Convert list of job dicts to a clean, ordered DataFrame."""
        if not jobs:
            return pd.DataFrame(columns=[DISPLAY_NAMES.get(c, c) for c in COLUMN_ORDER])

        df = pd.DataFrame(jobs)
        # Keep only known columns, in the defined order
        cols = [c for c in COLUMN_ORDER if c in df.columns]
        df = df[cols].rename(columns=DISPLAY_NAMES)
        # Fill any blanks with empty string (avoid NaN in exports)
        df = df.fillna("")
        return df

    @staticmethod
    def _apply_excel_formatting(writer: pd.ExcelWriter, df: pd.DataFrame) -> None:
        """Apply column widths, header styling, and freeze pane to worksheet."""
        workbook = writer.book
        worksheet = writer.sheets["Jobs"]

        # Header format — bold, light blue background
        header_fmt = workbook.add_format(  # type: ignore[attr-defined]
            {
                "bold": True,
                "bg_color": "#1E3A5F",
                "font_color": "#FFFFFF",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }
        )

        # Cell format — light alternating rows handled by table style
        cell_fmt = workbook.add_format(  # type: ignore[attr-defined]
            {"valign": "top", "text_wrap": True, "border": 1}
        )

        url_fmt = workbook.add_format(  # type: ignore[attr-defined]
            {
                "font_color": "#1565C0",
                "underline": True,
                "valign": "top",
            }
        )

        # Auto-size columns
        for col_idx, col_name in enumerate(df.columns):
            max_content = df[col_name].astype(str).str.len().max() if len(df) > 0 else 0
            width = min(max(int(max_content), len(col_name)) + 4, _MAX_COL_WIDTH)
            worksheet.set_column(col_idx, col_idx, width, cell_fmt)

            # Write header cell with special format
            worksheet.write(0, col_idx, col_name, header_fmt)

        # Make URLs clickable
        if "URL" in df.columns:
            url_col_idx = list(df.columns).index("URL")
            for row_idx, url_val in enumerate(df["URL"], start=1):
                if url_val and url_val.startswith("http"):
                    worksheet.write_url(row_idx, url_col_idx, url_val, url_fmt, url_val)

        # Freeze top row
        worksheet.freeze_panes(1, 0)
        # Set row height for header
        worksheet.set_row(0, 22)

    # ── Public API ─────────────────────────────────────────────────────────────

    def to_csv(
        self,
        jobs: list[dict[str, str]],
        filename: str = "jobs_export.csv",
    ) -> Path:
        """Write jobs to a CSV file and return the path.

        Args:
            jobs: List of job dicts conforming to the unified schema.
            filename: Output filename (saved inside the configured output_dir).

        Returns:
            Absolute path to the written CSV file.
        """
        path = self._output_dir / filename
        df = self._build_dataframe(jobs)
        # utf-8-sig BOM ensures Excel on Windows opens with correct encoding
        df.to_csv(path, index=False, encoding="utf-8-sig")
        logger.info("CSV exported: %s (%d rows)", path, len(df))
        return path

    def to_excel(
        self,
        jobs: list[dict[str, str]],
        filename: str = "jobs_export.xlsx",
    ) -> Path:
        """Write jobs to a formatted Excel file and return the path.

        Args:
            jobs: List of job dicts conforming to the unified schema.
            filename: Output filename (saved inside the configured output_dir).

        Returns:
            Absolute path to the written Excel file.
        """
        path = self._output_dir / filename
        df = self._build_dataframe(jobs)

        try:
            with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Jobs")
                self._apply_excel_formatting(writer, df)
        except ImportError:
            # Fallback to openpyxl if xlsxwriter not available
            logger.warning("xlsxwriter not found, falling back to openpyxl")
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Jobs")
                ws = writer.sheets["Jobs"]
                for col_idx, col_name in enumerate(df.columns, 1):
                    max_len = max(
                        df[col_name].astype(str).str.len().max() if len(df) > 0 else 0,
                        len(col_name),
                    )
                    col_letter = ws.cell(1, col_idx).column_letter
                    ws.column_dimensions[col_letter].width = min(max_len + 4, _MAX_COL_WIDTH)

        logger.info("Excel exported: %s (%d rows)", path, len(df))
        return path

    def to_bytes_csv(self, jobs: list[dict[str, str]]) -> bytes:
        """Return CSV content as bytes (for Streamlit st.download_button).

        Args:
            jobs: List of job dicts conforming to the unified schema.

        Returns:
            UTF-8-BOM encoded CSV bytes.
        """
        df = self._build_dataframe(jobs)
        return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    def to_bytes_excel(self, jobs: list[dict[str, str]]) -> bytes:
        """Return Excel content as bytes (for Streamlit st.download_button).

        Args:
            jobs: List of job dicts conforming to the unified schema.

        Returns:
            Raw .xlsx bytes.
        """
        df = self._build_dataframe(jobs)
        buffer = io.BytesIO()
        try:
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="Jobs")
                self._apply_excel_formatting(writer, df)
        except ImportError:
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Jobs")
        return buffer.getvalue()
