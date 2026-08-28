from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import Mapping

from opportunity_operator.opportunity_candidate import OpportunityCandidate


ENRICHABLE_FIELDS = (
    "applicant_feasibility",
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

ALLOWED_METHODS = frozenset(
    {
        "DETERMINISTIC_TOOL",
        "PRIMARY_SOURCE",
        "BOUNDED_TEST",
    }
)

_DECIMAL_FIELDS = frozenset(
    {
        "capital_required",
        "estimated_human_hours",
        "estimated_upside",
        "max_loss",
    }
)

_PERCENT_FIELDS = frozenset(
    {
        "ai_executability",
        "human_burden",
        "customer_dependency",
        "sales_dependency",
        "external_decision_dependency",
    }
)


@dataclass(frozen=True)
class EnrichmentMeasurement:
    field: str
    value: object
    method: str
    confidence: int
    evidence_ids: tuple[str, ...]


def _valid_text(value: object, name: str, limit: int = 256) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be text")

    normalized = value.strip()

    if not normalized or len(normalized) > limit:
        raise ValueError(f"invalid {name}")

    return normalized


def _normalize_decimal(value: object, field: str) -> Decimal:
    # JSON-facing monetary/hour estimates use strings deliberately so
    # binary float ambiguity cannot enter deterministic candidate state.
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a decimal string")

    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"invalid {field}") from exc

    if not number.is_finite() or number < 0:
        raise ValueError(f"invalid {field}")

    return number


def _normalize_value(field: str, value: object) -> object:
    if field == "applicant_feasibility":
        if value not in {"ELIGIBLE", "INELIGIBLE", "UNKNOWN"}:
            raise ValueError("invalid applicant_feasibility")
        return value

    if field in _DECIMAL_FIELDS:
        return _normalize_decimal(value, field)

    if field in _PERCENT_FIELDS:
        if type(value) is not int or not 0 <= value <= 100:
            raise ValueError(f"invalid {field}")
        return value

    if field == "time_to_evidence_days":
        if type(value) is not int or value < 0:
            raise ValueError("invalid time_to_evidence_days")
        return value

    raise ValueError("unsupported enrichment field")


def validate_enrichment_evidence(
    payload: object,
    *,
    candidate_id: str,
    allowed_evidence_ids: tuple[str, ...],
) -> tuple[EnrichmentMeasurement, ...]:
    """
    Validate structured candidate enrichment evidence.

    Narrative model judgment is intentionally insufficient. A measurement
    must be attributed to a deterministic tool, primary source, or bounded
    test and must cite evidence already admitted by the caller.
    """
    if not isinstance(payload, Mapping):
        raise TypeError("enrichment payload must be a mapping")

    if set(payload) != {"candidate_id", "measurements"}:
        raise ValueError("invalid enrichment payload keys")

    expected_candidate_id = _valid_text(
        candidate_id,
        "candidate_id",
    )

    supplied_candidate_id = _valid_text(
        payload["candidate_id"],
        "candidate_id",
    )

    if supplied_candidate_id != expected_candidate_id:
        raise ValueError("candidate identity mismatch")

    allowed = {
        _valid_text(item, "allowed_evidence_id")
        for item in allowed_evidence_ids
    }

    if not allowed:
        raise ValueError("at least one allowed evidence id is required")

    raw_measurements = payload["measurements"]

    if (
        not isinstance(raw_measurements, (list, tuple))
        or not raw_measurements
        or len(raw_measurements) > len(ENRICHABLE_FIELDS)
    ):
        raise ValueError("invalid measurements")

    normalized: list[EnrichmentMeasurement] = []
    seen_fields: set[str] = set()

    for raw in raw_measurements:
        if not isinstance(raw, Mapping):
            raise TypeError("measurement must be a mapping")

        if set(raw) != {
            "field",
            "value",
            "method",
            "confidence",
            "evidence_ids",
        }:
            raise ValueError("invalid measurement keys")

        field = _valid_text(raw["field"], "field")

        if field not in ENRICHABLE_FIELDS:
            raise ValueError("unsupported enrichment field")

        if field in seen_fields:
            raise ValueError("duplicate enrichment field")

        seen_fields.add(field)

        method = _valid_text(raw["method"], "method")

        if method not in ALLOWED_METHODS:
            raise ValueError("non-authoritative enrichment method")

        confidence = raw["confidence"]

        if type(confidence) is not int or not 0 <= confidence <= 100:
            raise ValueError("invalid enrichment confidence")

        evidence_ids = raw["evidence_ids"]

        if (
            not isinstance(evidence_ids, (list, tuple))
            or not evidence_ids
            or len(evidence_ids) > 64
        ):
            raise ValueError("invalid enrichment evidence ids")

        normalized_ids = tuple(
            _valid_text(item, "evidence_id")
            for item in evidence_ids
        )

        if len(set(normalized_ids)) != len(normalized_ids):
            raise ValueError("duplicate enrichment evidence id")

        unknown = set(normalized_ids) - allowed

        if unknown:
            raise ValueError("unknown enrichment evidence id")

        normalized.append(
            EnrichmentMeasurement(
                field=field,
                value=_normalize_value(
                    field,
                    raw["value"],
                ),
                method=method,
                confidence=confidence,
                evidence_ids=normalized_ids,
            )
        )

    return tuple(normalized)


def evidence_quality_from_measurements(
    measurements: tuple[EnrichmentMeasurement, ...],
) -> int:
    """
    Conservative coverage-weighted quality.

    Missing enrichment fields contribute zero. Therefore one strong fact
    cannot make an otherwise-unknown synthesized opportunity appear to
    have globally strong evidence.
    """
    if not isinstance(measurements, tuple):
        raise TypeError("measurements must be a tuple")

    by_field = {
        item.field: item
        for item in measurements
    }

    if len(by_field) != len(measurements):
        raise ValueError("duplicate enrichment field")

    total = sum(
        by_field[field].confidence
        if field in by_field
        else 0
        for field in ENRICHABLE_FIELDS
    )

    quality = round(
        total / len(ENRICHABLE_FIELDS)
    )

    return max(0, min(100, quality))


def apply_enrichment_evidence(
    candidate: OpportunityCandidate,
    measurements: tuple[EnrichmentMeasurement, ...],
) -> OpportunityCandidate:
    """
    Fill unknown candidate fields only.

    Existing known facts may be repeated identically for idempotence but
    cannot be silently overwritten by later enrichment.
    """
    if not isinstance(candidate, OpportunityCandidate):
        raise TypeError("candidate must be an OpportunityCandidate")

    if not isinstance(measurements, tuple) or not measurements:
        raise ValueError("measurements are required")

    updates: dict[str, object] = {}

    for measurement in measurements:
        if not isinstance(measurement, EnrichmentMeasurement):
            raise TypeError("invalid enrichment measurement")

        field = measurement.field
        current = getattr(candidate, field)
        proposed = measurement.value

        unknown = (
            current is None
            or (
                field == "applicant_feasibility"
                and current == "UNKNOWN"
            )
        )

        if unknown:
            updates[field] = proposed
            continue

        if current != proposed:
            raise ValueError(
                f"conflicting enrichment for {field}"
            )

    quality = evidence_quality_from_measurements(
        measurements
    )

    updates["evidence_quality"] = max(
        candidate.evidence_quality,
        quality,
    )

    return replace(
        candidate,
        **updates,
    )
