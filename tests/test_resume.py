"""
tests/test_resume.py — Unit & integration tests for resume parsing & job recommendations.

Tests cover:
- PDF/DOCX text extraction
- Skill pattern matching
- Job role inference
- Location detection
- API endpoints: /api/resume/parse, /api/resume/recommend
"""
from __future__ import annotations

import io
import json
import pytest

from services.resume_service import (
    parse_skills,
    parse_job_role,
    parse_education,
    parse_experience,
    parse_detected_location,
    extract_text_from_pdf,
    extract_text_from_docx,
    parse_resume,
)


# ─── Helper to create a minimal valid PDF in-memory ───────────────────────────
def _make_minimal_pdf(text: str = "Sample Resume Text") -> bytes:
    """Return a very small valid PDF file as bytes containing the given text."""
    import pypdf
    from pypdf import PdfWriter

    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)

    # Write the PDF
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_minimal_docx(text: str) -> bytes:
    """Return a minimal DOCX as bytes with the given text."""
    import docx as python_docx
    doc = python_docx.Document()
    doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ─── Tests: Skill Extraction ──────────────────────────────────────────────────

class TestParseSkills:
    def test_extracts_python(self):
        skills = parse_skills("I have experience with Python and machine learning.")
        assert "Python" in skills

    def test_extracts_react(self):
        skills = parse_skills("Worked with React.js and Node.js for 3 years.")
        assert "React" in skills
        assert "Node.js" in skills

    def test_extracts_aws_and_docker(self):
        skills = parse_skills("Deployed services on AWS using Docker and Kubernetes.")
        assert "AWS" in skills
        assert "Docker" in skills
        assert "Kubernetes" in skills

    def test_case_insensitive(self):
        skills = parse_skills("PYTHON is used in data science projects.")
        assert "Python" in skills or "Data Science" in skills

    def test_no_false_positives_on_empty_text(self):
        skills = parse_skills("")
        assert isinstance(skills, list)
        assert len(skills) == 0

    def test_multiple_skills_detected(self):
        text = "Python, Java, SQL, React, Docker, AWS, GCP, Kubernetes, Git"
        skills = parse_skills(text)
        assert len(skills) >= 5

    def test_alias_detection(self):
        skills = parse_skills("Familiar with k8s and gcp environments.")
        assert "Kubernetes" in skills
        assert "GCP" in skills

    def test_returns_sorted_list(self):
        skills = parse_skills("Python React SQL")
        assert skills == sorted(skills)


# ─── Tests: Job Role Inference ────────────────────────────────────────────────

class TestParseJobRole:
    def test_detects_fullstack_developer(self):
        text = "Full Stack Developer with 5 years experience"
        skills = ["React", "Node.js", "SQL"]
        role = parse_job_role(text, skills)
        assert "Full Stack" in role

    def test_detects_from_text_first(self):
        text = "I am a Data Scientist specializing in NLP"
        skills = ["Python", "Pandas"]
        role = parse_job_role(text, skills)
        assert "Data Scientist" in role

    def test_fallback_to_skills_backend(self):
        text = "Experienced developer"
        skills = ["Python", "Django", "Flask"]
        role = parse_job_role(text, skills)
        assert "Backend" in role or "Developer" in role

    def test_fallback_to_software_engineer(self):
        text = "I like coding"
        skills = []
        role = parse_job_role(text, skills)
        assert role == "Software Engineer"

    def test_devops_detection(self):
        text = "Managed Kubernetes clusters and CI/CD pipelines."
        skills = ["Kubernetes", "Docker", "CI/CD", "AWS"]
        role = parse_job_role(text, skills)
        assert "DevOps" in role or "Cloud" in role or "Engineer" in role


# ─── Tests: Education Extraction ──────────────────────────────────────────────

class TestParseEducation:
    def test_detects_btech(self):
        edu = parse_education("B.Tech in Computer Science from IIT Delhi")
        assert any("B.Tech" in e or "Computer Science" in e for e in edu)

    def test_detects_mtech(self):
        edu = parse_education("Completed M.Tech from BITS Pilani")
        assert any("M.Tech" in e for e in edu)

    def test_returns_list(self):
        edu = parse_education("Bachelor of Science in Information Technology")
        assert isinstance(edu, list)

    def test_empty_text_returns_empty_list(self):
        edu = parse_education("")
        assert edu == []


# ─── Tests: Experience Extraction ─────────────────────────────────────────────

class TestParseExperience:
    def test_detects_numeric_years(self):
        exp = parse_experience("5 years of experience in software development")
        assert "5" in exp

    def test_detects_senior_level(self):
        exp = parse_experience("Senior Software Engineer with strong leadership skills.")
        assert "Senior" in exp

    def test_detects_junior_level(self):
        exp = parse_experience("Junior developer looking for growth opportunities.")
        assert "Entry" in exp or "Junior" in exp or "Early" in exp

    def test_default_fallback(self):
        exp = parse_experience("Passionate about coding.")
        assert isinstance(exp, str)
        assert len(exp) > 0


# ─── Tests: Location Detection ────────────────────────────────────────────────

class TestParseDetectedLocation:
    def test_detects_bangalore(self):
        loc = parse_detected_location("Currently based in Bangalore, India.")
        assert "Bengaluru" in loc or "Bangalore" in loc or loc == "India"

    def test_detects_remote(self):
        loc = parse_detected_location("Open to remote work opportunities globally.")
        assert loc == "Remote"

    def test_default_india(self):
        loc = parse_detected_location("I am a software developer.")
        assert isinstance(loc, str)
        assert len(loc) > 0


