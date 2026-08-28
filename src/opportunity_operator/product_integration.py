"""Model-free integration of V3 candidates into the four product surfaces."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from .opportunity_candidate import CandidateOrigin, OpportunityCandidate
from .personalized_ranking import rank_candidates
from .user_profile import canonicalize_user_profile


_CONTEST_TERMS = ("challenge", "competition", "contest", "hackathon", "jury", "prize", "devpost")


def _text(value: object, fallback: str) -> str:
    if value is None:
        return fallback
    result = str(value).strip()
    return result[:1000] or fallback


def _decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() and result >= 0 else None


def adapt_explicit_feed_item(item: object) -> OpportunityCandidate:
    """Conservatively adapt one existing discovery item without inventing facts."""
    if not isinstance(item, Mapping):
        raise TypeError("feed item must be a mapping")
    candidate_id = _text(item.get("opportunity_id") or item.get("candidate_id"), "")
    if not candidate_id:
        raise ValueError("explicit candidate requires stable identity")
    source_url = item.get("canonical_source_url")
    if not isinstance(source_url, str) or not source_url.strip():
        source_url = None
    else:
        source_url = source_url.strip()
    classification_text = " ".join(
        _text(item.get(key), "")
        for key in ("title", "organizer", "economic_mechanism", "discovered_via", "type", "category")
    ).casefold()
    is_contest = any(term in classification_text for term in _CONTEST_TERMS)
    eligibility = str(item.get("eligibility", "UNKNOWN")).strip().upper()
    if eligibility not in {"ELIGIBLE", "INELIGIBLE"}:
        eligibility = "UNKNOWN"
    effort = _decimal(item.get("estimated_effort_hours"))
    confidence = item.get("confidence")
    evidence_quality = 0
    if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
        evidence_quality = max(0, min(100, round(float(confidence) * 100)))
    return OpportunityCandidate(
        candidate_id=candidate_id,
        title=_text(item.get("title"), "Untitled opportunity"),
        origin=CandidateOrigin.EXPLICIT,
        mechanism=_text(item.get("asset_fit"), "Externally offered opportunity"),
        hypothesis=_text(item.get("decision"), "Requires source verification"),
        economic_mechanism=_text(item.get("economic_mechanism"), "Unknown"),
        value_source=_text(item.get("organizer"), "Unknown external source"),
        source_ids=(source_url or _text(item.get("discovered_via"), candidate_id),),
        canonical_source_url=source_url,
        applicant_feasibility=eligibility,
        capital_required=_decimal(item.get("capital_required")),
        estimated_human_hours=effort,
        ai_executability=None,
        human_burden=None,
        customer_dependency=None,
        sales_dependency=None,
        external_decision_dependency=None,
        time_to_evidence_days=None,
        estimated_upside=None,
        max_loss=None,
        evidence_quality=evidence_quality,
        requires_business_build=False,
        requires_customer_work=False,
        requires_sales=False,
        requires_content=False,
        is_contest_or_jury=is_contest,
        is_financial_protocol=False,
    )


def _human_item(candidate: OpportunityCandidate, ranking: object, lane: str) -> dict[str, Any]:
    unknowns = []
    fields = (
        ("applicant feasibility", candidate.applicant_feasibility == "UNKNOWN"),
        ("capital_required", candidate.capital_required is None),
        ("human work", candidate.estimated_human_hours is None),
        ("AI executability", candidate.ai_executability is None),
        ("time to evidence", candidate.time_to_evidence_days is None),
        ("estimated upside", candidate.estimated_upside is None),
    )
    unknowns.extend(label for label, unknown in fields if unknown)
    reasons = list(ranking.reason_codes)
    if not reasons:
        reasons = ["PERSON_OPPORTUNITY_FIT"]
    return {
        "candidate_id": candidate.candidate_id,
        "title": candidate.title,
        "origin": candidate.origin.value,
        "product_lane": lane,
        "fit_band": ranking.fit_band,
        "reason_codes": reasons,
        "why_surfaced": [code.replace("_", " ").capitalize() for code in reasons],
        "applicant_feasibility": candidate.applicant_feasibility,
        "human_work_hours": (str(candidate.estimated_human_hours) if candidate.estimated_human_hours is not None else None),
        "ai_executability": candidate.ai_executability,
        "capital_required": (str(candidate.capital_required)
                             if candidate.capital_required is not None else None),
        "time_to_evidence_days": candidate.time_to_evidence_days,
        "source_url": candidate.canonical_source_url,
        "unknowns": unknowns,
    }


def build_product_view(profile: object, feed: object, synthesized_candidates: Iterable[OpportunityCandidate] = ()) -> dict[str, Any]:
    """Return the deterministic, JSON-safe, person-by-opportunity product view."""
    canonical = canonicalize_user_profile(profile)
    items = feed.get("items", ()) if isinstance(feed, Mapping) else ()
    if not isinstance(items, (list, tuple)):
        items = ()
    candidates = [adapt_explicit_feed_item(item) for item in items if isinstance(item, Mapping)]
    for candidate in synthesized_candidates:
        if not isinstance(candidate, OpportunityCandidate):
            raise TypeError("synthesized candidates must be OpportunityCandidate values")
        if candidate.origin is not CandidateOrigin.SYNTHESIZED:
            raise ValueError("only synthesized candidates may enter Build & Operate")
        candidates.append(candidate)
    by_id = {candidate.candidate_id: candidate for candidate in candidates}
    rankings = rank_candidates(canonical, candidates)
    rendered: dict[str, dict[str, Any]] = {}
    lanes = {"build_operate": [], "open_opportunities": [], "challenges_competitions": []}
    for ranking in rankings:
        candidate = by_id[ranking.candidate_id]
        lane = ("build_operate" if candidate.origin is CandidateOrigin.SYNTHESIZED else
                "challenges_competitions" if candidate.is_contest_or_jury else "open_opportunities")
        item = _human_item(candidate, ranking, lane)
        rendered[candidate.candidate_id] = item
        lanes[lane].append(item)
    source_rejects = {
        candidate.candidate_id
        for candidate in candidates
        if (candidate.origin is CandidateOrigin.EXPLICIT
            and candidate.hypothesis.strip().upper() in {"KILL", "REJECT"})
    }
    # Decision Inbox is an attention boundary, not simply the top-N
    # non-rejected candidates.
    #
    # Synthesized hypotheses are epistemically different from explicit,
    # externally offered opportunities: a raw synthesized hypothesis must
    # earn MEDIUM/HIGH fit before interrupting the user. An explicit
    # opportunity may still surface at LOW fit when applicant eligibility
    # is confirmed and primary evidence is already strong.
    decision_evidence_min = 70
    synthesized_required_fields = (
        "capital_required",
        "estimated_human_hours",
        "ai_executability",
        "human_burden",
        "customer_dependency",
        "sales_dependency",
        "external_decision_dependency",
        "time_to_evidence_days",
        "estimated_upside",
        "max_loss",
    )

    def decision_inbox_eligible(result: RankingResult) -> bool:
        candidate = by_id[result.candidate_id]

        if result.hard_reject or result.candidate_id in source_rejects:
            return False

        if candidate.origin is CandidateOrigin.SYNTHESIZED:
            complete = (
                candidate.applicant_feasibility != "UNKNOWN"
                and all(
                    getattr(candidate, field) is not None
                    for field in synthesized_required_fields
                )
            )
            return (
                complete
                and candidate.evidence_quality >= decision_evidence_min
                and result.fit_band in {"HIGH", "MEDIUM"}
            )

        if result.fit_band in {"HIGH", "MEDIUM"}:
            return True

        return (
            candidate.applicant_feasibility == "ELIGIBLE"
            and candidate.evidence_quality >= decision_evidence_min
        )

    inbox = [
        rendered[result.candidate_id]
        for result in rankings
        if decision_inbox_eligible(result)
    ][:3]
    return {
        "status": "PASS",
        "profile": canonical,
        "decision_inbox": inbox,
        **lanes,
        "counts": {"decision_inbox": len(inbox), **{key: len(value) for key, value in lanes.items()}},
    }
