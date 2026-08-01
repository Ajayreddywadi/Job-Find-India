from dataclasses import dataclass

@dataclass
class SearchRequest:
    keyword: str
    location: str = ""
    timeout: int = 20
