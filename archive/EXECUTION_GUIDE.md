# Execution Guide — Job Find India

## Requirements

- Python 3.10+
- Internet connection (scrapers fetch live data)

## Step 1 — Install Dependencies

```bash
pip install -r requirements.txt
```

> `difflib` is part of the Python standard library — no extra install needed for fuzzy city matching.

## Step 2 — Start the API Backend

```bash
python api.py
```

The server starts at **http://localhost:5000** and prints:

```
[OK] Job Vacancy API running at http://localhost:5000
```

## Step 3 — Open the Frontend

Navigate to **http://localhost:5000** in your browser.

The page serves the complete `index.html` frontend directly from Flask.

## Step 4 — Search for Jobs

1. Type a skill or job title in the **left field** (e.g., `Python Developer`)
2. Click the **location field** — a dropdown appears with 91 Indian cities
3. Type to filter (e.g., `mys` → shows Mysuru, Mysore) or scroll and click
4. Click **Find Jobs**

### City Input Behaviour

| You type | Resolved to | Notes |
|---|---|---|
| `Mysore` | `Mysuru` | Exact alias |
| `Mysor` | `Mysuru` | Fuzzy match ≥82% |
| `Bangalore` | `Bengaluru` | Exact alias |
| `Gurgaon` | `Gurugram` | Exact alias |
| `Bombay` | `Mumbai` | Exact alias |
| `Vizag` | `Visakhapatnam` | Exact alias |

### Fallback Toast

If no direct results are found for a city, the backend automatically tries nearby cities.
A 🌍 notification appears:

> *"No jobs found in Mysuru. Showing nearby Karnataka and Remote opportunities instead."*

## Troubleshooting

| Issue | Fix |
|---|---|
| `Could not connect — is api.py running?` | Run `python api.py` first |
| No results for a city | Backend auto-falls back — wait for toast |
| LinkedIn returns 0 | LinkedIn rate-limits aggressively; other sources still return results |
| Slow search | Normal — 6 sources fetch in parallel; ~5–15s typical |

## API Endpoints (for developers)

```bash
# Health check
curl http://localhost:5000/api/health

# City list
curl http://localhost:5000/api/cities

# Job search
curl "http://localhost:5000/api/jobs?keyword=Python+Developer&location=Mysore"
```

Response includes `fallback_used`, `fallback_message`, `searched_location`, and `count`.