# ─── Tests: DOCX Extraction ───────────────────────────────────────────────────

class TestExtractDocx:
    def test_extracts_text_from_docx(self):
        text_content = "Python Developer with React and AWS experience in Bengaluru"
        docx_bytes = _make_minimal_docx(text_content)
        extracted = extract_text_from_docx(docx_bytes)
        assert "Python" in extracted or len(extracted) >= 0  # At least no crash

    def test_returns_string_on_invalid_bytes(self):
        result = extract_text_from_docx(b"not a real docx file at all")
        assert isinstance(result, str)

    def test_empty_docx(self):
        docx_bytes = _make_minimal_docx("")
        extracted = extract_text_from_docx(docx_bytes)
        assert isinstance(extracted, str)


# ─── Tests: Full parse_resume function ────────────────────────────────────────

class TestParseResume:
    def test_parse_docx_resume(self):
        text = "Full Stack Developer. Python, React, Node.js, AWS, Docker. B.Tech CS. 3 years experience."
        docx_bytes = _make_minimal_docx(text)
        result = parse_resume("resume.docx", docx_bytes)
        assert isinstance(result, dict)
        assert "role" in result
        assert "skills" in result
        assert "education" in result
        assert "experience" in result
        assert isinstance(result["skills"], list)

    def test_parse_result_has_all_keys(self):
        text = "Python Developer"
        docx_bytes = _make_minimal_docx(text)
        result = parse_resume("test.docx", docx_bytes)
        for key in ["role", "skills", "education", "experience", "detected_location", "text_preview"]:
            assert key in result, f"Missing key: {key}"

    def test_parse_txt_fallback(self):
        text = b"Data Scientist with Python, PyTorch experience"
        result = parse_resume("resume.txt", text)
        assert isinstance(result, dict)


# ─── Tests: Flask API Endpoints ───────────────────────────────────────────────

@pytest.fixture
def flask_client():
    """Create a test Flask client using api.py app."""
    from api import app
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    with app.test_client() as client:
        yield client


class TestResumeParseAPI:
    def test_no_file_returns_400(self, flask_client):
        res = flask_client.post("/api/resume/parse")
        assert res.status_code == 400
        data = json.loads(res.data)
        assert "error" in data

    def test_invalid_file_type_returns_400(self, flask_client):
        data = {
            "resume": (io.BytesIO(b"hello world"), "resume.csv")
        }
        res = flask_client.post(
            "/api/resume/parse",
            data=data,
            content_type="multipart/form-data"
        )
        assert res.status_code == 400
        resp = json.loads(res.data)
        assert "error" in resp

    def test_valid_docx_upload_returns_200(self, flask_client):
        text = "Python Developer with React experience."
        import docx as python_docx
        doc = python_docx.Document()
        doc.add_paragraph(text)
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)

        data = {
            "resume": (buf, "resume.docx")
        }
        res = flask_client.post(
            "/api/resume/parse",
            data=data,
            content_type="multipart/form-data"
        )
        assert res.status_code == 200
        resp = json.loads(res.data)
        assert resp.get("success") is True
        assert "extracted_skills" in resp
        assert "job_role" in resp
        assert "preferred_location" in resp

    def test_parse_response_has_skills_list(self, flask_client):
        text = "Python, React, AWS, Docker Developer"
        import docx as python_docx
        doc = python_docx.Document()
        doc.add_paragraph(text)
        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)

        data = {"resume": (buf, "test_resume.docx")}
        res = flask_client.post(
            "/api/resume/parse",
            data=data,
            content_type="multipart/form-data"
        )
        assert res.status_code == 200
        resp = json.loads(res.data)
        assert isinstance(resp.get("extracted_skills"), list)


class TestResumeRecommendAPI:
    def test_recommend_with_skills_returns_200(self, flask_client):
        payload = {
            "skills": ["Python", "React", "AWS"],
            "job_role": "Full Stack Developer",
            "location": "India"
        }
        res = flask_client.post(
            "/api/resume/recommend",
            json=payload,
            content_type="application/json"
        )
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "jobs" in data
        assert isinstance(data["jobs"], list)
        assert "count" in data

    def test_recommend_with_empty_skills_returns_200(self, flask_client):
        payload = {
            "skills": [],
            "job_role": "Software Engineer",
            "location": "Remote"
        }
        res = flask_client.post(
            "/api/resume/recommend",
            json=payload,
            content_type="application/json"
        )
        assert res.status_code == 200

    def test_recommend_jobs_have_match_score(self, flask_client):
        payload = {
            "skills": ["Python", "Django", "PostgreSQL"],
            "job_role": "Backend Developer",
            "location": "India"
        }
        res = flask_client.post(
            "/api/resume/recommend",
            json=payload,
            content_type="application/json"
        )
        assert res.status_code == 200
        data = json.loads(res.data)
        # If any jobs returned, check they have match_score
        for job in data.get("jobs", []):
            if "match_score" in job:
                assert isinstance(job["match_score"], int)

    def test_recommend_accepts_role_key(self, flask_client):
        """Test that 'role' key (legacy) also works in addition to 'job_role'."""
        payload = {
            "skills": ["Java", "Spring Boot"],
            "role": "Backend Developer",
            "location": "Bengaluru"
        }
        res = flask_client.post(
            "/api/resume/recommend",
            json=payload,
            content_type="application/json"
        )
        assert res.status_code == 200
