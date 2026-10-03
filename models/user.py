from dataclasses import dataclass
from typing import Any

@dataclass
class User:
    id: int
    full_name: str
    email: str
    password_hash: str
    preferred_location: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a safe dictionary representation of the user (excluding password_hash)."""
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "preferred_location": self.preferred_location,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
