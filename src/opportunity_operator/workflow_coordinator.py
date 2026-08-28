"""Deterministic coordination of routed opportunity events."""

from collections.abc import Mapping
import copy

from .event_router import route_opportunity_event


_STAGES = (
    "PRIMARY_SOURCE_VERIFICATION",
    "DETERMINISTIC_HARD_GATE",
    "INVESTIGATION",
    "FAILURE_MEMORY",
    "ECONOMIC_EVIDENCE",
    "FINAL_ADJUDICATION",
)
_TERMINAL_DISPOSITIONS = {
    "PROMOTE",
    "WATCH",
    "KILL",
    "DECISION_REQUIRED",
}
_ROUTER_DISPOSITIONS = _TERMINAL_DISPOSITIONS | {
    "PROCESS",
    "NOOP",
    "FAIL_CLOSED",
}
_OUTCOME_KEYS = {
    "event_id",
    "opportunity_id",
    "idempotency_key",
    "disposition",
    "reason_codes",
    "stage_trace",
    "replayed",
}


def _valid_reasons(value):
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item) for item in value)
    )


def _base_outcome(route, disposition, reasons, trace=()):
    return {
        "event_id": route.get("event_id", ""),
        "opportunity_id": route.get("opportunity_id", ""),
        "idempotency_key": route.get("idempotency_key", ""),
        "disposition": disposition,
        "reason_codes": copy.deepcopy(list(reasons)),
        "stage_trace": copy.deepcopy(list(trace)),
        "replayed": False,
    }


def _invalid_router_outcome(route=None):
    safe_route = route if isinstance(route, Mapping) else {}
    return _base_outcome(safe_route, "KILL", ["INVALID_ROUTER_RESULT"])


def _valid_route(route):
    required = {
        "event_id",
        "opportunity_id",
        "idempotency_key",
        "disposition",
        "next_stage",
        "reason_codes",
    }
    if not isinstance(route, Mapping) or set(route) != required:
        return False
    if not all(
        isinstance(route[name], str)
        for name in ("idempotency_key", "disposition", "next_stage")
    ) or not _valid_reasons(route["reason_codes"]):
        return False
    disposition = route["disposition"]
    if disposition not in _ROUTER_DISPOSITIONS:
        return False
    if disposition == "FAIL_CLOSED":
        return route["idempotency_key"] == "" and route["next_stage"] == "NONE"
    if not all(isinstance(route[name], str) for name in ("event_id", "opportunity_id")):
        return False
    if not all(route[name] for name in ("event_id", "opportunity_id", "idempotency_key")):
        return False
    if disposition == "PROCESS":
        return route["next_stage"] in _STAGES
    if disposition == "DECISION_REQUIRED":
        return route["next_stage"] == "HUMAN_GATE"
    return route["next_stage"] == "NONE"


def _valid_stage_result(result):
    if not isinstance(result, Mapping) or result.get("status") not in {"CONTINUE", "TERMINAL"}:
        return False
    if not _valid_reasons(result.get("reason_codes")):
        return False
    if result["status"] == "CONTINUE":
        return set(result) == {"status", "reason_codes"}
    return (
        set(result) == {"status", "disposition", "reason_codes"}
        and result.get("disposition") in _TERMINAL_DISPOSITIONS
    )


def _valid_completed_outcome(value, key):
    if not isinstance(value, Mapping) or set(value) != _OUTCOME_KEYS:
        return False
    return (
        value.get("idempotency_key") == key
        and value.get("disposition") in (_TERMINAL_DISPOSITIONS | {"NOOP"})
        and _valid_reasons(value.get("reason_codes"))
        and isinstance(value.get("stage_trace"), list)
        and isinstance(value.get("replayed"), bool)
        and isinstance(value.get("event_id"), str)
        and isinstance(value.get("opportunity_id"), str)
    )


def _as_replay(value):
    replay = copy.deepcopy(dict(value))
    replay["replayed"] = True
    return replay


def _complete(store, key, outcome):
    """Persist an outcome, replacing it with a stable closed result on failure."""
    try:
        store.complete(key, copy.deepcopy(outcome))
        return outcome
    except Exception:
        return _base_outcome(outcome, "KILL", ["WORKFLOW_STORE_FAILED"], outcome["stage_trace"])


