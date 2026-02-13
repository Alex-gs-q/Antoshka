from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(frozen=True)
class ActionResult:
    text: str
    action: str
    title: str
    details: str = ""
    status: str = "ok"
    url: Optional[str] = None
    meta: Dict[str, str] = field(default_factory=dict)

    def to_text(self) -> str:
        return self.text
