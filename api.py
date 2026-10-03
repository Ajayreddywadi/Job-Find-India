"""
api.py — Job Vacancy Scraper REST API, Auth & Resume Recommendation Server
========================================================================
A Flask REST API exposing job scraper results as JSON, user authentication,
and AI-assisted resume parsing & job recommendations.

Endpoints
---------
POST /api/auth/register  → Register new user account
POST /api/auth/login     → Authenticate user and create session
POST /api/auth/logout    → Destroy current user session
GET  /api/auth/me        → Get profile of currently logged-in user
PUT  /api/auth/profile   → Update user preferred location / settings

POST /api/resume/parse     → Upload and parse PDF/DOCX resume
POST /api/resume/recommend → Recommend jobs based on extracted skills & role

GET /api/jobs?keyword=<str>&location=<str> → Scrape and return job dicts
GET /api/cities → Return canonical list of Indian cities
GET /api/health → Health check {"status": "ok"}
GET /api/skills → Return sample skills list

Serves on: http://localhost:5000
"""

from __future__ import annotations

import logging

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS

from config.settings import SECRET_KEY
from database import init_db
from scraper import JobAggregator
from services.auth_service import (
    register_user,
    authenticate_user,
    get_user_by_id,
    update_user_location,
)
from services.resume_service import (
    parse_resume,
    recommend_jobs_from_resume,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("api")

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# CORS configuration supporting credentials (cookies/session) for frontend
CORS(app, supports_credentials=True)

# Initialize database schema automatically on module import/startup
init_db()


@app.route("/")
def index():
    logger.info("Serving index.html frontend")
    return send_from_directory(".", "index.html")


# ── Authentication Endpoints ─────────────────────────────────────────────────

@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    """Register a new user account."""
    data = request.get_json(silent=True) or {}
    full_name = data.get("full_name", "")
    email = data.get("email", "")
    password = data.get("password", "")
    preferred_location = data.get("preferred_location", "")

    user, error = register_user(
        full_name=full_name,
        email=email,
        password=password,
        preferred_location=preferred_location,
    )
    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Registration successful. Please log in.",
        "user": user,
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Authenticate user credentials and create a session."""
    data = request.get_json(silent=True) or {}
    email = data.get("email", "")
    password = data.get("password", "")

    user, error = authenticate_user(email=email, password=password)
    if error:
        return jsonify({"error": error}), 401

    # Create authenticated session
    session["user_id"] = user["id"]
    session.permanent = True
    logger.info("Session created for user_id=%d (%s)", user["id"], user["email"])

    return jsonify({
        "message": "Login successful",
        "user": user,
    }), 200


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """Destroy user session."""
    user_id = session.pop("user_id", None)
    session.clear()
    logger.info("Session cleared for user_id=%s", user_id)
    return jsonify({"message": "Logged out successfully"}), 200


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    """Get the currently authenticated user's profile."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"user": None, "authenticated": False}), 200

    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return jsonify({"user": None, "authenticated": False}), 200

    return jsonify({"user": user, "authenticated": True}), 200


@app.route("/api/auth/profile", methods=["PUT"])
def auth_update_profile():
    """Update authenticated user profile preferences."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json(silent=True) or {}
    pref_loc = data.get("preferred_location", "")

    user, error = update_user_location(user_id, pref_loc)
    if error:
        return jsonify({"error": error}), 400

    return jsonify({"message": "Profile updated successfully", "user": user}), 200


# ── Resume Parsing & Recommendation Endpoints ────────────────────────────────

@app.route("/api/resume/parse", methods=["POST"])
def resume_parse():
    """Parse uploaded PDF or DOCX resume and extract candidate profile."""
    if "file" not in request.files and "resume" not in request.files:
        return jsonify({"error": "No resume file uploaded. Please upload a PDF or DOCX file."}), 400

    file = request.files.get("resume") or request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "No file selected."}), 400

    filename = file.filename
    if not (
        filename.lower().endswith(".pdf")
        or filename.lower().endswith(".docx")
        or filename.lower().endswith(".doc")
        or filename.lower().endswith(".txt")
    ):
        return jsonify({"error": "Unsupported file format. Please upload a PDF or DOCX resume."}), 400

    try:
        file_bytes = file.read()
        parsed_data = parse_resume(filename, file_bytes)

        # Check if user has saved preferred location in DB
        user_id = session.get("user_id")
        if user_id:
            user = get_user_by_id(user_id)
            if user and user.get("preferred_location"):
                parsed_data["saved_location"] = user["preferred_location"]
                parsed_data["target_location"] = user["preferred_location"]
            else:
                parsed_data["target_location"] = parsed_data["detected_location"]
        else:
            parsed_data["target_location"] = parsed_data["detected_location"]

        logger.info(
            "Successfully parsed resume %r: role=%r, skills_count=%d",
            filename, parsed_data["role"], len(parsed_data["skills"]),
        )
        # Normalize keys to match frontend expectations
        response_data = {
            "success": True,
            "job_role": parsed_data.get("role", "Software Engineer"),
            "extracted_skills": parsed_data.get("skills", []),
            "education": parsed_data.get("education", []),
            "experience": parsed_data.get("experience", ""),
            "preferred_location": parsed_data.get("target_location", parsed_data.get("detected_location", "India")),
            "detected_location": parsed_data.get("detected_location", "India"),
            "text_preview": parsed_data.get("text_preview", ""),
        }
        return jsonify(response_data), 200
    except Exception as exc:
        logger.error("Failed to parse resume %r: %s", filename, exc)
        return jsonify({"error": "Failed to extract text from resume file."}), 500


@app.route("/api/resume/recommend", methods=["POST"])
def resume_recommend():
    """Recommend jobs based on extracted/edited resume skills, role, and location."""
    data = request.get_json(silent=True) or {}
    skills_list = data.get("skills", [])
    # Accept both 'role' and 'job_role' for compatibility with frontend
    role = (data.get("job_role") or data.get("role") or "").strip()
    location = data.get("location", "").strip()

    if not isinstance(skills_list, list):
        skills_list = []

    # If user is authenticated and location is provided, save preferred_location
    user_id = session.get("user_id")
    if user_id and location:
        update_user_location(user_id, location)

    recommendation = recommend_jobs_from_resume(skills=skills_list, role=role, location=location)

    # Normalize match_score to integer for frontend comparison (e.g. '85%' -> 85)
    for job in recommendation.get("jobs", []):
        ms = job.get("match_score")
        if isinstance(ms, str):
            try:
                job["match_score"] = int(ms.replace("%", ""))
            except ValueError:
                job["match_score"] = 0

    return jsonify(recommendation), 200


# ── City list ─────────────────────────────────────────────────────────────────
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
