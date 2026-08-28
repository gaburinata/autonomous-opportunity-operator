from __future__ import annotations

from .models import State


_ALLOWED = {
    State.DISCOVERED: {State.VERIFIED, State.KILL, State.DECISION_REQUIRED},
    State.VERIFIED: {State.INVESTIGATING, State.KILL, State.DECISION_REQUIRED},
    State.INVESTIGATING: {State.TESTED, State.KILL, State.WATCH, State.DECISION_REQUIRED},
    State.TESTED: {State.PROMOTE, State.WATCH, State.KILL, State.DECISION_REQUIRED},
}


def transition(current: State, target: State) -> State:
    if target not in _ALLOWED.get(current, set()):
        raise ValueError(f"illegal transition: {current} -> {target}")
    return target

