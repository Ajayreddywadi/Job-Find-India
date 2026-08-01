from dataclasses import dataclass
from typing import Any
from models.job import Job

@dataclass
class SearchResponse:
    jobs: list[Job]
    fallback_used: bool
    fallback_message: str
    searched_location: str
