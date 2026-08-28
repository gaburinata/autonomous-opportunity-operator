from __future__ import annotations

from decimal import Decimal

from .models import EconomicEvidenceDecision, Opportunity, State


def adjudicate_economics(opportunity: Opportunity, evidence_ids: tuple[str, ...],
                         has_failure_warning: bool) -> EconomicEvidenceDecision:
    economics = opportunity.unit_economics
    if economics is None or not evidence_ids:
        return EconomicEvidenceDecision(State.WATCH, None, None, None, Decimal("0"), evidence_ids,
                                        ("INSUFFICIENT_ECONOMIC_EVIDENCE",), True)
    margin = economics.margin_per_unit
    if margin <= 0:
        return EconomicEvidenceDecision(State.KILL, economics.revenue_per_unit,
                                        economics.variable_cost_per_unit, margin, economics.confidence,
                                        evidence_ids, ("NON_POSITIVE_UNIT_MARGIN",))
    if economics.confidence < Decimal("0.70") or has_failure_warning:
        reasons = ["LOW_CONFIDENCE"] if economics.confidence < Decimal("0.70") else []
        if has_failure_warning:
            reasons.append("KNOWN_FAILURE_SIMILARITY")
        return EconomicEvidenceDecision(State.WATCH, economics.revenue_per_unit,
                                        economics.variable_cost_per_unit, margin, economics.confidence,
                                        evidence_ids, tuple(reasons))
    return EconomicEvidenceDecision(State.PROMOTE, economics.revenue_per_unit,
                                    economics.variable_cost_per_unit, margin, economics.confidence,
                                    evidence_ids, ("POSITIVE_UNIT_ECONOMICS",))

