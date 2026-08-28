"""Unified, immutable representation of explicit and synthesized candidates."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class CandidateOrigin(StrEnum):
    EXPLICIT = "explicit"
    SYNTHESIZED = "synthesized"


_PERCENT_FIELDS = (
    "ai_executability", "human_burden", "customer_dependency",
    "sales_dependency", "external_decision_dependency",
)
_TEXT_FIELDS = (
    "candidate_id", "title", "mechanism", "hypothesis",
    "economic_mechanism", "value_source",
)


@dataclass(frozen=True)
class OpportunityCandidate:
    candidate_id: str
    title: str
    origin: CandidateOrigin
    mechanism: str
    hypothesis: str
    economic_mechanism: str
    value_source: str
    source_ids: tuple[str, ...]
    canonical_source_url: str | None
    applicant_feasibility: str
    capital_required: Decimal | None
    estimated_human_hours: Decimal | None
    ai_executability: int | None
    human_burden: int | None
    customer_dependency: int | None
    sales_dependency: int | None
    external_decision_dependency: int | None
    time_to_evidence_days: int | None
    estimated_upside: Decimal | None
    max_loss: Decimal | None
    evidence_quality: int
    requires_business_build: bool
    requires_customer_work: bool
    requires_sales: bool
    requires_content: bool
    is_contest_or_jury: bool
    is_financial_protocol: bool

    def __post_init__(self) -> None:
        if not isinstance(self.origin, CandidateOrigin):
            raise ValueError("invalid candidate origin")
        for name in _TEXT_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip() or len(value) > 1000:
                raise ValueError(f"invalid {name}")
        if (not isinstance(self.source_ids, tuple) or not self.source_ids
                or any(not isinstance(item, str) or not item.strip() or len(item) > 256
                       for item in self.source_ids)):
            raise ValueError("at least one valid provenance source is required")
        if self.canonical_source_url is not None and (
            not isinstance(self.canonical_source_url, str)
            or not self.canonical_source_url.strip()
            or len(self.canonical_source_url) > 2048
        ):
            raise ValueError("invalid canonical_source_url")
        if self.applicant_feasibility not in {"ELIGIBLE", "INELIGIBLE", "UNKNOWN"}:
            raise ValueError("invalid applicant_feasibility")
        for name in ("capital_required", "estimated_human_hours", "estimated_upside", "max_loss"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, Decimal) or not value.is_finite() or value < 0):
                raise ValueError(f"invalid {name}")
        if self.capital_required is not None and not isinstance(self.capital_required, Decimal):
            raise TypeError("capital_required must be Decimal or None")
        for name in _PERCENT_FIELDS:
            value = getattr(self, name)
            if value is not None and (type(value) is not int or not 0 <= value <= 100):
                raise ValueError(f"invalid {name}")
        if type(self.evidence_quality) is not int or not 0 <= self.evidence_quality <= 100:
            raise ValueError("invalid evidence_quality")
        if self.time_to_evidence_days is not None and (
            type(self.time_to_evidence_days) is not int or self.time_to_evidence_days < 0
        ):
            raise ValueError("invalid time_to_evidence_days")
        for name in (
            "requires_business_build", "requires_customer_work", "requires_sales",
            "requires_content", "is_contest_or_jury", "is_financial_protocol",
        ):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be boolean")
