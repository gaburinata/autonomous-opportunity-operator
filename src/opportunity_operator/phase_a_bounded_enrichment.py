"""Phase-A bounded-test contract for real synthesized opportunities.

This module does not execute network requests, models, trades, customer
contact, publishing, payments or other consequential actions.

Phase A is deliberately narrow. For the Coinbase/Kraken monitoring-product
hypothesis it may admit bounded technical evidence about automation
executability only.

It must not convert a technical prototype into claims about:
- customer demand,
- willingness to pay,
- revenue,
- unit economics,
- capital requirements,
- human operating burden,
- sales dependency,
- upside,
- maximum loss,
- or eligibility.

Those remain unknown until independently supported.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping

from opportunity_operator.enrichment_evidence import (
    ENRICHABLE_FIELDS,
    apply_enrichment_evidence,
    validate_enrichment_evidence,
)
from opportunity_operator.opportunity_candidate import (
    CandidateOrigin,
    OpportunityCandidate,
)
from opportunity_operator.personalized_ranking import (
    score_candidate,
)
from opportunity_operator.product_integration import (
    build_product_view,
)


PHASE_A_TEST_KIND = (
    "COINBASE_KRAKEN_SPREAD_MONITOR_TECHNICAL_FEASIBILITY_V1"
)

_REQUIRED_SOURCE_IDS = frozenset(
    {
        "coinbase-btcusd-live",
        "kraken-xbtusd-live",
    }
)

# A bounded market-data capture can directly test whether the intended
# machine loop can operate reliably. It cannot prove the commercial claims.
PHASE_A_ALLOWED_ENRICHMENT_FIELDS = frozenset(
    {
        "ai_executability",
    }
)

PHASE_A_FORBIDDEN_ENRICHMENT_FIELDS = frozenset(
    set(ENRICHABLE_FIELDS)
    - set(PHASE_A_ALLOWED_ENRICHMENT_FIELDS)
)


def _valid_text(
    value: object,
    name: str,
    *,
    limit: int = 256,
) -> str:

    if not isinstance(
        value,
        str,
    ):
        raise TypeError(
            f"{name} must be text"
        )

    normalized = value.strip()

    if (
        not normalized
        or len(normalized) > limit
    ):
        raise ValueError(
            f"invalid {name}"
        )

    return normalized


def _require_target_candidate(
    candidate: OpportunityCandidate,
) -> None:

    if not isinstance(
        candidate,
        OpportunityCandidate,
    ):
        raise TypeError(
            "candidate must be OpportunityCandidate"
        )

    if (
        candidate.origin
        is not CandidateOrigin.SYNTHESIZED
    ):
        raise ValueError(
            "phase A requires synthesized candidate"
        )

    missing = (
        _REQUIRED_SOURCE_IDS
        - set(
            candidate.source_ids
        )
    )

    if missing:
        raise ValueError(
            "candidate lacks required market provenance"
        )

    title = candidate.title.lower()
    mechanism = candidate.mechanism.lower()

    if (
        "coinbase" not in title
        or "kraken" not in title
        or "monitor" not in (
            title
            + " "
            + mechanism
        )
    ):
        raise ValueError(
            "candidate is not the phase-A spread-monitor target"
        )


def build_phase_a_test_plan(
    candidate: OpportunityCandidate,
    *,
    duration_seconds: int = 120,
    interval_seconds: int = 2,
) -> dict[str, Any]:
    """Return deterministic zero-consequence technical test plan."""

    _require_target_candidate(
        candidate
    )

    if (
        type(duration_seconds) is not int
        or not 60 <= duration_seconds <= 900
    ):
        raise ValueError(
            "invalid duration_seconds"
        )

    if (
        type(interval_seconds) is not int
        or not 1 <= interval_seconds <= 30
    ):
        raise ValueError(
            "invalid interval_seconds"
        )

    planned_samples = (
        duration_seconds
        // interval_seconds
    )

    if planned_samples < 10:
        raise ValueError(
            "insufficient planned samples"
        )

    identity_material = (
        "phase-a-v1"
        + "|"
        + candidate.candidate_id
        + "|"
        + str(duration_seconds)
        + "|"
        + str(interval_seconds)
        + "|"
        + ",".join(
            sorted(
                candidate.source_ids
            )
        )
    )

    plan_id = (
        "phase-a-"
        + sha256(
            identity_material.encode(
                "utf-8"
            )
        ).hexdigest()
    )

    return {
        "status":
            "PASS",

        "plan_id":
            plan_id,

        "candidate_id":
            candidate.candidate_id,

        "test_kind":
            PHASE_A_TEST_KIND,

        "duration_seconds":
            duration_seconds,

        "interval_seconds":
            interval_seconds,

        "planned_samples":
            planned_samples,

        "capture":
            {
                "coinbase":
                    "BTC-USD best bid/ask",

                "kraken":
                    "XBT/USD best bid/ask",

                "required_metrics":
                    [
                        "capture_timestamp",
                        "source_success",
                        "best_bid",
                        "best_ask",
                        "raw_direction_1_bps",
                        "raw_direction_2_bps",
                    ],
            },

        "constraints":
            {
                "capital_at_risk":
                    0,

                "trades":
                    0,

                "orders":
                    0,

                "public_posting":
                    0,

                "customer_contact":
                    0,

                "model_calls":
                    0,
            },

        "evidence_contract":
            {
                "new_evidence_id_required":
                    True,

                "method":
                    "BOUNDED_TEST",

                "allowed_enrichment_fields":
                    sorted(
                        PHASE_A_ALLOWED_ENRICHMENT_FIELDS
                    ),

                "forbidden_enrichment_fields":
                    sorted(
                        PHASE_A_FORBIDDEN_ENRICHMENT_FIELDS
                    ),

                "may_prove_customer_demand":
                    False,

                "may_prove_willingness_to_pay":
                    False,

                "may_prove_revenue":
                    False,

                "may_prove_unit_economics":
                    False,

                "may_promote":
                    False,
            },
    }


def apply_phase_a_bounded_test_evidence(
    profile: object,
    candidate: OpportunityCandidate,
    test_record: object,
) -> dict[str, Any]:
    """Admit only narrowly supported Phase-A bounded-test enrichment."""

    _require_target_candidate(
        candidate
    )

    if not isinstance(
        test_record,
        Mapping,
    ):
        raise TypeError(
            "test_record must be mapping"
        )

    expected_keys = {
        "candidate_id",
        "evidence_id",
        "test_kind",
        "measurements",
    }

    if set(test_record) != expected_keys:
        raise ValueError(
            "invalid phase-A test record keys"
        )

    supplied_candidate_id = _valid_text(
        test_record[
            "candidate_id"
        ],
        "candidate_id",
    )

    if (
        supplied_candidate_id
        != candidate.candidate_id
    ):
        raise ValueError(
            "candidate identity mismatch"
        )

    if (
        test_record[
            "test_kind"
        ]
        != PHASE_A_TEST_KIND
    ):
        raise ValueError(
            "invalid phase-A test kind"
        )

    evidence_id = _valid_text(
        test_record[
            "evidence_id"
        ],
        "evidence_id",
    )

    if evidence_id in set(
        candidate.source_ids
    ):
        raise ValueError(
            "phase-A evidence id must be newly admitted"
        )

    raw_measurements = test_record[
        "measurements"
    ]

    if (
        not isinstance(
            raw_measurements,
            (list, tuple),
        )
        or not raw_measurements
    ):
        raise ValueError(
            "phase-A measurements required"
        )

    normalized_payload = {
        "candidate_id":
            candidate.candidate_id,

        "measurements":
            [],
    }

    for measurement in raw_measurements:

        if not isinstance(
            measurement,
            Mapping,
        ):
            raise TypeError(
                "measurement must be mapping"
            )

        field = measurement.get(
            "field"
        )

        if field not in (
            PHASE_A_ALLOWED_ENRICHMENT_FIELDS
        ):
            raise ValueError(
                "phase-A field is not directly supported"
            )

        if measurement.get(
            "method"
        ) != "BOUNDED_TEST":
            raise ValueError(
                "phase-A measurements must use BOUNDED_TEST"
            )

        ids = measurement.get(
            "evidence_ids"
        )

        if (
            not isinstance(
                ids,
                (list, tuple),
            )
            or tuple(ids)
            != (
                evidence_id,
            )
        ):
            raise ValueError(
                "phase-A measurement must cite only its bounded-test evidence"
            )

        normalized_payload[
            "measurements"
        ].append(
            dict(
                measurement
            )
        )

    allowed_evidence_ids = tuple(
        candidate.source_ids
    ) + (
        evidence_id,
    )

    measurements = validate_enrichment_evidence(
        normalized_payload,
        candidate_id=
            candidate.candidate_id,
        allowed_evidence_ids=
            allowed_evidence_ids,
    )

    enriched = apply_enrichment_evidence(
        candidate,
        measurements,
    )

    ranking_before = score_candidate(
        profile,
        candidate,
    )

    ranking_after = score_candidate(
        profile,
        enriched,
    )

    product_view = build_product_view(
        profile,
        {
            "items":
                [],
        },
        synthesized_candidates=(
            enriched,
        ),
    )

    inbox_ids = {
        item[
            "candidate_id"
        ]
        for item in product_view.get(
            "decision_inbox",
            []
        )
    }

    unknown_fields = [
        field
        for field in ENRICHABLE_FIELDS
        if (
            getattr(
                enriched,
                field,
            )
            is None
            or (
                field
                == "applicant_feasibility"
                and getattr(
                    enriched,
                    field,
                )
                == "UNKNOWN"
            )
        )
    ]

    return {
        "status":
            "PASS",

        "candidate_id":
            candidate.candidate_id,

        "test_kind":
            PHASE_A_TEST_KIND,

        "evidence_id":
            evidence_id,

        "measurement_fields":
            [
                item.field
                for item in measurements
            ],

        "evidence_quality_before":
            candidate.evidence_quality,

        "evidence_quality_after":
            enriched.evidence_quality,

        "ranking_before":
            {
                "score":
                    ranking_before.score,

                "fit_band":
                    ranking_before.fit_band,

                "hard_reject":
                    ranking_before.hard_reject,

                "reason_codes":
                    list(
                        ranking_before.reason_codes
                    ),
            },

        "ranking_after":
            {
                "score":
                    ranking_after.score,

                "fit_band":
                    ranking_after.fit_band,

                "hard_reject":
                    ranking_after.hard_reject,

                "reason_codes":
                    list(
                        ranking_after.reason_codes
                    ),
            },

        "unknown_enrichment_fields":
            unknown_fields,

        "decision_inbox_eligible":
            (
                candidate.candidate_id
                in inbox_ids
            ),

        "economic_evidence":
            {
                "unit_economics_present":
                    False,

                "promotion_allowed":
                    False,

                "reason_codes":
                    [
                        "INSUFFICIENT_ECONOMIC_EVIDENCE",
                    ],
            },

        "candidate_after":
            enriched,
    }


__all__ = [
    "PHASE_A_ALLOWED_ENRICHMENT_FIELDS",
    "PHASE_A_FORBIDDEN_ENRICHMENT_FIELDS",
    "PHASE_A_TEST_KIND",
    "apply_phase_a_bounded_test_evidence",
    "build_phase_a_test_plan",
]
