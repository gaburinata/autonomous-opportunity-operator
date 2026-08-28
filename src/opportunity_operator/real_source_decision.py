"""Bridge captured primary-source evidence into the decision workflow."""

from collections.abc import Mapping
import copy
import hashlib
import json
import re

from .primary_source_intake import build_discovered_event, ingest_primary_source
from .workflow_coordinator import coordinate_opportunity_event


_PROFILE_KEYS = {
    "operator_jurisdiction",
    "available_capital",
    "max_cash_spend",
    "max_human_hours",
    "objective",
}
_NUMERIC_KEYS = ("available_capital", "max_cash_spend", "max_human_hours")
_DECIMAL = re.compile(r"[0-9]+(?:\.[0-9]+)?\Z", re.ASCII)


def _canonical_decimal(value):
    if not isinstance(value, str) or not _DECIMAL.fullmatch(value):
        raise ValueError("invalid decimal")
    integer, separator, fraction = value.partition(".")
    integer = integer.lstrip("0") or "0"
    fraction = fraction.rstrip("0")
    return integer + (separator + fraction if fraction else "")


def canonicalize_decision_profile(profile):
    """Validate and return an independent, deterministic decision profile."""
    if not isinstance(profile, Mapping) or set(profile) != _PROFILE_KEYS:
        raise ValueError("invalid decision profile keys")
    if any(not isinstance(profile[key], str) for key in _PROFILE_KEYS):
        raise ValueError("decision profile values must be strings")

    jurisdiction = profile["operator_jurisdiction"].strip()
    objective = profile["objective"].strip()
    if not jurisdiction or len(jurisdiction) > 128:
        raise ValueError("invalid operator jurisdiction")
    if not objective or len(objective) > 500:
        raise ValueError("invalid objective")

    result = {
        "operator_jurisdiction": jurisdiction,
        "available_capital": _canonical_decimal(profile["available_capital"]),
        "max_cash_spend": _canonical_decimal(profile["max_cash_spend"]),
        "max_human_hours": _canonical_decimal(profile["max_human_hours"]),
        "objective": objective,
    }
    return result


def build_decision_event(source_event, decision_profile):
    """Create a profile-sensitive event without changing its source event."""
    canonical_profile = canonicalize_decision_profile(decision_profile)
    if not isinstance(source_event, Mapping):
        raise ValueError("invalid source event")
    event_id = source_event.get("event_id")
    opportunity_id = source_event.get("opportunity_id")
    payload = source_event.get("payload")
    if (
        not isinstance(event_id, str) or not event_id
        or source_event.get("event_type") != "opportunity.discovered"
        or not isinstance(opportunity_id, str) or not opportunity_id
        or not isinstance(payload, Mapping)
    ):
        raise ValueError("invalid source event")

    profile_json = json.dumps(
        canonical_profile,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(
        (event_id + "\x00" + profile_json).encode("utf-8")
    ).hexdigest()
    decision_payload = copy.deepcopy(dict(payload))
    decision_payload["source_event_id"] = event_id
    decision_payload["decision_profile"] = copy.deepcopy(canonical_profile)
    return {
        "event_id": "decision-" + digest,
        "event_type": "opportunity.discovered",
        "opportunity_id": opportunity_id,
        "payload": decision_payload,
    }


def _failure(reason_codes):
    return {
        "scenario": "real-primary-source-decision",
        "status": "FAIL_CLOSED",
        "reason_codes": copy.deepcopy(list(reason_codes)),
    }


def execute_primary_source_decision(
    source_url,
    opportunity_id,
    decision_profile,
    *,
    store_factory,
    executor_factory,
    ingestor=ingest_primary_source,
):
    """Capture, identify, and coordinate one primary-source decision."""
    try:
        canonical_profile = canonicalize_decision_profile(decision_profile)
    except (TypeError, ValueError):
        return _failure(["INVALID_DECISION_PROFILE"])

    try:
        document = ingestor(source_url)
    except Exception:
        return _failure(["SOURCE_FETCH_FAILED"])
    if not isinstance(document, Mapping) or document.get("status") != "PASS":
        reasons = document.get("reason_codes") if isinstance(document, Mapping) else None
        if not isinstance(reasons, list) or not reasons or not all(
            isinstance(reason, str) and reason for reason in reasons
        ):
            reasons = ["SOURCE_FETCH_FAILED"]
        return _failure(reasons)

    try:
        source_event = build_discovered_event(document, opportunity_id)
        decision_event = build_decision_event(source_event, canonical_profile)
    except (KeyError, TypeError, ValueError):
        return _failure(["INVALID_INTAKE_DOCUMENT"])

    try:
        store = store_factory()
        executor = executor_factory()
    except Exception:
        return _failure(["WORKFLOW_CONSTRUCTION_FAILED"])
    outcome = coordinate_opportunity_event(decision_event, store, executor)
    runtime = getattr(executor, "runtime_evidence", None)
    try:
        runtime_evidence = runtime() if callable(runtime) else {}
    except Exception:
        runtime_evidence = {}

    payload = source_event["payload"]
    source_evidence = {
        "source_url": payload["source_url"],
        "final_url": payload["final_url"],
        "content_type": payload["content_type"],
        "byte_length": payload["byte_length"],
        "source_sha256": payload["source_sha256"],
        "text_length": payload["text_length"],
        "text_sha256": payload["text_sha256"],
        "source_event_id": source_event["event_id"],
    }
    return {
        "scenario": "real-primary-source-decision",
        "status": "PASS",
        "reason_codes": ["DECISION_WORKFLOW_COMPLETED"],
        "decision_event_id": decision_event["event_id"],
        "source_evidence": source_evidence,
        "decision_profile": copy.deepcopy(canonical_profile),
        "outcome": outcome,
        "runtime_evidence": runtime_evidence,
    }
