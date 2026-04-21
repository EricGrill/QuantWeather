from __future__ import annotations

import json
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import Any

from .domain import RecommendationRecord


def recommendation_to_dict(record: RecommendationRecord) -> dict[str, Any]:
    payload = asdict(record)
    return _normalize_enums(payload)


def recommendations_to_json(
    records: list[RecommendationRecord],
    indent: int = 2,
) -> str:
    payload = [recommendation_to_dict(record) for record in records]
    return json.dumps(payload, indent=indent, sort_keys=True)


def write_recommendations_json(
    records: list[RecommendationRecord],
    path: str | Path,
    indent: int = 2,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(recommendations_to_json(records, indent=indent) + "\n", encoding="utf-8")
    return output_path


def _normalize_enums(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _normalize_enums(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_enums(item) for item in value]
    return value
