import re
from models.job import Job

# Simple URL validation regex
_URL_RE = re.compile(
    r'^https?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

def validate_request(keyword: str, location: str) -> None:
    """Validate request query parameters."""
    if not keyword or not keyword.strip():
        raise ValueError("Keyword search parameter is required and cannot be empty.")
    # Add any specific character restriction check if necessary

def validate_job(job: Job) -> bool:
    """Validate a parsed job dictionary against core schema requirements."""
    # Check that required keys are present
    required_keys = {"title", "company", "location", "url", "source"}
    for key in required_keys:
        if not job.get(key) or not str(job[key]).strip():
            return False

    # Check URL format
    url = str(job.get("url", ""))
    if not _URL_RE.match(url):
        return False

    return True
