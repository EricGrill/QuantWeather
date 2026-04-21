from __future__ import annotations

from .domain import ApprovalDecision, ApprovalStatus


def can_execute(decision: ApprovalDecision) -> bool:
    return decision.status == ApprovalStatus.APPROVED
