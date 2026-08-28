from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from enum import Enum
from typing import Any

from opportunity_operator.enrichment_evidence import (
    apply_enrichment_evidence,
    validate_enrichment_evidence,
)
from opportunity_operator.opportunity_candidate import OpportunityCandidate
from opportunity_operator.personalized_ranking import score_candidate


def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]

    if isinstance(value, list):
        return [_json_safe(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    return value


def _candidate_json(candidate: OpportunityCandidate) -> dict[str, object]:
    return {
        key: _json_safe(value)
        for key, value in asdict(candidate).items()
    }


def _ranking_json(result: object) -> dict[str, object]:
    return {
        "candidate_id": result.candidate_id,
        "score": result.score,
        "fit_band": result.fit_band,
        "hard_reject": result.hard_reject,
        "reason_codes": list(result.reason_codes),
    }


def enrich_and_rerank_candidate(
    profile: object,
    candidate: OpportunityCandidate,
    enrichment_payload: object,
    *,
    allowed_evidence_ids: tuple[str, ...],
) -> dict[str, Any]:
    """
    Apply only validated enrichment evidence and deterministically re-rank.

    This function performs no model, network, cloud, filesystem, trading,
    payment, registration, submission, or other consequential action.
    """
    if not isinstance(candidate, OpportunityCandidate):
        raise TypeError("candidate must be an OpportunityCandidate")

    before = score_candidate(
        profile,
        candidate,
    )

    measurements = validate_enrichment_evidence(
        enrichment_payload,
        candidate_id=candidate.candidate_id,
        allowed_evidence_ids=allowed_evidence_ids,
    )

    enriched = apply_enrichment_evidence(
        candidate,
        measurements,
    )

    after = score_candidate(
        profile,
        enriched,
    )

    return {
        "status": "PASS",
        "candidate_before": _candidate_json(candidate),
        "candidate_after": _candidate_json(enriched),
        "ranking_before": _ranking_json(before),
        "ranking_after": _ranking_json(after),
        "measurement_count": len(measurements),
        "evidence_ids": sorted(
            {
                evidence_id
                for measurement in measurements
                for evidence_id in measurement.evidence_ids
            }
        ),
    }
