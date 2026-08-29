"""Candidate-2 differentiation prototype contract.

Purpose:
Test whether AOO can produce a source-grounded, compact professional
research digest that is meaningfully different from a generic newsletter.

This module performs no network calls and no model calls.

It does not establish:
- customer demand,
- willingness to pay,
- medical correctness,
- clinical efficacy,
- revenue,
- unit economics,
- or profitability.

The prototype is intended for professional research review only.
"""

from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Any, Mapping, Sequence


PROTOTYPE_KIND = (
    "PEDIATRIC_DENTISTRY_"
    "MONDAY_MORNING_CLINICAL_DIGEST_V1"
)

MIN_SOURCE_RECORDS = 5
MAX_SOURCE_RECORDS = 20

MIN_DIGEST_ITEMS = 3
MAX_DIGEST_ITEMS = 5

DISCLAIMER = (
    "For licensed dental professionals. "
    "Research summary only; not a substitute "
    "for clinical judgment or full-text review."
)

EVIDENCE_REVIEW_VALUES = frozenset(
    {
        "REVIEW_NOW",
        "WATCH",
        "BACKGROUND",
    }
)

_REQUIRED_SOURCE_KEYS = frozenset(
    {
        "source_id",
        "title",
        "publication_date",
        "abstract",
        "source_url",
    }
)

_REQUIRED_OUTPUT_KEYS = frozenset(
    {
        "prototype_kind",
        "digest_title",
        "audience",
        "executive_summary",
        "items",
        "limitations",
        "disclaimer",
    }
)

_REQUIRED_ITEM_KEYS = frozenset(
    {
        "source_ids",
        "topic",
        "what_changed",
        "why_it_matters",
        "practice_review_question",
        "evidence_review",
        "caveats",
    }
)


class ClinicalDigestContractError(
    ValueError
):
    pass


def _text(
    value: object,
    field: str,
    *,
    minimum: int = 1,
    maximum: int = 4000,
) -> str:

    if not isinstance(
        value,
        str,
    ):
        raise ClinicalDigestContractError(
            f"{field}:NOT_STRING"
        )

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    if len(value) < minimum:
        raise ClinicalDigestContractError(
            f"{field}:TOO_SHORT"
        )

    if len(value) > maximum:
        raise ClinicalDigestContractError(
            f"{field}:TOO_LONG"
        )

    return value


def normalize_source_records(
    records: Sequence[
        Mapping[str, object]
    ],
) -> tuple[
    dict[str, str],
    ...,
]:
    """Validate and canonicalize admitted research records."""

    if not isinstance(
        records,
        (list, tuple),
    ):
        raise ClinicalDigestContractError(
            "records:NOT_SEQUENCE"
        )

    if not (
        MIN_SOURCE_RECORDS
        <= len(records)
        <= MAX_SOURCE_RECORDS
    ):
        raise ClinicalDigestContractError(
            "records:COUNT_OUT_OF_RANGE"
        )

    normalized = []
    seen_ids = set()

    for index, record in enumerate(
        records,
        1,
    ):

        if not isinstance(
            record,
            Mapping,
        ):
            raise ClinicalDigestContractError(
                f"record[{index}]:NOT_MAPPING"
            )

        if set(record) != _REQUIRED_SOURCE_KEYS:
            raise ClinicalDigestContractError(
                f"record[{index}]:FIELD_SET_MISMATCH"
            )

        source_id = _text(
            record["source_id"],
            f"record[{index}].source_id",
            maximum=300,
        )

        if source_id in seen_ids:
            raise ClinicalDigestContractError(
                "records:DUPLICATE_SOURCE_ID"
            )

        seen_ids.add(source_id)

        title = _text(
            record["title"],
            f"record[{index}].title",
            maximum=1000,
        )

        publication_date = _text(
            record["publication_date"],
            f"record[{index}].publication_date",
            maximum=32,
        )

        if not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}",
            publication_date,
        ):
            raise ClinicalDigestContractError(
                f"record[{index}].publication_date:INVALID"
            )

        abstract = _text(
            record["abstract"],
            f"record[{index}].abstract",
            minimum=40,
            maximum=12000,
        )

        source_url = _text(
            record["source_url"],
            f"record[{index}].source_url",
            maximum=2000,
        )

        if not source_url.startswith(
            "https://"
        ):
            raise ClinicalDigestContractError(
                f"record[{index}].source_url:NOT_HTTPS"
            )

        normalized.append(
            {
                "source_id":
                    source_id,

                "title":
                    title,

                "publication_date":
                    publication_date,

                "abstract":
                    abstract,

                "source_url":
                    source_url,
            }
        )

    normalized.sort(
        key=lambda item: (
            item["publication_date"],
            item["source_id"],
        ),
        reverse=True,
    )

    return tuple(normalized)


