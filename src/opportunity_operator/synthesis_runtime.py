"""Deterministic, vendor-independent evidence-backed synthesis boundary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import fields
from decimal import Decimal
from enum import Enum
import hashlib
import json
from urllib.parse import urlsplit

from .opportunity_synthesis import SynthesisObservation, build_synthesized_candidate
from .user_profile import canonicalize_user_profile


_EVIDENCE_KEYS = {"source_id", "source_url", "title", "excerpt"}
_OBSERVATION_KEYS = {
    "title", "observed_condition", "economic_mechanism", "value_source",
    "why_ai_changes_feasibility", "assumptions", "cheap_test",
    "evidence_required", "source_ids", "mechanism_hint",
}
_MAX_EVIDENCE = 64
_MAX_OBSERVATIONS = 32
_MAX_LIST = 64

SYNTHESIS_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["observations"],
    "properties": {
        "observations": {
            "type": "array", "maxItems": _MAX_OBSERVATIONS,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": sorted(_OBSERVATION_KEYS),
                "properties": {
                    "title": {"type": "string", "minLength": 1, "maxLength": 1000},
                    **{name: {"type": "string", "minLength": 1, "maxLength": 2000}
                       for name in ("observed_condition", "economic_mechanism", "value_source",
                                    "why_ai_changes_feasibility", "cheap_test")},
                    "mechanism_hint": {"type": "string", "maxLength": 2000},
                    **{name: {"type": "array", "maxItems": _MAX_LIST,
                              "items": {"type": "string", "minLength": 1, "maxLength": 1000}}
                       for name in ("assumptions",)},
                    **{name: {"type": "array", "minItems": 1, "maxItems": _MAX_LIST,
                              "items": {"type": "string", "minLength": 1, "maxLength": 1000}}
                       for name in ("evidence_required", "source_ids")},
                },
            },
        }
    },
}


def _text(value: object, name: str, maximum: int, *, empty: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be text")
    value = value.strip()
    if (not empty and not value) or len(value) > maximum:
        raise ValueError(f"invalid {name}")
    return value


def _list(value: object, name: str, *, empty: bool = False) -> tuple[str, ...]:
    if (not isinstance(value, Sequence) or isinstance(value, (str, bytes))
            or len(value) > _MAX_LIST or (not empty and not value)):
        raise ValueError(f"invalid {name}")
    return tuple(_text(item, name, 1000) for item in value)


def canonicalize_evidence_items(items: object) -> list[dict[str, str]]:
    """Validate and return a deterministically ordered independent evidence bundle."""
    if (not isinstance(items, Sequence) or isinstance(items, (str, bytes))
            or not items or len(items) > _MAX_EVIDENCE):
        raise ValueError("invalid evidence items")
    result = []
    seen = set()
    for item in items:
        if not isinstance(item, Mapping) or set(item) != _EVIDENCE_KEYS:
            raise ValueError("invalid evidence item keys")
        source_id = _text(item["source_id"], "source_id", 256)
        if source_id in seen:
            raise ValueError("duplicate source_id")
        seen.add(source_id)
        source_url = _text(item["source_url"], "source_url", 2048)
        parsed = urlsplit(source_url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username is not None:
            raise ValueError("source_url must be HTTPS")
        result.append({
            "source_id": source_id, "source_url": source_url,
            "title": _text(item["title"], "title", 1000),
            "excerpt": _text(item["excerpt"], "excerpt", 8000),
        })
    return sorted(result, key=lambda item: item["source_id"])


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_synthesis_prompt(profile: object, evidence_items: object) -> str:
    canonical_profile = canonicalize_user_profile(profile)
    canonical_evidence = canonicalize_evidence_items(evidence_items)
    instructions = {
        "task": "Produce evidence-backed Build & Operate hypotheses, not generic brainstorming.",
        "reasoning_chain": ["observed condition", "economic mechanism", "value source / payer",
                            "why AI changes feasibility", "assumptions", "cheapest meaningful test",
                            "evidence required"],
        "constraints": [
            "Do not invent facts.",
            "Unknown quantities must remain unknown.",
            "Every hypothesis must cite one or more source IDs supplied in the evidence bundle.",
            "Do not recommend consequential external execution.",
            "Return only data matching the required response schema.",
        ],
        "response_shape": SYNTHESIS_RESPONSE_SCHEMA,
        "profile": canonical_profile,
        "evidence_items": canonical_evidence,
    }
    return _json(instructions)


def validate_synthesis_response(payload: object, evidence_items: object) -> list[dict[str, object]]:
    evidence = canonicalize_evidence_items(evidence_items)
    supplied_ids = {item["source_id"] for item in evidence}
    if not isinstance(payload, Mapping) or set(payload) != {"observations"}:
        raise ValueError("invalid synthesis response")
    observations = payload["observations"]
    if (not isinstance(observations, Sequence) or isinstance(observations, (str, bytes))
            or len(observations) > _MAX_OBSERVATIONS):
        raise ValueError("invalid observations")
    validated = []
    for item in observations:
        if not isinstance(item, Mapping) or set(item) != _OBSERVATION_KEYS:
            raise ValueError("invalid observation keys")
        normalized = {
            "title": _text(item["title"], "title", 1000),
            "observed_condition": _text(item["observed_condition"], "observed_condition", 2000),
            "economic_mechanism": _text(item["economic_mechanism"], "economic_mechanism", 2000),
            "value_source": _text(item["value_source"], "value_source", 2000),
            "why_ai_changes_feasibility": _text(item["why_ai_changes_feasibility"], "why_ai_changes_feasibility", 2000),
            "assumptions": _list(item["assumptions"], "assumptions", empty=True),
            "cheap_test": _text(item["cheap_test"], "cheap_test", 2000),
            "evidence_required": _list(item["evidence_required"], "evidence_required"),
            "source_ids": _list(item["source_ids"], "source_ids"),
            "mechanism_hint": _text(item["mechanism_hint"], "mechanism_hint", 2000, empty=True),
        }
        if len(set(normalized["source_ids"])) != len(normalized["source_ids"]):
            raise ValueError("duplicate provenance")
        if not set(normalized["source_ids"]).issubset(supplied_ids):
            raise ValueError("unknown provenance")
        identity_content = {key: (list(value) if isinstance(value, tuple) else value)
                            for key, value in normalized.items()}
        digest = hashlib.sha256(_json(identity_content).encode("utf-8")).hexdigest()
        validated.append({**normalized, "observation_id": "obs-" + digest,
                          "candidate_id": "synth-" + digest})
    return validated


def _failure(reason: str, evidence_source_ids: list[str] | None = None) -> dict[str, object]:
    return {"status": "FAIL_CLOSED", "reason_codes": [reason], "candidates": [],
            "evidence_source_ids": evidence_source_ids or []}


class _JsonSafeCandidate(dict[str, object]):
    @property
    def origin(self) -> object:
        """Retain read compatibility without storing an Enum in the mapping."""
        return type("OriginValue", (), {"value": self["origin"]})()


def _json_safe_candidate(candidate: object) -> dict[str, object]:
    """Serialize a validated candidate without leaking runtime-only value types."""
    result = _JsonSafeCandidate()
    for field in fields(candidate):
        value = getattr(candidate, field.name)
        if isinstance(value, Enum):
            value = value.value
        elif isinstance(value, Decimal):
            value = str(value)
        elif isinstance(value, tuple):
            value = list(value)
        result[field.name] = value
    return result


def execute_evidence_backed_synthesis(profile: object, evidence_items: object, executor: object) -> dict[str, object]:
    """Call an injected executor at most once and validate all output fail-closed."""
    try:
        evidence = canonicalize_evidence_items(evidence_items)
        prompt = build_synthesis_prompt(profile, evidence)
    except (TypeError, ValueError, ArithmeticError):
        return _failure("INVALID_SYNTHESIS_INPUT")
    source_ids = [item["source_id"] for item in evidence]
    if not callable(executor):
        return _failure("INVALID_SYNTHESIS_EXECUTOR", source_ids)
    try:
        payload = executor(prompt, SYNTHESIS_RESPONSE_SCHEMA)
    except Exception:
        return _failure("SYNTHESIS_EXECUTOR_FAILED", source_ids)
    try:
        validated = validate_synthesis_response(payload, evidence)
        candidates = []
        for item in validated:
            observation = SynthesisObservation(
                observation_id=item["observation_id"],
                observed_condition=item["observed_condition"],
                economic_mechanism=item["economic_mechanism"], value_source=item["value_source"],
                why_ai_changes_feasibility=item["why_ai_changes_feasibility"],
                assumptions=item["assumptions"], cheap_test=item["cheap_test"],
                evidence_required=item["evidence_required"], source_ids=item["source_ids"],
                mechanism_hint=item["mechanism_hint"],
            )
            candidate = build_synthesized_candidate(
                observation, candidate_id=item["candidate_id"], title=item["title"]
            )
            candidates.append(_json_safe_candidate(candidate))
    except (TypeError, ValueError, KeyError, ArithmeticError):
        return _failure("INVALID_SYNTHESIS_RESPONSE", source_ids)
    return {"status": "PASS", "reason_codes": [], "candidates": candidates,
            "evidence_source_ids": source_ids}
