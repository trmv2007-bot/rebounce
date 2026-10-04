from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(slots=True)
class CompanionIdentity:
    """Persistent identity for one user's companion."""

    user_id: str
    name: str
    companion_id: UUID = field(default_factory=uuid4)
    relationship_style: str = "companion"
    personality: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        if not self.user_id.strip():
            raise ValueError("user_id must not be empty")
        if not self.name:
            raise ValueError("companion name must not be empty")
        if len(self.name) > 80:
            raise ValueError("companion name must be 80 characters or fewer")
