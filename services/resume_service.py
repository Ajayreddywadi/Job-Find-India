"""
services/resume_service.py — Resume Parser & Job Recommendation Engine
========================================================================
Extracts text from PDF and DOCX files, detects technical skills, job titles,
education, and experience, and matches candidate profiles against aggregated jobs.
"""

from __future__ import annotations

import io
import re
import logging
from typing import Any

import pypdf
import docx

from config.cities import CITY_ALIASES, normalize_city
from services.search_service import JobAggregator

logger = logging.getLogger("resume_service")

# Comprehensive dictionary of technical skills and canonical display names
SKILL_PATTERNS: dict[str, str] = {
    r"\bpython\b": "Python",
    r"\bjava\b": "Java",
    r"\bjavascript\b|\bjs\b": "JavaScript",
    r"\btypescript\b|\bts\b": "TypeScript",
    r"\breact(?:\.js|js)?\b": "React",
    r"\bnext(?:\.js|js)?\b": "Next.js",
    r"\bnode(?:\.js|js)?\b": "Node.js",
    r"\bexpress(?:\.js|js)?\b": "Express.js",
    r"\bvue(?:\.js|js)?\b": "Vue.js",
    r"\bangular(?:\.js|js)?\b": "Angular",
    r"\bhtml(?:5)?\b": "HTML",
    r"\bcss(?:3)?\b": "CSS",
    r"\btailwind(?:css)?\b": "Tailwind CSS",
    r"\bbootstrap\b": "Bootstrap",
    r"\bsql\b": "SQL",
    r"\bpostgresql\b|\bpostgres\b": "PostgreSQL",
    r"\bmysql\b": "MySQL",
    r"\bmongodb\b|\bmongo\b": "MongoDB",
    r"\bredis\b": "Redis",
    r"\baws\b|\bamazon web services\b": "AWS",
    r"\bazure\b": "Azure",
    r"\bgcp\b|\bgoogle cloud\b": "GCP",
    r"\bdocker\b": "Docker",
    r"\bkubernetes\b|\bk8s\b": "Kubernetes",
    r"\bc\+\+\b": "C++",
    r"\bc#\b|\b\.net\b": "C# / .NET",
    r"\bgolang\b|\bgo\b": "Go",
    r"\brust\b": "Rust",
    r"\bmachine learning\b|\bml\b": "Machine Learning",
    r"\bdata science\b": "Data Science",
    r"\bartificial intelligence\b|\bai\b": "Artificial Intelligence",
    r"\bdeep learning\b": "Deep Learning",
    r"\bpytorch\b": "PyTorch",
    r"\btensorflow\b": "TensorFlow",
    r"\bpandas\b": "Pandas",
    r"\bnumpy\b": "NumPy",
    r"\bscikit-learn\b|\bsklearn\b": "Scikit-Learn",
    r"\bflask\b": "Flask",
    r"\bdjango\b": "Django",
    r"\bfastapi\b": "FastAPI",
    r"\bspring(?:boot)?\b": "Spring Boot",
    r"\bmicroservices\b": "Microservices",
    r"\brest(?:\s*api)?\b": "REST API",
    r"\bgraphql\b": "GraphQL",
    r"\bgit\b|\bgithub\b": "Git",
    r"\blinux\b": "Linux",
    r"\bbash\b|\bshell\b": "Bash",
    r"\bci/cd\b|\bjenkins\b": "CI/CD",
    r"\bterraform\b": "Terraform",
    r"\bredux\b": "Redux",
    r"\bflutter\b": "Flutter",
    r"\bswift\b": "Swift",
    r"\bkotlin\b": "Kotlin",
    r"\bandroid\b": "Android",
    r"\bios\b": "iOS",
    r"\bmobile\b": "Mobile Development",
    r"\bqa\b|\bselenium\b|\bcypress\b|\btesting\b": "QA / Testing",
    r"\bdevops\b": "DevOps",
    r"\bjira\b|\bagile\b|\bscrum\b": "Agile / Scrum",
    r"\bfigma\b|\bui/ux\b": "UI/UX Design",
    r"\btableau\b|\bpower bi\b": "Data Analytics",
    r"\bspark\b|\bhadoop\b|\bkafka\b": "Big Data",
}

