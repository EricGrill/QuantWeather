from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExecutionEvent:
    event_type: str
    created_at: str
    payload: dict[str, Any]
