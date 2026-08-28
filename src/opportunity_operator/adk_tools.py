"""Offline deterministic tools exposed to Google ADK.

The three upstream tools persist their returned value in invocation-scoped
``temp:`` state.  Final adjudication reads only that state; an LLM cannot pass
or reconstruct an upstream tool result.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
from typing import Any

from google.adk.tools import ToolContext


GATE_STATE_KEY = "temp:aoo_gate_result"
FAILURE_STATE_KEY = "temp:aoo_failure_result"
ECONOMICS_STATE_KEY = "temp:aoo_economics_result"

ACTION_APPROVAL_FIELDS = (
    "spending", "registration", "identity_or_legal_declaration",
    "wallet_transaction", "trading", "cloud_resource_creation",
    "external_submission",
)


def _digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _persist(tool_context: ToolContext, key: str, result: dict[str, Any]) -> dict[str, Any]:
    """Persist and return the same object, keeping one authoritative value."""
    tool_context.state[key] = result
    return result


def eligibility_capital_deadline_gate(
    eligible: bool,
    deadline_utc: str | None,
    evaluated_at_utc: str,
    tool_context: ToolContext,
    capital_required: str = "0",
    prohibited_action: bool = False,
    known_hard_safety_boundary: bool = False,
    requires_spending: bool = False,
    requires_registration: bool = False,
    requires_identity_or_legal_declaration: bool = False,
    requires_wallet_transaction: bool = False,
    requires_trading: bool = False,
    requires_cloud_resource_creation: bool = False,
    requires_external_submission: bool = False,
) -> dict[str, Any]:
    """Apply authoritative eligibility, deadline, capital, action, and safety gates."""
    try:
        now = datetime.fromisoformat(evaluated_at_utc.replace("Z", "+00:00"))
        if now.tzinfo is None:
            raise ValueError("evaluated_at_utc must be timezone-aware")
        deadline = None if deadline_utc is None else datetime.fromisoformat(deadline_utc.replace("Z", "+00:00"))
        if deadline is not None and deadline.tzinfo is None:
            raise ValueError("deadline_utc must be timezone-aware")
        capital = Decimal(capital_required)
        if not capital.is_finite() or capital < 0:
            raise ValueError("capital_required must be finite and non-negative")
    except (ValueError, TypeError, InvalidOperation) as exc:
        result = {"disposition": "KILL", "passed": False,
                  "reason_codes": ["MALFORMED_GATE_INPUT"], "error": type(exc).__name__}
        return _persist(tool_context, GATE_STATE_KEY, result)

    hard_reasons = []
    if not eligible:
        hard_reasons.append("INELIGIBLE")
    if deadline is not None and deadline <= now:
        hard_reasons.append("DEADLINE_EXPIRED")
    if prohibited_action:
        hard_reasons.append("PROHIBITED_ACTION")
    if known_hard_safety_boundary:
        hard_reasons.append("HARD_SAFETY_BOUNDARY")
    if hard_reasons:
        result = {"disposition": "KILL", "passed": False, "reason_codes": hard_reasons}
        return _persist(tool_context, GATE_STATE_KEY, result)

    approval_reasons = []
    if capital > 0:
        approval_reasons.append("CAPITAL_APPROVAL_REQUIRED")
    action_values = (
        requires_spending, requires_registration, requires_identity_or_legal_declaration,
        requires_wallet_transaction, requires_trading, requires_cloud_resource_creation,
        requires_external_submission,
    )
    approval_reasons.extend(
        f"{name.upper()}_APPROVAL_REQUIRED"
        for name, required in zip(ACTION_APPROVAL_FIELDS, action_values) if required
    )
    if approval_reasons:
        result = {"disposition": "DECISION_REQUIRED", "passed": False,
                  "reason_codes": approval_reasons}
        return _persist(tool_context, GATE_STATE_KEY, result)
    result = {"disposition": None, "passed": True, "reason_codes": ["HARD_GATES_PASSED"]}
    return _persist(tool_context, GATE_STATE_KEY, result)


def calculate_unit_economics(
    revenue_per_unit: str,
    variable_cost_per_unit: str,
    confidence: float | str | None,
    evidence_ids: list[str],
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Calculate unit margin, with confidence affecting positive margins only."""
    try:
        revenue = Decimal(revenue_per_unit)
        cost = Decimal(variable_cost_per_unit)
        if not revenue.is_finite() or not cost.is_finite():
            raise ValueError("economic values must be finite")
    except (InvalidOperation, ValueError, TypeError) as exc:
        result = {"disposition": "KILL", "reason_codes": ["MALFORMED_ECONOMIC_INPUT"],
                  "error": type(exc).__name__}
        return _persist(tool_context, ECONOMICS_STATE_KEY, result)

    margin = revenue - cost
    base = {"revenue_per_unit": str(revenue), "variable_cost_per_unit": str(cost),
            "margin_per_unit": str(margin), "confidence": confidence,
            "evidence_ids": list(evidence_ids)}
    if margin <= 0:
        result = {"disposition": "KILL", **base,
                  "reason_codes": ["NON_POSITIVE_UNIT_MARGIN"]}
        return _persist(tool_context, ECONOMICS_STATE_KEY, result)

    try:
        conf = Decimal(str(confidence))
        if not conf.is_finite():
            raise ValueError("confidence must be finite")
    except (InvalidOperation, ValueError, TypeError):
        result = {"disposition": "WATCH", **base,
                  "reason_codes": ["MALFORMED_OR_MISSING_CONFIDENCE"]}
        return _persist(tool_context, ECONOMICS_STATE_KEY, result)

    base["confidence"] = str(conf)
    if not evidence_ids:
        disposition, reasons = "WATCH", ["INSUFFICIENT_ECONOMIC_EVIDENCE"]
    elif conf < Decimal("0.70"):
        disposition, reasons = "WATCH", ["LOW_CONFIDENCE"]
    else:
        disposition, reasons = "PROMOTE", ["POSITIVE_UNIT_ECONOMICS"]
    result = {"disposition": disposition, **base, "reason_codes": reasons}
    return _persist(tool_context, ECONOMICS_STATE_KEY, result)


