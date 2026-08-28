from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from .models import GateDecision, Opportunity, State


def hard_gate(opportunity: Opportunity, now: datetime | None = None) -> GateDecision:
    now = now or datetime.now(timezone.utc)
    reasons: list[str] = []
    if not opportunity.eligible:
        reasons.append("INELIGIBLE")
    if opportunity.deadline_utc is not None and opportunity.deadline_utc <= now:
        reasons.append("DEADLINE_EXPIRED")
    if reasons:
        return GateDecision(False, False, State.KILL, tuple(reasons))
    if (opportunity.capital_required > Decimal("0") or
            opportunity.requires_account_action or opportunity.requires_legal_action):
        if opportunity.capital_required > 0:
            reasons.append("CAPITAL_APPROVAL_REQUIRED")
        if opportunity.requires_account_action:
            reasons.append("ACCOUNT_ACTION_REQUIRED")
        if opportunity.requires_legal_action:
            reasons.append("LEGAL_ACTION_REQUIRED")
        return GateDecision(False, False, State.DECISION_REQUIRED, tuple(reasons))
    return GateDecision(True, True, None, ("HARD_GATES_PASSED",))

