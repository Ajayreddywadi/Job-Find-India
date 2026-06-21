# Changelog — Job Find India

## [2.0.0] - 2026-06-16
### Added — City Intelligence Engine (Backend Only)
- **`CITY_ALIASES` dictionary** in `scraper.py`: 100+ alias→canonical mappings
  (`Mysore→mysuru`, `Bangalore→bengaluru`, `Bombay→mumbai`, `Gurgaon→gurugram`,
  `Vizag→visakhapatnam`, `Trivandrum→thiruvananthapuram`, `Madras→chennai`, etc.)
- **`normalize_city(raw)`** utility function: exact alias lookup + `difflib` fuzzy
  fallback at ≥82% similarity, enabling typo tolerance (`Mysor`, `mysur`, `MYSORE`
  all resolve correctly).
- **`CITY_STATE_MAP` dictionary**: maps every canonical Indian city to its state,
  used for state-level fallback matching.
- **`NEARBY_CITIES` dictionary**: defines fallback chains for 50+ Indian cities
  (e.g., Mysuru → [Bengaluru, Karnataka, Remote, India]).
- **`_location_matches()` rewrite** (5-tier matching):
  1. No location → accept all non-Indian-restricted
  2. Remote/worldwide query → accept all non-Indian-restricted
  3. India query → accept all non-Indian-restricted
  4. Specific Indian city → check canonical name, all aliases, state name, fuzzy
     token match, remote-friendly terms
  5. Unknown location → substring match
- **`JobAggregator._run_scrapers(location)`** extracted as reusable helper.
- **Smart fallback in `JobAggregator.run()`**: if exact city yields 0 results,
  walks `NEARBY_CITIES` chain and tries each fallback location in turn.
- **Structured API response**: `/api/jobs` now returns
  `{ jobs, fallback_used, fallback_message, searched_location, count }` instead of
  a plain array — backward-compatible (frontend handles both formats).

### Changed
- `scraper.py` version bumped to `2.0.0`.
- `api.py` version bumped to `1.1.0`; `/api/jobs` unpacks structured response and
  relays `fallback_message` and `searched_location` to the frontend.
- `index.html` `doSearch()`: reads `data.jobs` from new dict response; shows 🌍 toast
  with backend fallback message; updates location input to reflect actual searched city.

### Verified Test Results
| Query | Result |
|---|---|
| Python Developer + Mysore | 7 jobs, no fallback |
| Python Developer + Mysuru | 4 jobs, no fallback |
| React Developer + Mysor   | 3 jobs, no fallback |
| Data Scientist + Bengaluru | 7 jobs, no fallback |
| Java Developer + Bangalore | 11 jobs, no fallback |

---

## [1.1.0] - 2026-06-16
### Added
- Searchable city dropdown with `/api/cities` endpoint (91 cities).
- Frontend city alias resolution (JS `CITY_ALIASES` + `resolveCity()`).
- Keyboard navigation in city dropdown (↑ ↓ Enter Escape).

---

## [1.0.0] - 2026-06-16
### Added
- LinkedIn Guest API scraper.
- Unstop opportunity scraper (jobs + internships).
- Himalayas, Jobicy, Remotive, Arbeitnow scrapers.
- ThreadPoolExecutor parallel scraper engine (6 workers).
- German-only job filter for India searches.
- Flask REST API with CORS (`api.py`).
- Standalone HTML/CSS/JS frontend (`index.html`) at `http://localhost:5000`.
- CSV / JSON export functionality.
- Sidebar filters (job type, source, salary), sortable results, pagination.