def failure_memory_similarity_check(
    candidate_signature: list[str],
    failure_records: list[dict[str, Any]],
    tool_context: ToolContext,
    warning_threshold: str = "0.50",
) -> dict[str, Any]:
    """Validate an external failure library and compute deterministic Jaccard matches."""
    required = {"memory_id", "hypothesis", "environment", "parameter_regime", "failure_class",
                "evidence", "similarity_signature", "reconsideration_conditions"}
    accepted, rejected = [], []
    candidate = {str(x).strip().lower() for x in candidate_signature if str(x).strip()}
    try:
        threshold = Decimal(warning_threshold)
        if not threshold.is_finite():
            raise ValueError
    except (InvalidOperation, ValueError, TypeError):
        threshold = Decimal("0.50")
    for index, record in enumerate(failure_records):
        if not isinstance(record, dict) or not required.issubset(record):
            rejected.append({"index": index, "reason_code": "MALFORMED_FAILURE_RECORD"})
            continue
        evidence = record["evidence"]
        signature = record["similarity_signature"]
        if (not isinstance(evidence, list) or not evidence or
                not all(isinstance(item, dict) and item.get("source_id") and item.get("digest") for item in evidence) or
                not isinstance(signature, list) or not signature):
            rejected.append({"index": index, "reason_code": "MALFORMED_FAILURE_EVIDENCE"})
            continue
        prior = {str(x).strip().lower() for x in signature if str(x).strip()}
        union = candidate | prior
        score = Decimal(len(candidate & prior)) / Decimal(len(union)) if union else Decimal("0")
        accepted.append({"memory_id": str(record["memory_id"]), "score": str(score),
                         "warning": score >= threshold, "overlapping_terms": sorted(candidate & prior)})
    accepted.sort(key=lambda item: (-Decimal(item["score"]), item["memory_id"]))
    result = {"matches": accepted, "rejected_records": rejected,
              "reason_codes": ["KNOWN_FAILURE_SIMILARITY"] if any(x["warning"] for x in accepted) else []}
    return _persist(tool_context, FAILURE_STATE_KEY, result)


