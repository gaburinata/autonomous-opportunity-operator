"""Deterministic routing for external opportunity events."""

from collections.abc import Mapping
import hashlib


_HUMAN_ACTION_CLASSES = {
    "SPEND_MONEY",
    "IDENTITY_OR_LEGAL",
    "REGISTER_ACCOUNT",
    "WALLET_TRANSACTION",
    "REAL_MONEY_TRADING",
    "CREATE_PAID_CLOUD_RESOURCE",
    "EXTERNAL_SUBMISSION",
}

_EVENT_ROUTES = {
    "opportunity.discovered": (
        "PROCESS",
        "PRIMARY_SOURCE_VERIFICATION",
        "NEW_OPPORTUNITY",
    ),
    "opportunity.source_changed": (
        "PROCESS",
        "PRIMARY_SOURCE_VERIFICATION",
        "SOURCE_CHANGED",
    ),
    "opportunity.deadline_changed": (
        "PROCESS",
        "DETERMINISTIC_HARD_GATE",
        "DEADLINE_CHANGED",
    ),
    "opportunity.economics_changed": (
        "PROCESS",
        "ECONOMIC_EVIDENCE",
        "ECONOMICS_CHANGED",
    ),
    "opportunity.failure_memory_changed": (
        "PROCESS",
        "FAILURE_MEMORY",
        "FAILURE_MEMORY_CHANGED",
    ),
}


def route_opportunity_event(event, seen_event_ids=()):
    """Validate and deterministically route one opportunity event."""
    if isinstance(event, Mapping):
        event_id = event.get("event_id", "")
        event_type = event.get("event_type", "")
        opportunity_id = event.get("opportunity_id", "")
    else:
        event_id = ""
        event_type = ""
        opportunity_id = ""

    required_values = (event_id, event_type, opportunity_id)
    if not all(isinstance(value, str) and value for value in required_values):
        return {
            "event_id": event_id,
            "opportunity_id": opportunity_id,
            "idempotency_key": "",
            "disposition": "FAIL_CLOSED",
            "next_stage": "NONE",
            "reason_codes": ["INVALID_EVENT"],
        }

    idempotency_key = hashlib.sha256(
        (opportunity_id + "\x00" + event_id).encode("utf-8")
    ).hexdigest()

    if event_id in seen_event_ids:
        route = ("NOOP", "NONE", "DUPLICATE_EVENT")
    elif event.get("action_class") in _HUMAN_ACTION_CLASSES:
        route = (
            "DECISION_REQUIRED",
            "HUMAN_GATE",
            "HUMAN_AUTHORIZATION_REQUIRED",
        )
    else:
        route = _EVENT_ROUTES.get(
            event_type,
            ("WATCH", "NONE", "UNSUPPORTED_EVENT_TYPE"),
        )

    disposition, next_stage, reason_code = route
    return {
        "event_id": event_id,
        "opportunity_id": opportunity_id,
        "idempotency_key": idempotency_key,
        "disposition": disposition,
        "next_stage": next_stage,
        "reason_codes": [reason_code],
    }
