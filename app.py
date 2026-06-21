"""
app.py — Job Vacancy Scraper
==============================
Streamlit dashboard — entry point for the application.

Run with:
    streamlit run app.py

Author : Job Vacancy Scraper Project
Version: 1.0.0
Updated: 2026-06-16
"""

from __future__ import annotations

import logging
from datetime import datetime

import pandas as pd
import streamlit as st

from charts import (
    jobs_by_location_bar,
    jobs_by_source_pie,
    jobs_by_type_bar,
    jobs_over_time_line,
    top_tags_bar,
)
from exporter import DataExporter
from scraper import JobAggregator

# ── Page config (must be first Streamlit call) ─────────────────────────────────
st.set_page_config(
    page_title="Job Vacancy Scraper",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

logger = logging.getLogger("app")

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Base & fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── App background ── */
    .stApp {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        color: #E2E8F0;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #1E293B !important;
        border-right: 1px solid #334155;
    }
    [data-testid="stSidebar"] * {
        color: #CBD5E1 !important;
    }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1E3A5F, #1E293B);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #38BDF8 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #94A3B8 !important;
        font-size: 0.85rem !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #1565C0, #0D47A1) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.5rem 2rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(21,101,192,0.4) !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 16px rgba(21,101,192,0.6) !important;
    }

    /* ── Download buttons ── */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #065F46, #047857) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    .stDownloadButton > button:hover {
        transform: translateY(-1px) !important;
    }

    /* ── Text inputs ── */
    .stTextInput > div > div > input {
        background: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        color: #E2E8F0 !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #38BDF8 !important;
        box-shadow: 0 0 0 2px rgba(56,189,248,0.2) !important;
    }

    /* ── Select boxes ── */
    .stSelectbox > div > div {
        background: #1E293B !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        color: #E2E8F0 !important;
    }

    /* ── Dataframe ── */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #334155;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        background: #1E293B;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #94A3B8 !important;
        border-radius: 8px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: #1565C0 !important;
        color: white !important;
    }

    /* ── Section headers ── */
    .section-header {
        font-size: 1.2rem;
        font-weight: 600;
        color: #38BDF8;
        margin-bottom: 0.5rem;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid #334155;
    }

    /* ── Job card ── */
    .job-card {
        background: linear-gradient(135deg, #1E293B, #0F172A);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .job-card:hover {
        border-color: #38BDF8;
        box-shadow: 0 4px 20px rgba(56,189,248,0.15);
    }
    .job-title {
        font-size: 1.05rem;
        font-weight: 600;
        color: #F1F5F9;
    }
    .job-meta {
        font-size: 0.82rem;
        color: #64748B;
        margin-top: 4px;
    }
    .job-tag {
        display: inline-block;
        background: #1E3A5F;
        color: #93C5FD;
        border-radius: 4px;
        padding: 1px 7px;
        font-size: 0.72rem;
        margin: 2px 2px 0 0;
        font-weight: 500;
    }
    .badge-source {
        display: inline-block;
        background: #14532D;
        color: #86EFAC;
        border-radius: 4px;
        padding: 1px 8px;
        font-size: 0.72rem;
        font-weight: 600;
    }
    .badge-type {
        display: inline-block;
        background: #3B1D8C;
        color: #C4B5FD;
        border-radius: 4px;
        padding: 1px 8px;
        font-size: 0.72rem;
        font-weight: 600;
        margin-left: 4px;
    }

    /* ── Alert / info boxes ── */
    .stAlert {
        border-radius: 10px !important;
    }

    /* ── Divider ── */
    hr {
        border-color: #334155 !important;
    }

    /* ── Spinner ── */
    .stSpinner > div {
        border-top-color: #38BDF8 !important;
    }

    /* ── Footer ── */
    .footer {
        text-align: center;
        color: #475569;
        font-size: 0.78rem;
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #334155;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Session state helpers ─────────────────────────────────────────────────────

def _init_state() -> None:
    """Initialise session-state keys on first load."""
    defaults: dict = {
        "jobs": [],
        "searched": False,
        "keyword": "",
        "location": "India",
        "did_you_mean": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ── Sidebar ───────────────────────────────────────────────────────────────────

def _render_sidebar() -> tuple[str, str, bool]:
    """Render sidebar controls and return (keyword, location, search_clicked)."""
    with st.sidebar:
        st.markdown(
            """
            <div style='text-align:center; padding: 10px 0 20px'>
                <div style='font-size:2.5rem'>💼</div>
                <div style='font-size:1.2rem; font-weight:700; color:#38BDF8'>
                    Job Find India
                </div>
                <div style='font-size:0.78rem; color:#64748B; margin-top:4px'>
                    Real-time multi-source aggregator
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### 🔍 Search Parameters")
        keyword = st.text_input(
            "Keyword",
            placeholder="e.g. Python Developer, Data Analyst…",
            help="Search by job title, skill, or keyword",
            value=st.session_state.keyword,
        )

        # Autocomplete suggestions for keyword
        from utils.skills import get_skill_suggestions
        suggestions = get_skill_suggestions(keyword)
        if suggestions:
            st.markdown("<div style='font-size:0.75rem;color:#64748B;margin-top:-6px;margin-bottom:6px'>Suggestions:</div>", unsafe_allow_html=True)
            cols = st.columns(len(suggestions))
            for i, sug in enumerate(suggestions):
                with cols[i]:
                    if st.button(sug, key=f"sug_btn_{i}", use_container_width=True):
                        st.session_state.keyword = sug
                        st.rerun()

        # Searchable Dropdown for Cities
        from utils.cities import get_indian_cities
        cities_list = get_indian_cities()
        
        default_index = 0
        if st.session_state.location in cities_list:
            default_index = cities_list.index(st.session_state.location)
        elif "India" in cities_list:
            default_index = cities_list.index("India")

        location = st.selectbox(
            "Location",
            options=cities_list,
            index=default_index,
            help="Select an Indian city or Remote/India",
        )

        search_clicked = st.button("🚀 Search Jobs", use_container_width=True)

        st.markdown("---")
        st.markdown("### 📡 Data Sources")
        for src, icon in [
            ("LinkedIn", "💼"),
            ("Unstop", "🎓"),
            ("Himalayas", "🏔️"),
            ("Jobicy", "🌎"),
            ("Remotive", "💡"),
            ("Arbeitnow", "🏢"),
        ]:
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:8px;"
                f"padding:6px 0;color:#94A3B8'>{icon} {src}</div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown(
            "<div style='color:#475569;font-size:0.75rem;text-align:center'>"
            "All APIs are public & key-free<br>Data © respective sources"
            "</div>",
            unsafe_allow_html=True,
        )

    return keyword.strip(), location.strip(), search_clicked


# ── Metric row ────────────────────────────────────────────────────────────────

def _render_metrics(jobs: list[dict]) -> None:
    sources = {j.get("source", "") for j in jobs}
    remote_count = sum(1 for j in jobs if "remote" in j.get("job_type", "").lower() or
                       "remote" in j.get("location", "").lower())
    latest = max((j.get("date_posted", "") for j in jobs), default="")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🔎 Total Jobs", len(jobs))
    c2.metric("📡 Sources", len(sources))
    c3.metric("🌍 Remote Jobs", remote_count)
    c4.metric("📅 Latest Post", latest or "—")


# ── Filters panel ─────────────────────────────────────────────────────────────

def _apply_filters(jobs: list[dict]) -> list[dict]:
    """Render inline filter widgets and return filtered job list."""
    if not jobs:
        return jobs

    sources = sorted({j.get("source", "") for j in jobs if j.get("source")})
    job_types = sorted({j.get("job_type", "") for j in jobs if j.get("job_type")})

    with st.expander("🎛️ Filter Results", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            sel_sources = st.multiselect(
                "Source", sources, default=sources, key="flt_source"
            )
        with col2:
            sel_types = st.multiselect(
                "Job Type", job_types, default=job_types, key="flt_type"
            )
        with col3:
            sort_by = st.selectbox(
                "Sort by",
                ["Date (newest)", "Date (oldest)", "Company A-Z", "Title A-Z"],
                key="flt_sort",
            )

    filtered = [
        j for j in jobs
        if j.get("source", "") in sel_sources
        and (j.get("job_type", "") in sel_types or not j.get("job_type"))
    ]

    sort_map = {
        "Date (newest)": lambda j: j.get("date_posted", "") or "",
        "Date (oldest)": lambda j: j.get("date_posted", "") or "",
        "Company A-Z":   lambda j: j.get("company", "").lower(),
        "Title A-Z":     lambda j: j.get("title", "").lower(),
    }
    reverse = sort_by in ("Date (newest)",)
    filtered.sort(key=sort_map[sort_by], reverse=reverse)

    return filtered


# ── Job cards view ────────────────────────────────────────────────────────────

def _render_job_cards(jobs: list[dict], page_size: int = 20) -> None:
    """Render paginated job cards."""
    if not jobs:
        st.info("No jobs match the current filters.")
        return

    total = len(jobs)
    total_pages = max(1, (total + page_size - 1) // page_size)

    col_info, col_nav = st.columns([3, 1])
    with col_info:
        st.markdown(
            f"<div style='color:#64748B;font-size:0.85rem'>"
            f"Showing <b style='color:#38BDF8'>{total}</b> results</div>",
            unsafe_allow_html=True,
        )
    with col_nav:
        page = st.number_input(
            "Page", min_value=1, max_value=total_pages, value=1, key="card_page"
        )

    start = (page - 1) * page_size
    page_jobs = jobs[start : start + page_size]

    for job in page_jobs:
        title = job.get("title", "Untitled")
        company = job.get("company", "Unknown")
        location = job.get("location", "")
        url = job.get("url", "")
        source = job.get("source", "")
        job_type = job.get("job_type", "")
        date_posted = job.get("date_posted", "")
        tags = job.get("tags", "")
        description = job.get("description", "")

        tags_html = "".join(
            f"<span class='job-tag'>{t.strip()}</span>"
            for t in tags.split(",") if t.strip()
        )
        source_badge = f"<span class='badge-source'>{source}</span>" if source else ""
        type_badge = f"<span class='badge-type'>{job_type}</span>" if job_type else ""
        title_link = f"<a href='{url}' target='_blank' style='color:#38BDF8;text-decoration:none'>{title}</a>" if url else title

        st.markdown(
            f"""
            <div class='job-card'>
                <div class='job-title'>{title_link}</div>
                <div class='job-meta'>
                    🏢 {company} &nbsp;|&nbsp; 📍 {location}
                    {"&nbsp;|&nbsp; 📅 " + date_posted if date_posted else ""}
                    &nbsp;&nbsp; {source_badge} {type_badge}
                </div>
                {"<div style='margin-top:8px;font-size:0.82rem;color:#94A3B8'>" + description[:200] + ("…" if len(description) > 200 else "") + "</div>" if description else ""}
                {"<div style='margin-top:8px'>" + tags_html + "</div>" if tags_html else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )


# ── Table view ────────────────────────────────────────────────────────────────

def _render_table(jobs: list[dict]) -> None:
    if not jobs:
        st.info("No jobs to display.")
        return

    df = pd.DataFrame(jobs)[
        ["title", "company", "location", "job_type", "tags", "date_posted", "source", "url"]
    ].rename(
        columns={
            "title": "Title",
            "company": "Company",
            "location": "Location",
            "job_type": "Type",
            "tags": "Tags",
            "date_posted": "Date",
            "source": "Source",
            "url": "URL",
        }
    )
    st.dataframe(df, use_container_width=True, height=500)


# ── Analytics tab ─────────────────────────────────────────────────────────────

def _render_analytics(jobs: list[dict]) -> None:
    if not jobs:
        st.info("Run a search first to see analytics.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='section-header'>Jobs by Source</div>", unsafe_allow_html=True)
        fig = jobs_by_source_pie(jobs)
        if fig:
            st.pyplot(fig, use_container_width=True)

    with col2:
        st.markdown("<div class='section-header'>Jobs by Type</div>", unsafe_allow_html=True)
        fig = jobs_by_type_bar(jobs)
        if fig:
            st.pyplot(fig, use_container_width=True)

    st.markdown("---")

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("<div class='section-header'>Top Locations</div>", unsafe_allow_html=True)
        fig = jobs_by_location_bar(jobs, top_n=10)
        if fig:
            st.pyplot(fig, use_container_width=True)

    with col4:
        st.markdown("<div class='section-header'>Top Skill Tags</div>", unsafe_allow_html=True)
        fig = top_tags_bar(jobs, top_n=15)
        if fig:
            st.pyplot(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("<div class='section-header'>Posting Trend</div>", unsafe_allow_html=True)
    fig = jobs_over_time_line(jobs)
    if fig:
        st.pyplot(fig, use_container_width=True)
    else:
        st.info("Not enough date data to plot a trend.")


# ── Export tab ────────────────────────────────────────────────────────────────

def _render_export(jobs: list[dict]) -> None:
    if not jobs:
        st.info("Run a search first to export results.")
        return

    exporter = DataExporter()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    st.markdown("### 📁 Download Results")
    st.markdown(
        f"<div style='color:#64748B;margin-bottom:1rem'>"
        f"{len(jobs)} jobs ready for export</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            <div style='background:#1E293B;border:1px solid #334155;border-radius:12px;
            padding:20px;text-align:center;margin-bottom:1rem'>
                <div style='font-size:2rem'>📄</div>
                <div style='font-weight:600;color:#E2E8F0;margin:8px 0'>CSV Export</div>
                <div style='font-size:0.82rem;color:#64748B'>
                    Comma-separated values<br>Compatible with Excel, Google Sheets
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        csv_bytes = exporter.to_bytes_csv(jobs)
        st.download_button(
            label="⬇️ Download CSV",
            data=csv_bytes,
            file_name=f"jobs_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col2:
        st.markdown(
            """
            <div style='background:#1E293B;border:1px solid #334155;border-radius:12px;
            padding:20px;text-align:center;margin-bottom:1rem'>
                <div style='font-size:2rem'>📊</div>
                <div style='font-weight:600;color:#E2E8F0;margin:8px 0'>Excel Export</div>
                <div style='font-size:0.82rem;color:#64748B'>
                    Formatted .xlsx with clickable URLs<br>Auto-sized columns
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        try:
            xlsx_bytes = exporter.to_bytes_excel(jobs)
            st.download_button(
                label="⬇️ Download Excel",
                data=xlsx_bytes,
                file_name=f"jobs_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as exc:
            st.error(f"Excel export failed: {exc}")

    st.markdown("---")
    st.markdown("### 💾 Save to Disk")
    col3, col4 = st.columns(2)
    with col3:
        if st.button("Save CSV to /data", use_container_width=True):
            path = exporter.to_csv(jobs, f"jobs_{timestamp}.csv")
            st.success(f"Saved: {path}")
    with col4:
        if st.button("Save Excel to /data", use_container_width=True):
            try:
                path = exporter.to_excel(jobs, f"jobs_{timestamp}.xlsx")
                st.success(f"Saved: {path}")
            except Exception as exc:
                st.error(f"Failed: {exc}")


# ── Main app ──────────────────────────────────────────────────────────────────

def main() -> None:
    _init_state()

    # Header
    st.markdown(
        """
        <div style='text-align:center;padding:2rem 0 1.5rem'>
            <h1 style='font-size:2.8rem;font-weight:800;margin:0;
               background:linear-gradient(90deg,#38BDF8,#818CF8);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent'>
                💼 Job Find India
            </h1>
            <p style='color:#64748B;margin:8px 0 0;font-size:1rem'>
                Real-time job aggregation from LinkedIn · Unstop · Himalayas · Jobicy · Remotive · Arbeitnow
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    keyword, location, search_clicked = _render_sidebar()

    # Trigger search
    if search_clicked:
        if not keyword:
            st.warning("⚠️ Please enter a keyword to search.")
        else:
            st.session_state.keyword = keyword
            st.session_state.location = location
            
            # Check for spelling correction (synonyms / normalizer)
            from utils.normalizer import normalize_keyword
            normalized = normalize_keyword(keyword)
            if normalized.lower() != keyword.lower():
                st.session_state.did_you_mean = normalized.title()
            else:
                st.session_state.did_you_mean = None
                
            with st.spinner(f"🔍 Searching for **{keyword}** jobs across 6 sources…"):
                aggregator = JobAggregator(keyword=keyword, location=location)
                jobs = aggregator.run()
            st.session_state.jobs = jobs
            st.session_state.searched = True

    jobs: list[dict] = st.session_state.jobs

    # Did you mean spelling check
    if st.session_state.searched and st.session_state.get("did_you_mean"):
        st.markdown(
            f"""
            <div style='background:#1E293B;border-left:4px solid #F59E0B;padding:12px 16px;border-radius:8px;margin-bottom:16px'>
                <div style='color:#64748B;font-size:0.82rem'>Searching for: <i>{st.session_state.keyword}</i></div>
                <div style='color:#F59E0B;font-weight:600;font-size:0.95rem;margin:4px 0'>Did you mean: {st.session_state.did_you_mean}?</div>
                <div style='color:#E2E8F0;font-size:0.88rem'>Showing results for <b>{st.session_state.did_you_mean}</b>.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # City-based fallback warning
    is_fallback = False
    if st.session_state.searched and jobs:
        loc = st.session_state.location
        if loc and loc not in ["India", "Remote"]:
            city_match = [j for j in jobs if loc.lower() in j.get("location", "").lower()]
            if not city_match:
                st.info(f"ℹ️ No jobs found in **{loc}**. Showing nearby or Remote opportunities.")

    # Landing state
    if not st.session_state.searched:
        st.markdown(
            """
            <div style='text-align:center;padding:4rem 2rem;
               background:linear-gradient(135deg,#1E293B,#0F172A);
               border:1px solid #334155;border-radius:16px;margin-top:2rem'>
                <div style='font-size:4rem;margin-bottom:1rem'>🚀</div>
                <h3 style='color:#E2E8F0;font-weight:600;margin:0 0 0.5rem'>
                    Ready to find your next opportunity?
                </h3>
                <p style='color:#64748B;margin:0'>
                    Enter a keyword in the sidebar and click <b style='color:#38BDF8'>Search Jobs</b>
                </p>
                <div style='margin-top:2rem;display:flex;gap:16px;justify-content:center;flex-wrap:wrap'>
                    <div style='background:#1E3A5F;border-radius:8px;padding:10px 20px;color:#93C5FD;font-size:0.85rem'>
                        ⚡ Concurrent fetching
                    </div>
                    <div style='background:#14532D;border-radius:8px;padding:10px 20px;color:#86EFAC;font-size:0.85rem'>
                        🔑 No API key needed
                    </div>
                    <div style='background:#3B1D8C;border-radius:8px;padding:10px 20px;color:#C4B5FD;font-size:0.85rem'>
                        📊 Analytics & export
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # No results
    if not jobs:
        st.error(
            "😕 No results found. Try a different keyword or leave the location blank."
        )
        return

    # Metrics
    st.markdown("---")
    _render_metrics(jobs)
    st.markdown("---")

    # Tabs
    tab_cards, tab_table, tab_analytics, tab_export = st.tabs(
        ["🃏 Job Cards", "📋 Table View", "📊 Analytics", "📁 Export"]
    )

    filtered = _apply_filters(jobs)

    with tab_cards:
        _render_job_cards(filtered)

    with tab_table:
        _render_table(filtered)

    with tab_analytics:
        _render_analytics(jobs)  # use all jobs for analytics (not filtered)

    with tab_export:
        _render_export(filtered)

    # Footer
    st.markdown(
        f"<div class='footer'>Job Vacancy Scraper · College Open Ended Lab Project 2026 · "
        f"Last search: {datetime.now().strftime('%H:%M:%S')}</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