# Recognized Job Roles
JOB_ROLES: list[str] = [
    "Full Stack Developer", "Full Stack Engineer",
    "Frontend Developer", "Frontend Engineer",
    "Backend Developer", "Backend Engineer",
    "Software Engineer", "Software Developer",
    "Data Scientist", "Data Analyst",
    "Machine Learning Engineer", "AI Engineer",
    "DevOps Engineer", "Cloud Engineer",
    "Mobile Developer", "Android Developer", "iOS Developer",
    "Product Manager", "QA Engineer", "Quality Assurance Engineer",
    "UI/UX Designer", "Systems Administrator", "Solution Architect",
    "Security Engineer", "Database Administrator",
]


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF file bytes."""
    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        text_parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
        return "\n".join(text_parts)
    except Exception as exc:
        logger.error("Error reading PDF resume: %s", exc)
        return ""


def extract_text_from_docx(docx_bytes: bytes) -> str:
    """Extract text from DOCX file bytes."""
    try:
        doc = docx.Document(io.BytesIO(docx_bytes))
        text_parts = []
        for p in doc.paragraphs:
            if p.text:
                text_parts.append(p.text)
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                if row_text:
                    text_parts.append(row_text)
        return "\n".join(text_parts)
    except Exception as exc:
        logger.error("Error reading DOCX resume: %s", exc)
        return ""


def extract_text_from_file(filename: str, file_bytes: bytes) -> str:
    """Extract text from PDF or DOCX file based on filename extension."""
    fn_lower = filename.lower()
    if fn_lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif fn_lower.endswith(".docx") or fn_lower.endswith(".doc"):
        return extract_text_from_docx(file_bytes)
    else:
        # Fallback to UTF-8 plain text decode if text file
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""


def parse_skills(text: str) -> list[str]:
    """Detect matching technical skills in the text."""
    found: set[str] = set()
    text_lower = text.lower()

    for pattern, canonical in SKILL_PATTERNS.items():
        if re.search(pattern, text_lower):
            found.add(canonical)

    return sorted(list(found))


def parse_job_role(text: str, skills: list[str]) -> str:
    """Detect primary job role/title from text or infer from extracted skills."""
    text_lower = text.lower()

    # Direct match check against known roles
    for role in JOB_ROLES:
        if role.lower() in text_lower:
            return role

    # Rule-based fallback based on extracted skills
    skills_lower = {s.lower() for s in skills}

    if {"react", "angular", "vue.js", "html", "css", "tailwind css"}.intersection(skills_lower) and {
        "node.js", "python", "java", "sql", "express.js"
    }.intersection(skills_lower):
        return "Full Stack Developer"
    if {"react", "frontend", "html", "css", "vue.js", "angular"}.intersection(skills_lower):
        return "Frontend Developer"
    if {"python", "java", "node.js", "express.js", "spring boot", "django", "flask"}.intersection(skills_lower):
        return "Backend Developer"
    if {"data science", "machine learning", "pytorch", "tensorflow", "pandas"}.intersection(skills_lower):
        return "Data Scientist"
    if {"aws", "docker", "kubernetes", "devops", "ci/cd", "terraform"}.intersection(skills_lower):
        return "DevOps Engineer"
    if {"android", "ios", "flutter", "swift", "kotlin"}.intersection(skills_lower):
        return "Mobile Developer"
    if {"ui/ux design"}.intersection(skills_lower):
        return "UI/UX Designer"

    return "Software Engineer"


def parse_education(text: str) -> list[str]:
    """Extract education background degrees."""
    found: set[str] = set()
    patterns = [
        (r"\bb\.?\s*tech\b|\bbachelor of technology\b", "B.Tech"),
        (r"\bb\.?\s*e\.?\b|\bbachelor of engineering\b", "B.E."),
        (r"\bm\.?\s*tech\b|\bmaster of technology\b", "M.Tech"),
        (r"\bm\.?\s*s\.?\b|\bmaster of science\b", "M.S."),
        (r"\bb\.?\s*c\.?\s*a\.?\b|\bbachelor of computer applications\b", "BCA"),
        (r"\bm\.?\s*c\.?\s*a\.?\b|\bmaster of computer applications\b", "MCA"),
        (r"\bb\.?\s*s\.?\b|\bbachelor of science\b", "B.S."),
        (r"\bph\.?d\.?\b|\bdoctor of philosophy\b", "Ph.D."),
        (r"\bcomputer science\b", "Computer Science"),
        (r"\binformation technology\b", "Information Technology"),
    ]

    text_lower = text.lower()
    for pattern, canonical in patterns:
        if re.search(pattern, text_lower):
            found.add(canonical)

    return sorted(list(found))


def parse_experience(text: str) -> str:
    """Extract experience summary or years of experience."""
    match = re.search(
        r"\b(\d+|\b(?:one|two|three|four|five|six|seven|eight|nine|ten))\+?\s*(?:-\s*\d+\s*)?(?:years?|yrs?)\b",
        text,
        re.IGNORECASE,
    )
    if match:
        return f"{match.group(0).strip()} of relevant experience"

    if re.search(r"\bsenior\b", text, re.IGNORECASE):
        return "Senior Level Professional"
    if re.search(r"\bjunior\b|\bintern\b|\bentry level\b", text, re.IGNORECASE):
        return "Entry / Early Career Professional"

    return "Experienced Professional"


def parse_detected_location(text: str) -> str:
    """Detect location from resume text matching Indian cities."""
    text_lower = text.lower()

    # Search for known Indian cities/aliases
    for alias, canonical in CITY_ALIASES.items():
        if len(alias) >= 4 and re.search(r"\b" + re.escape(alias) + r"\b", text_lower):
            return canonical.title()

    if "remote" in text_lower:
        return "Remote"

    return "India"


def parse_resume(filename: str, file_bytes: bytes) -> dict[str, Any]:
    """Parse resume file and extract structured candidate profile."""
    text = extract_text_from_file(filename, file_bytes)

    skills = parse_skills(text)
    role = parse_job_role(text, skills)
    education = parse_education(text)
    experience = parse_experience(text)
    detected_location = parse_detected_location(text)

    return {
        "role": role,
        "skills": skills,
        "education": education,
        "experience": experience,
        "detected_location": detected_location,
        "text_preview": text[:300].strip() if text else "",
    }


def recommend_jobs_from_resume(
    skills: list[str],
    role: str,
    location: str = "India",
) -> dict[str, Any]:
    """Search for jobs matching extracted skills and role, calculating match score."""
    target_loc = location.strip() if location and location.strip() else "India"

    # Construct search keyword: primary role or top skills + role
    if role:
        kw = role
    elif skills:
        kw = f"{skills[0]} Developer"
    else:
        kw = "Software Engineer"

    logger.info("Recommending jobs — keyword=%r, location=%r, skills_count=%d", kw, target_loc, len(skills))

    aggregator = JobAggregator(keyword=kw, location=target_loc)
    result = aggregator.run()

    jobs_list = result.get("jobs", [])
    skills_lower = [s.lower() for s in skills]

    scored_jobs: list[dict[str, Any]] = []

    for idx, job in enumerate(jobs_list):
        j_text = f"{job.get('title', '')} {job.get('tags', '')} {job.get('description', '')}".lower()

        matched: list[str] = []
        for sk in skills:
            sk_l = sk.lower()
            if sk_l in j_text:
                matched.append(sk)

        # Base score starts at 75% for top rank, declining slightly down list, plus bonus for skill overlap
        rank_score = max(50, 85 - (idx * 2))
        skill_bonus = min(25, len(matched) * 5)
        score = min(98, rank_score + skill_bonus)

        job_copy = dict(job)
        job_copy["match_score"] = f"{score}%"
        job_copy["matched_skills"] = matched
        scored_jobs.append(job_copy)

    # Sort recommended jobs by match_score descending
    scored_jobs.sort(key=lambda x: int(x["match_score"].replace("%", "")), reverse=True)

    return {
        "jobs": scored_jobs,
        "count": len(scored_jobs),
        "matched_skills": skills,
        "searched_keyword": kw,
        "searched_location": target_loc,
        "fallback_used": result.get("fallback_used", False),
        "fallback_message": result.get("fallback_message", ""),
    }
