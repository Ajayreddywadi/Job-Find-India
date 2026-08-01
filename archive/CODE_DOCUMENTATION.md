# Code Documentation — Job Find India

## Architecture Overview

```
http://localhost:5000
       │
       ▼
   api.py  (Flask REST API)
       │
       ├── GET /            → serves index.html
       ├── GET /api/health  → {"status":"ok"}
       ├── GET /api/cities  → ["India","Remote","Bengaluru",…] (91 cities)
       └── GET /api/jobs?keyword=…&location=…
               │
               ▼
          JobAggregator (scraper.py)
               │  ThreadPoolExecutor (6 workers)
               ├── LinkedInScraper
               ├── UnstopScraper
               ├── HimalayasScraper
               ├── JobicyScraper
               ├── RemotiveScraper
               └── ArbeitnowScraper
```

## Files

| File | Role |
|---|---|
| `api.py` | Flask server, REST endpoints, city list |
| `scraper.py` | All scraper classes, city normalisation, aggregator |
| `index.html` | Complete single-file frontend (HTML + CSS + JS) |
| `requirements.txt` | Python dependencies |

## scraper.py — Key Components

### Constants
| Name | Value | Purpose |
|---|---|---|
| `DEFAULT_TIMEOUT` | 20s | Per-HTTP-request timeout |
| `MAX_WORKERS` | 6 | ThreadPoolExecutor workers |
| `MAX_RESULTS_PER_SOURCE` | 50 | Cap per scraper |
| `FUZZY_THRESHOLD` | 0.82 | Min similarity for fuzzy city match |

### City Normalisation Data

#### `CITY_ALIASES: dict[str, str]`
Maps 100+ raw city strings (lowercase) to their canonical lowercase names.

```python
CITY_ALIASES = {
    "mysore":    "mysuru",
    "bangalore": "bengaluru",
    "bombay":    "mumbai",
    "gurgaon":   "gurugram",
    "calcutta":  "kolkata",
    "vizag":     "visakhapatnam",
    # ... 94 more entries
}
```

#### `CITY_STATE_MAP: dict[str, str]`
Maps canonical city name → state name (lowercase).

```python
CITY_STATE_MAP = {
    "mysuru":   "karnataka",
    "bengaluru":"karnataka",
    "mumbai":   "maharashtra",
    "hyderabad":"telangana",
    # ...
}
```

#### `NEARBY_CITIES: dict[str, list[str]]`
Defines fallback chains. Used by `JobAggregator.run()` when the primary city has no results.

```python
NEARBY_CITIES = {
    "mysuru": ["bengaluru", "karnataka", "remote", "india"],
    "noida":  ["delhi", "gurugram", "uttar pradesh", "remote", "india"],
    # ...
}
```

### Key Functions

#### `normalize_city(raw: str) -> str`
```
1. Lowercase the input.
2. Exact lookup in CITY_ALIASES → return canonical.
3. difflib.get_close_matches(cutoff=0.82) against alias keys → return canonical.
4. Return raw (lowercase) if no match.
```

#### `BaseScraper._location_matches(job_location: str) -> bool`
5-tier filter:
1. **No filter** (`self.location_canonical == ""`) → accept unless non-Indian-restricted
2. **Remote query** → accept unless non-Indian-restricted
3. **India query** → accept unless non-Indian-restricted
4. **Specific Indian city** (most common path):
   - a. Canonical name substring in job location
   - b. Any alias of the city in job location
   - c. City's state name in job location
   - d. Fuzzy token match (SequenceMatcher ≥ 82%)
   - e. Job is remote-friendly (Worldwide, Global, Remote, APAC…)
5. **Other** → direct substring or non-restricted

#### `JobAggregator.run() -> dict`
Returns structured response:
```python
{
    "jobs":             list[dict],   # sorted by date descending
    "fallback_used":    bool,
    "fallback_message": str,          # "" if no fallback
    "searched_location": str,
}
```
Fallback chain: exact city → `NEARBY_CITIES` entries → auto-state → remote → india.

## api.py — Endpoints

### `GET /api/jobs`
**Params**: `keyword` (required), `location` (optional, default "")

**Response**:
```json
{
  "jobs": [...],
  "fallback_used": false,
  "fallback_message": "",
  "searched_location": "Mysore",
  "count": 7
}
```

### `GET /api/cities`
Returns ordered list of 91 canonical city names (India and Remote first).

## index.html — City Autocomplete (JS)

### `CITY_ALIASES` (JS object)
Client-side alias map (mirrors Python dict) for instant input normalisation before the API call.

### `resolveCity(raw: str) -> str`
Looks up `CITY_ALIASES` then scans for prefix/partial matches. Applied to user input before `fetch()`.

### `loadCities()`
Fetches `GET /api/cities` on page load. Falls back to a 26-city inline list if the server isn't running.

### `doSearch()`
1. Reads keyword + location inputs.
2. Calls `resolveCity()` on the location.
3. Fetches `GET /api/jobs`.
4. Reads `data.jobs` (dict response).
5. If `data.fallback_used`, shows 🌍 toast with `data.fallback_message` and updates location inputs.
