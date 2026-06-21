# Job Find India — Multi-Source Job Scraper & Aggregator

Job Find India is a professional, high-performance web aggregator for tech jobs and internships in India.
It aggregates results from LinkedIn, Unstop, Himalayas, Jobicy, Remotive, and Arbeitnow **concurrently**.

## Features

| Feature | Detail |
|---|---|
| 🔍 **Smart City Search** | Fuzzy city matching — "Mysore", "Mysor", "mysuru" all resolve to Mysuru |
| 🗺️ **City Alias Normalisation** | 100+ aliases: Bangalore→Bengaluru, Bombay→Mumbai, Gurgaon→Gurugram, Vizag→Visakhapatnam, etc. |
| 📍 **City Dropdown** | Searchable autocomplete dropdown with 91+ Indian cities; keyboard navigation supported |
| 🌍 **Smart Fallback** | No results in Mysuru? Auto-falls back to Bengaluru → Karnataka → Remote → India with toast message |
| 🔄 **Parallel Scraping** | ThreadPoolExecutor fetches 6 sources simultaneously |
| 🧹 **Deduplication** | Removes duplicate job URLs across all sources |
| 📊 **Sidebar Filters** | Filter by job type, source, salary; sortable results |
| 📥 **Data Export** | Export results to CSV or JSON formats |
| 🚫 **German Filter** | Non-Indian-restricted jobs (Germany/US/UK-only) are filtered out for India searches |

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the API backend:
   ```bash
   python api.py
   ```
3. Open your browser at:
   ```
   http://localhost:5000
   ```

## City Matching Rules

```
Input: "Mysore"  →  normalized: "mysuru"  →  matches jobs in Karnataka/Remote/Worldwide
Input: "Mysor"   →  fuzzy match (≥82%)   →  resolved to "mysuru"
Input: "Bangalore" → alias lookup        →  resolved to "bengaluru"
```

If the exact city yields no results, the backend automatically tries:
1. Nearby cities (e.g., Mysuru → Bengaluru)
2. State-level (e.g., Karnataka)
3. Remote
4. India-wide

The UI shows a 🌍 toast: *"No jobs found in Mysuru. Showing nearby Karnataka and Remote opportunities instead."*

## Sources

- **LinkedIn** — Guest job search API (Indian city support)
- **Unstop** — Jobs & internships (India-focused)
- **Himalayas** — 95k+ remote/hybrid tech jobs
- **Jobicy** — Curated remote tech jobs
- **Remotive** — Remote-first job board
- **Arbeitnow** — Remote-friendly roles (worldwide)
