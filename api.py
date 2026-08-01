"""
api.py — Job Vacancy Scraper REST API
======================================
A lightweight Flask server that exposes scraper results as JSON,
so the standalone HTML frontend can fetch live job data.

Endpoints
---------
GET /api/jobs?keyword=<str>&location=<str>
    Run the aggregator and return JSON list of job dicts.

GET /api/cities
    Return the canonical list of 100+ Indian cities for the city dropdown.

GET /api/health
    Health check — returns {"status": "ok"}.

Run with:
    python api.py

Serves on: http://localhost:5000
CORS is enabled so the HTML page can fetch from it directly.

Author : Job Vacancy Scraper Project
Version: 1.1.0
Updated: 2026-06-16
"""

from __future__ import annotations

import logging

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from scraper import JobAggregator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("api")

app = Flask(__name__)
CORS(app)  # allow requests from the HTML frontend (file:// or localhost)


@app.route("/")
def index():
    logger.info("Serving index.html frontend")
    return send_from_directory(".", "index.html")


# ── City list ─────────────────────────────────────────────────────────────────
# Canonical display names.  The frontend resolves aliases (Bangalore→Bengaluru,
# Bombay→Mumbai, Gurgaon→Gurugram) before sending the canonical name here.
_CITIES: list[str] = [
    # Special / top-level
    "India", "Remote",
    # Major tech hubs
    "Bengaluru", "Hyderabad", "Chennai", "Pune", "Mumbai", "Delhi", "Noida",
    "Gurugram", "Ahmedabad", "Kolkata",
    # Tier-2 tech cities
    "Mysuru", "Kochi", "Thiruvananthapuram", "Coimbatore", "Indore",
    "Chandigarh", "Jaipur", "Lucknow", "Nagpur", "Bhopal", "Surat",
    "Visakhapatnam", "Bhubaneswar", "Patna",
    # Other major cities
    "Agra", "Varanasi", "Meerut", "Ghaziabad", "Faridabad",
    "Nashik", "Aurangabad", "Solapur", "Kolhapur", "Vadodara",
    "Rajkot", "Surat", "Gandhinagar",
    "Jodhpur", "Udaipur", "Kota", "Ajmer", "Sikar",
    "Amritsar", "Ludhiana", "Jalandhar",
    "Dehradun", "Haridwar",
    "Ranchi", "Jamshedpur", "Dhanbad",
    "Guwahati", "Dibrugarh",
    "Mangaluru", "Hubballi", "Belagavi", "Davangere", "Ballari",
    "Madurai", "Tiruchirappalli", "Salem", "Tirunelveli", "Erode",
    "Vijayawada", "Guntur", "Tirupati", "Kakinada",
    "Warangal", "Nizamabad", "Karimnagar",
    "Kozhikode", "Thrissur", "Kollam", "Kannur",
    "Raipur", "Bhilai", "Bilaspur",
    "Gwalior", "Jabalpur", "Ujjain",
    "Agartala", "Imphal", "Shillong", "Aizawl",
    "Srinagar", "Jammu", "Leh",
    "Panaji", "Margao",
    "Puducherry",
    "Port Blair",
]
# Deduplicate while preserving order
_seen: set[str] = set()
_CITIES_UNIQUE: list[str] = []
for _c in _CITIES:
    if _c not in _seen:
        _seen.add(_c)
        _CITIES_UNIQUE.append(_c)
_CITIES = _CITIES_UNIQUE


@app.route("/api/cities")
def cities():
    """Return the canonical city list for the frontend dropdown."""
    return jsonify(_CITIES)


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/skills")
def skills():
    return jsonify(["Python", "Java", "React", "Node", "SQL", "JavaScript", "HTML", "CSS", "Data Science"])


@app.route("/api/jobs")
def jobs():
    keyword  = request.args.get("keyword",  "").strip()
    location = request.args.get("location", "").strip()

    if not keyword:
        return jsonify({"error": "keyword parameter is required"}), 400

    logger.info("Search request — keyword=%r, location=%r", keyword, location)
    aggregator = JobAggregator(keyword=keyword, location=location)
    result = aggregator.run()

    jobs_list        = result.get("jobs", [])
    fallback_used    = result.get("fallback_used", False)
    fallback_message = result.get("fallback_message", "")
    searched_loc     = result.get("searched_location", location)

    logger.info(
        "Returning %d jobs (fallback=%s, searched_location=%r)",
        len(jobs_list), fallback_used, searched_loc,
    )
    return jsonify({
        "jobs":             jobs_list,
        "fallback_used":    fallback_used,
        "fallback_message": fallback_message,
        "searched_location": searched_loc,
        "count":            len(jobs_list),
    })


if __name__ == "__main__":
    print("\n[OK] Job Vacancy API running at http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
