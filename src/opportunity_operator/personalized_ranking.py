"""Deterministic person-by-opportunity executability ranking."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from collections.abc import Iterable

from .opportunity_candidate import OpportunityCandidate
from .user_profile import canonicalize_user_profile


@dataclass(frozen=True)
class RankingResult:
    candidate_id: str
    score: int
    fit_band: str
    hard_reject: bool
    reason_codes: tuple[str, ...]


def score_candidate(profile: object, candidate: OpportunityCandidate) -> RankingResult:
    canonical = canonicalize_user_profile(profile)
    if not isinstance(candidate, OpportunityCandidate):
        raise TypeError("candidate must be an OpportunityCandidate")
    willingness = canonical["willingness"]
    reasons: list[str] = []
    hard_reject = False
    score = 0

    if candidate.applicant_feasibility == "INELIGIBLE":
        hard_reject = True
        reasons.append("APPLICANT_INELIGIBLE")
    elif candidate.applicant_feasibility == "ELIGIBLE":
        score += 12
    else:
        score -= 12
        reasons.append("APPLICANT_FEASIBILITY_UNKNOWN")

    if candidate.capital_required is None:
        reasons.append("CAPITAL_REQUIRED_UNKNOWN")
    elif candidate.capital_required > Decimal(canonical["max_cash_spend"]):
        hard_reject = True
        reasons.append("CAPITAL_EXCEEDS_MAX_SPEND")

    if candidate.ai_executability is not None:
        score += candidate.ai_executability // 5
    if candidate.evidence_quality:
        score += candidate.evidence_quality // 5
    if candidate.human_burden is not None:
        autonomy_weight = {"maximum": 3, "mostly_ai": 2, "anything_realistic": 1}[
            canonical["ai_autonomy"]
        ]
        score += (100 - candidate.human_burden) * autonomy_weight // 10
    if candidate.time_to_evidence_days is not None:
        score += max(0, 20 - min(candidate.time_to_evidence_days, 20))

    mismatches = (
        (candidate.requires_business_build, "build_business", "BUSINESS_BUILD_MISMATCH", 25),
        (candidate.requires_customer_work, "work_with_customers", "CUSTOMER_WORK_MISMATCH", 45),
        (candidate.requires_sales, "sell", "SALES_MISMATCH", 45),
        (candidate.requires_content, "publish_content", "CONTENT_MISMATCH", 25),
        (candidate.is_contest_or_jury, "contests_juries", "CONTEST_JURY_MISMATCH", 25),
        (candidate.is_financial_protocol, "financial_protocols", "FINANCIAL_PROTOCOL_MISMATCH", 25),
    )
    for required, preference, reason, penalty in mismatches:
        if required and not willingness[preference]:
            score -= penalty
            reasons.append(reason)
    if (candidate.capital_required is not None
            and candidate.capital_required > 0
            and not willingness["invest_capital"]):
        score -= 25
        reasons.append("CAPITAL_INVESTMENT_MISMATCH")

    if hard_reject:
        score -= 1000
        band = "REJECT"
    elif score >= 70:
        band = "HIGH"
    elif score >= 35:
        band = "MEDIUM"
    else:
        band = "LOW"
    return RankingResult(candidate.candidate_id, score, band, hard_reject, tuple(reasons))


def rank_candidates(profile: object, candidates: Iterable[OpportunityCandidate]) -> tuple[RankingResult, ...]:
    results = tuple(score_candidate(profile, candidate) for candidate in candidates)
    return tuple(sorted(results, key=lambda item: (item.hard_reject, -item.score, item.candidate_id)))
