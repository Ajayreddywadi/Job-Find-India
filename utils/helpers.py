import html
import re
import textwrap
from models.job import Job

# Compile regex at module level for optimal reuse
_RESTRICTED_COUNTRIES_RE = re.compile(r'\b(us|uk|uae)\b', re.IGNORECASE)

def _clean_html(raw: str) -> str:
    """Strip HTML tags and normalise whitespace."""
    decoded = html.unescape(raw or "")
    no_tags = re.sub(r"<[^>]+>", " ", decoded)
    return re.sub(r"\s+", " ", no_tags).strip()

def _truncate(text: str, max_chars: int = 300) -> str:
    """Truncate text to max_chars with ellipsis."""
    return textwrap.shorten(text, width=max_chars, placeholder="…")

def _empty_job() -> Job:
    """Return an empty Job TypedDict instance."""
    return {
        "title":       "",
        "company":     "",
        "location":    "",
        "url":         "",
        "source":      "",
        "date_posted": "",
        "job_type":    "",
        "tags":        "",
        "description": "",
        "salary":      "",
    }

def _is_non_indian_restricted(location: str) -> bool:
    """Check if the job location is restricted to a non-Indian country/region."""
    loc_lower = (location or "").lower().strip()
    if not loc_lower:
        return False

    # If it explicitly contains India or worldwide/global remote indicators, it's open to India.
    _INDIA_FRIENDLY = {"india", "worldwide", "global", "anywhere", "apac", "asia"}
    if any(f in loc_lower for f in _INDIA_FRIENDLY):
        return False

    # Check for known restricted countries/regions/cities
    restricted_words = [
        "germany", "deutschland", "berlin", "munich", "frankfurt", "hamburg",
        "united states", "usa", "america", "united kingdom", "london", "canada",
        "france", "paris", "netherlands", "amsterdam", "sweden", "stockholm",
        "europe", "european", "latam", "spain", "italy", "poland", "romania",
        "swiss", "switzerland", "austria", "belgium", "denmark", "norway", "finland",
        "australia", "sydney", "melbourne", "singapore", "japan", "tokyo"
    ]
    for word in restricted_words:
        if word in loc_lower:
            return True

    # Standalone words check
    if _RESTRICTED_COUNTRIES_RE.search(loc_lower):
        return True

    return False
