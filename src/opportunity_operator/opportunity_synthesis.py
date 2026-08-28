"""Evidence-disciplined conversion of observations into hypotheses."""

from __future__ import annotations

from dataclasses import dataclass
from .opportunity_candidate import CandidateOrigin, OpportunityCandidate


def _valid_text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise ValueError(f"invalid {name}")


def _valid_text_tuple(value: object, name: str) -> None:
    if (not isinstance(value, tuple) or not value or len(value) > 64
            or any(not isinstance(item, str) or not item.strip() or len(item) > 1000
                   for item in value)):
        raise ValueError(f"invalid {name}")


def _valid_optional_text_tuple(value: object, name: str) -> None:
    if (not isinstance(value, tuple) or len(value) > 64
            or any(not isinstance(item, str) or not item.strip() or len(item) > 1000
                   for item in value)):
        raise ValueError(f"invalid {name}")


@dataclass(frozen=True)
class SynthesisObservation:
    observation_id: str
    observed_condition: str
    economic_mechanism: str
    value_source: str
    why_ai_changes_feasibility: str
    assumptions: tuple[str, ...]
    cheap_test: str
    evidence_required: tuple[str, ...]
    source_ids: tuple[str, ...]
    mechanism_hint: str

    def __post_init__(self) -> None:
        for name in (
            "observation_id", "observed_condition", "economic_mechanism",
            "value_source", "why_ai_changes_feasibility", "cheap_test",
        ):
            _valid_text(getattr(self, name), name)
        if (not isinstance(self.mechanism_hint, str)
                or len(self.mechanism_hint) > 2000):
            raise ValueError("invalid mechanism_hint")
        _valid_optional_text_tuple(self.assumptions, "assumptions")
        _valid_text_tuple(self.evidence_required, "evidence_required")
        _valid_text_tuple(self.source_ids, "source_ids")


def build_synthesized_candidate(
    observation: SynthesisObservation, *, candidate_id: str, title: str
) -> OpportunityCandidate:
    if not isinstance(observation, SynthesisObservation):
        raise TypeError("observation must be a SynthesisObservation")
    _valid_text(candidate_id, "candidate_id")
    _valid_text(title, "title")
    # OpportunityCandidate deliberately bounds text fields at 1,000
    # characters. Synthesis observations are richer than that boundary,
    # so hypothesis must be a concise testable proposition rather than a
    # serialization of the entire observation.
    def _hypothesis_fragment(value: str, limit: int) -> str:
        text = value.strip()
        if len(text) <= limit:
            return text
        head = text[: limit - 3].rstrip()
        if " " in head:
            word_safe = head.rsplit(" ", 1)[0].rstrip()
            if word_safe:
                head = word_safe
        return head + "..."

    hypothesis = (
        f"Observed condition: {_hypothesis_fragment(observation.observed_condition, 230)} "
        f"Economic mechanism: {_hypothesis_fragment(observation.economic_mechanism, 300)} "
        f"Value source: {_hypothesis_fragment(observation.value_source, 150)} "
        f"Cheap test: {_hypothesis_fragment(observation.cheap_test, 250)}"
    )
    return OpportunityCandidate(
        candidate_id=candidate_id.strip(), title=title.strip(),
        origin=CandidateOrigin.SYNTHESIZED,
        mechanism=observation.mechanism_hint.strip() or "unspecified", hypothesis=hypothesis,
        economic_mechanism=observation.economic_mechanism.strip(),
        value_source=observation.value_source.strip(), source_ids=observation.source_ids,
        canonical_source_url=None, applicant_feasibility="UNKNOWN",
        capital_required=None, estimated_human_hours=None,
        ai_executability=None, human_burden=None, customer_dependency=None,
        sales_dependency=None, external_decision_dependency=None,
        time_to_evidence_days=None, estimated_upside=None, max_loss=None,
        evidence_quality=0, requires_business_build=False,
        requires_customer_work=False, requires_sales=False, requires_content=False,
        is_contest_or_jury=False, is_financial_protocol=False,
    )