def build_digest_generation_request(
    records: Sequence[
        Mapping[str, object]
    ],
) -> dict[str, object]:
    """Build deterministic, evidence-disciplined generation request."""

    normalized = normalize_source_records(
        records
    )

    evidence_payload = [
        {
            "source_id":
                item["source_id"],

            "title":
                item["title"],

            "publication_date":
                item["publication_date"],

            "abstract":
                item["abstract"],

            "source_url":
                item["source_url"],
        }
        for item in normalized
    ]

    evidence_json = json.dumps(
        evidence_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    source_digest = sha256(
        evidence_json.encode(
            "utf-8"
        )
    ).hexdigest()

    instruction = (
        "Create a concise Monday-morning research digest for licensed "
        "pediatric dentists using ONLY the admitted research records below. "
        "This is not a generic newsletter. The differentiation target is: "
        "(1) cross-source compression, "
        "(2) explicit traceability to source_ids, "
        "(3) what changed, "
        "(4) why it may matter for professional review, "
        "(5) one practice-review question rather than a treatment command, "
        "and (6) explicit caveats. "
        "Do not invent evidence, patient facts, diagnoses, dosages, "
        "treatment instructions, guidelines, effect sizes, or certainty "
        "not present in the supplied records. "
        "Do not claim that an individual study changes standard of care. "
        "Do not provide individualized medical or dental advice. "
        "Every digest item must cite one or more admitted source_ids. "
        "Use 3 to 5 digest items. "
        "evidence_review must be exactly one of "
        "REVIEW_NOW, WATCH, BACKGROUND. "
        "Return only structured JSON matching the supplied schema."
    )

    schema = {
        "type":
            "object",

        "properties":
            {
                "prototype_kind":
                    {
                        "type":
                            "string",
                    },

                "digest_title":
                    {
                        "type":
                            "string",
                    },

                "audience":
                    {
                        "type":
                            "string",
                    },

                "executive_summary":
                    {
                        "type":
                            "string",
                    },

                "items":
                    {
                        "type":
                            "array",

                        "items":
                            {
                                "type":
                                    "object",

                                "properties":
                                    {
                                        "source_ids":
                                            {
                                                "type":
                                                    "array",

                                                "items":
                                                    {
                                                        "type":
                                                            "string",
                                                    },
                                            },

                                        "topic":
                                            {
                                                "type":
                                                    "string",
                                            },

                                        "what_changed":
                                            {
                                                "type":
                                                    "string",
                                            },

                                        "why_it_matters":
                                            {
                                                "type":
                                                    "string",
                                            },

                                        "practice_review_question":
                                            {
                                                "type":
                                                    "string",
                                            },

                                        "evidence_review":
                                            {
                                                "type":
                                                    "string",

                                                "enum":
                                                    [
                                                        "REVIEW_NOW",
                                                        "WATCH",
                                                        "BACKGROUND",
                                                    ],
                                            },

                                        "caveats":
                                            {
                                                "type":
                                                    "string",
                                            },
                                    },

                                "required":
                                    sorted(
                                        _REQUIRED_ITEM_KEYS
                                    ),
                            },
                    },

                "limitations":
                    {
                        "type":
                            "array",

                        "items":
                            {
                                "type":
                                    "string",
                            },
                    },

                "disclaimer":
                    {
                        "type":
                            "string",
                    },
            },

        "required":
            sorted(
                _REQUIRED_OUTPUT_KEYS
            ),
    }

    return {
        "prototype_kind":
            PROTOTYPE_KIND,

        "source_digest":
            source_digest,

        "source_count":
            len(normalized),

        "admitted_source_ids":
            [
                item["source_id"]
                for item in normalized
            ],

        "instruction":
            instruction,

        "evidence":
            evidence_payload,

        "response_schema":
            schema,
    }


def validate_digest_output(
    payload: Mapping[str, object],
    *,
    admitted_source_ids: Sequence[str],
) -> dict[str, object]:
    """Fail closed on unsupported citations or unsafe prototype output."""

    if not isinstance(
        payload,
        Mapping,
    ):
        raise ClinicalDigestContractError(
            "output:NOT_MAPPING"
        )

    if set(payload) != _REQUIRED_OUTPUT_KEYS:
        raise ClinicalDigestContractError(
            "output:FIELD_SET_MISMATCH"
        )

    prototype_kind = _text(
        payload["prototype_kind"],
        "prototype_kind",
        maximum=200,
    )

    if prototype_kind != PROTOTYPE_KIND:
        raise ClinicalDigestContractError(
            "prototype_kind:MISMATCH"
        )

    digest_title = _text(
        payload["digest_title"],
        "digest_title",
        maximum=300,
    )

    audience = _text(
        payload["audience"],
        "audience",
        maximum=300,
    )

    if (
        "pediatric"
        not in audience.lower()
        or "dent"
        not in audience.lower()
    ):
        raise ClinicalDigestContractError(
            "audience:MISMATCH"
        )

    executive_summary = _text(
        payload["executive_summary"],
        "executive_summary",
        maximum=2000,
    )

    items = payload["items"]

    if not isinstance(
        items,
        list,
    ):
        raise ClinicalDigestContractError(
            "items:NOT_LIST"
        )

    if not (
        MIN_DIGEST_ITEMS
        <= len(items)
        <= MAX_DIGEST_ITEMS
    ):
        raise ClinicalDigestContractError(
            "items:COUNT_OUT_OF_RANGE"
        )

    admitted = set(
        admitted_source_ids
    )

    if not admitted:
        raise ClinicalDigestContractError(
            "admitted_source_ids:EMPTY"
        )

    normalized_items = []
    represented_sources = set()

    forbidden_instruction_patterns = (
        r"\bprescribe\b",
        r"\bdiagnose\b",
        r"\bstart\s+(?:the\s+)?patient\b",
        r"\bstop\s+(?:the\s+)?patient\b",
        r"\bincrease\s+(?:the\s+)?dose\b",
        r"\bdecrease\s+(?:the\s+)?dose\b",
        r"\badminister\s+\d",
    )

    for index, item in enumerate(
        items,
        1,
    ):

        if not isinstance(
            item,
            Mapping,
        ):
            raise ClinicalDigestContractError(
                f"item[{index}]:NOT_MAPPING"
            )

        if set(item) != _REQUIRED_ITEM_KEYS:
            raise ClinicalDigestContractError(
                f"item[{index}]:FIELD_SET_MISMATCH"
            )

        source_ids = item[
            "source_ids"
        ]

        if (
            not isinstance(
                source_ids,
                list,
            )
            or not source_ids
        ):
            raise ClinicalDigestContractError(
                f"item[{index}].source_ids:INVALID"
            )

        normalized_source_ids = []

        for source_id in source_ids:
            source_id = _text(
                source_id,
                f"item[{index}].source_id",
                maximum=300,
            )

            if source_id not in admitted:
                raise ClinicalDigestContractError(
                    f"item[{index}]:UNKNOWN_SOURCE_ID"
                )

            if source_id not in normalized_source_ids:
                normalized_source_ids.append(
                    source_id
                )

                represented_sources.add(
                    source_id
                )

        topic = _text(
            item["topic"],
            f"item[{index}].topic",
            maximum=300,
        )

        what_changed = _text(
            item["what_changed"],
            f"item[{index}].what_changed",
            maximum=1500,
        )

        why_it_matters = _text(
            item["why_it_matters"],
            f"item[{index}].why_it_matters",
            maximum=1500,
        )

        review_question = _text(
            item[
                "practice_review_question"
            ],
            f"item[{index}].practice_review_question",
            maximum=1000,
        )

        if not review_question.endswith(
            "?"
        ):
            raise ClinicalDigestContractError(
                f"item[{index}].practice_review_question:NOT_QUESTION"
            )

        evidence_review = _text(
            item["evidence_review"],
            f"item[{index}].evidence_review",
            maximum=50,
        )

        if (
            evidence_review
            not in EVIDENCE_REVIEW_VALUES
        ):
            raise ClinicalDigestContractError(
                f"item[{index}].evidence_review:INVALID"
            )

        caveats = _text(
            item["caveats"],
            f"item[{index}].caveats",
            maximum=1500,
        )

        combined = " ".join(
            (
                what_changed,
                why_it_matters,
                review_question,
            )
        ).lower()

        for pattern in forbidden_instruction_patterns:
            if re.search(
                pattern,
                combined,
                flags=re.I,
            ):
                raise ClinicalDigestContractError(
                    f"item[{index}]:TREATMENT_COMMAND"
                )

        normalized_items.append(
            {
                "source_ids":
                    normalized_source_ids,

                "topic":
                    topic,

                "what_changed":
                    what_changed,

                "why_it_matters":
                    why_it_matters,

                "practice_review_question":
                    review_question,

                "evidence_review":
                    evidence_review,

                "caveats":
                    caveats,
            }
        )

    if len(represented_sources) < 3:
        raise ClinicalDigestContractError(
            "output:INSUFFICIENT_SOURCE_COVERAGE"
        )

    limitations = payload[
        "limitations"
    ]

    if (
        not isinstance(
            limitations,
            list,
        )
        or len(limitations) < 2
    ):
        raise ClinicalDigestContractError(
            "limitations:INSUFFICIENT"
        )

    normalized_limitations = [
        _text(
            value,
            "limitations.item",
            maximum=1000,
        )
        for value in limitations
    ]

    disclaimer = _text(
        payload["disclaimer"],
        "disclaimer",
        maximum=500,
    )

    if disclaimer != DISCLAIMER:
        raise ClinicalDigestContractError(
            "disclaimer:MISMATCH"
        )

    return {
        "prototype_kind":
            prototype_kind,

        "digest_title":
            digest_title,

        "audience":
            audience,

        "executive_summary":
            executive_summary,

        "items":
            normalized_items,

        "limitations":
            normalized_limitations,

        "disclaimer":
            disclaimer,

        "represented_source_count":
            len(
                represented_sources
            ),

        "differentiation_features":
            [
                "cross_source_compression",
                "source_traceability",
                "what_changed",
                "why_it_matters",
                "practice_review_question",
                "explicit_caveats",
            ],

        "economic_claims":
            {
                "customer_demand_proven":
                    False,

                "willingness_to_pay_proven":
                    False,

                "revenue_proven":
                    False,

                "unit_economics_proven":
                    False,

                "profitability_proven":
                    False,

                "promotion_allowed":
                    False,
            },
    }


__all__ = [
    "ClinicalDigestContractError",
    "DISCLAIMER",
    "PROTOTYPE_KIND",
    "build_digest_generation_request",
    "normalize_source_records",
    "validate_digest_output",
]