def coordinate_opportunity_event(event, store, executor, *, max_transitions=6):
    """Route, replay, and execute one opportunity event to a terminal outcome."""
    try:
        route = route_opportunity_event(copy.deepcopy(event))
    except Exception:
        return _invalid_router_outcome()

    if not _valid_route(route):
        return _invalid_router_outcome(route)
    route = copy.deepcopy(dict(route))
    if route["disposition"] == "FAIL_CLOSED":
        return _base_outcome(route, "FAIL_CLOSED", route["reason_codes"])

    key = route["idempotency_key"]
    try:
        completed = store.load(key)
    except Exception:
        return _base_outcome(route, "KILL", ["WORKFLOW_STORE_FAILED"])
    if completed is not None:
        if _valid_completed_outcome(completed, key):
            return _as_replay(completed)
        return _base_outcome(route, "KILL", ["WORKFLOW_STORE_FAILED"])

    try:
        claimed = store.claim(key)
    except Exception:
        return _base_outcome(route, "KILL", ["WORKFLOW_STORE_FAILED"])
    if not claimed:
        try:
            completed = store.load(key)
        except Exception:
            return _base_outcome(route, "KILL", ["WORKFLOW_STORE_FAILED"])
        if completed is not None and _valid_completed_outcome(completed, key):
            return _as_replay(completed)
        return _base_outcome(route, "KILL", ["REPLAY_IN_PROGRESS"])

    if route["disposition"] != "PROCESS":
        outcome = _base_outcome(route, route["disposition"], route["reason_codes"])
        return _complete(store, key, outcome)

    trace = []
    prior_results = []
    start = _STAGES.index(route["next_stage"])
    for stage in _STAGES[start:]:
        if (
            isinstance(max_transitions, bool)
            or not isinstance(max_transitions, int)
            or max_transitions <= 0
            or len(trace) >= max_transitions
        ):
            outcome = _base_outcome(route, "KILL", ["MAX_TRANSITIONS_EXCEEDED"], trace)
            return _complete(store, key, outcome)

        try:
            result = executor.execute(
                stage,
                copy.deepcopy(event),
                tuple(copy.deepcopy(prior_results)),
            )
        except Exception:
            trace.append({
                "sequence": len(trace) + 1,
                "stage": stage,
                "status": "FAILED",
                "disposition": "KILL",
                "reason_codes": ["WORKFLOW_EXECUTION_FAILED"],
            })
            outcome = _base_outcome(route, "KILL", ["WORKFLOW_EXECUTION_FAILED"], trace)
            return _complete(store, key, outcome)

        if not _valid_stage_result(result):
            trace.append({
                "sequence": len(trace) + 1,
                "stage": stage,
                "status": "FAILED",
                "disposition": "KILL",
                "reason_codes": ["INVALID_STAGE_RESULT"],
            })
            outcome = _base_outcome(route, "KILL", ["INVALID_STAGE_RESULT"], trace)
            return _complete(store, key, outcome)

        result = copy.deepcopy(dict(result))
        disposition = result.get("disposition")
        trace.append({
            "sequence": len(trace) + 1,
            "stage": stage,
            "status": result["status"],
            "disposition": disposition,
            "reason_codes": copy.deepcopy(result["reason_codes"]),
        })
        prior_results.append(result)
        if result["status"] == "TERMINAL":
            outcome = _base_outcome(route, disposition, result["reason_codes"], trace)
            return _complete(store, key, outcome)
        if stage == "FINAL_ADJUDICATION":
            trace[-1] = {
                "sequence": trace[-1]["sequence"],
                "stage": stage,
                "status": "FAILED",
                "disposition": "KILL",
                "reason_codes": ["INVALID_STAGE_RESULT"],
            }
            outcome = _base_outcome(route, "KILL", ["INVALID_STAGE_RESULT"], trace)
            return _complete(store, key, outcome)

    outcome = _base_outcome(route, "KILL", ["INVALID_STAGE_RESULT"], trace)
    return _complete(store, key, outcome)