def _reason_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item for item in value)


def _authoritative_state_error(reason_code: str, source_identity: str,
                               evidence: list[str], sequence: int) -> dict[str, Any]:
    return _final_event("KILL", [reason_code], source_identity, evidence, sequence)


def _final_event(disposition: str, reasons: list[str], source_identity: str,
                 evidence: list[str], sequence: int) -> dict[str, Any]:
    event = {"source_identity": source_identity, "evidence": list(evidence), "sequence": sequence,
             "recorded_at": "SEQUENCE_CONTROLLED", "disposition": disposition,
             "reason_codes": reasons}
    event["stable_digest"] = _digest(event)
    return event


def final_evidence_safety_adjudication(
    source_identity: str,
    evidence: list[str],
    sequence: int,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Adjudicate only from authoritative upstream values in ToolContext state."""
    state = tool_context.state
    for key, missing_reason in (
        (GATE_STATE_KEY, "MISSING_AUTHORITATIVE_GATE_RESULT"),
        (ECONOMICS_STATE_KEY, "MISSING_AUTHORITATIVE_ECONOMICS_RESULT"),
        (FAILURE_STATE_KEY, "MISSING_AUTHORITATIVE_FAILURE_RESULT"),
    ):
        if key not in state:
            return _authoritative_state_error(missing_reason, source_identity, evidence, sequence)

    gate = state[GATE_STATE_KEY]
    economics = state[ECONOMICS_STATE_KEY]
    failure = state[FAILURE_STATE_KEY]
    valid_gate = (isinstance(gate, dict) and gate.get("disposition") in {None, "KILL", "DECISION_REQUIRED"}
                  and isinstance(gate.get("passed"), bool) and _reason_list(gate.get("reason_codes"))
                  and bool(gate.get("reason_codes")))
    valid_economics = (isinstance(economics, dict)
                       and economics.get("disposition") in {"KILL", "WATCH", "PROMOTE"}
                       and _reason_list(economics.get("reason_codes"))
                       and bool(economics.get("reason_codes")))
    valid_failure = (isinstance(failure, dict) and isinstance(failure.get("matches"), list)
                     and isinstance(failure.get("rejected_records"), list)
                     and _reason_list(failure.get("reason_codes")))
    if not (valid_gate and valid_economics and valid_failure):
        return _authoritative_state_error("INVALID_AUTHORITATIVE_STATE",
                                          source_identity, evidence, sequence)

    if gate["disposition"] in {"KILL", "DECISION_REQUIRED"}:
        disposition, reasons = gate["disposition"], list(gate["reason_codes"])
    elif economics["disposition"] == "KILL":
        disposition, reasons = "KILL", list(economics["reason_codes"])
    elif failure["reason_codes"]:
        disposition, reasons = "WATCH", list(failure["reason_codes"])
    else:
        disposition, reasons = economics["disposition"], list(economics["reason_codes"])
    return _final_event(disposition, reasons, source_identity, evidence, sequence)


def authoritative_failure_memory_similarity_check(
    candidate_signature: list[str],
    tool_context: ToolContext,
    warning_threshold: str = "0.50",
) -> dict[str, Any]:
    """
    Compare a candidate against AOO's authoritative durable
    failure-memory library.

    Historical failure records are loaded internally and
    cannot be supplied or replaced by the model.
    """
    from .failure_memory_library import (
        load_failure_records,
    )

    records = list(
        load_failure_records()
    )

    return failure_memory_similarity_check(
        candidate_signature,
        records,
        tool_context,
        warning_threshold,
    )


# Keep the externally visible tool name stable.
authoritative_failure_memory_similarity_check.__name__ = (
    "failure_memory_similarity_check"
)

authoritative_failure_memory_similarity_check.__qualname__ = (
    "failure_memory_similarity_check"
)
