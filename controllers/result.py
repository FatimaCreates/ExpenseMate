from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Result:
    """What a controller hands back to the UI."""
    ok: bool
    message: str = ""
    data: Any = None
    error: Optional[str] = None   # e.g. "validation", "budget_exceeded"
