"""Deterministic validation for the V3 personal opportunity profile."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
import re


_PROFILE_KEYS = {
    "goal", "country", "available_capital", "max_cash_spend",
    "human_hours_per_week", "ai_autonomy", "willingness",
    "skills_assets", "constraints",
}
_WILLINGNESS_KEYS = {
    "build_business", "work_with_customers", "sell", "publish_content",
    "invest_capital", "contests_juries", "financial_protocols",
}
_GOALS = {"income", "time", "both"}
_AUTONOMY = {"maximum", "mostly_ai", "anything_realistic"}
_DECIMAL = re.compile(r"[0-9]+(?:\.[0-9]+)?\Z", re.ASCII)
_MAX_TEXT = 256
_MAX_LIST_ITEMS = 64


def _text(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be text")
    value = value.strip()
    if not value or len(value) > _MAX_TEXT:
        raise ValueError(f"invalid {name}")
    return value


def _decimal(value: object, name: str) -> tuple[str, Decimal]:
    if not isinstance(value, str) or not _DECIMAL.fullmatch(value):
        raise ValueError(f"invalid {name}")
    number = Decimal(value)
    integer, separator, fraction = value.partition(".")
    integer = integer.lstrip("0") or "0"
    fraction = fraction.rstrip("0")
    return integer + (separator + fraction if fraction else ""), number


def _text_list(value: object, name: str) -> list[str]:
    if (not isinstance(value, Sequence) or isinstance(value, (str, bytes))
            or len(value) > _MAX_LIST_ITEMS):
        raise ValueError(f"invalid {name}")
    return [_text(item, name) for item in value]


def canonicalize_user_profile(profile: object) -> dict[str, object]:
    """Return an independent, JSON-safe canonical profile."""
    if not isinstance(profile, Mapping) or set(profile) != _PROFILE_KEYS:
        raise ValueError("invalid user profile keys")

    goal = profile["goal"]
    autonomy = profile["ai_autonomy"]
    if not isinstance(goal, str):
        raise ValueError("invalid goal")
    if not isinstance(autonomy, str):
        raise ValueError("invalid ai_autonomy")
    goal = goal.strip()
    autonomy = autonomy.strip()
    if goal not in _GOALS:
        raise ValueError("invalid goal")
    if autonomy not in _AUTONOMY:
        raise ValueError("invalid ai_autonomy")

    country = _text(profile["country"], "country")
    if len(country) > 128:
        raise ValueError("invalid country")

    willingness = profile["willingness"]
    if not isinstance(willingness, Mapping) or set(willingness) != _WILLINGNESS_KEYS:
        raise ValueError("invalid willingness keys")
    if any(type(willingness[key]) is not bool for key in _WILLINGNESS_KEYS):
        raise TypeError("willingness values must be booleans")

    capital, capital_value = _decimal(profile["available_capital"], "available_capital")
    spend, spend_value = _decimal(profile["max_cash_spend"], "max_cash_spend")
    hours, _ = _decimal(profile["human_hours_per_week"], "human_hours_per_week")
    if spend_value > capital_value:
        raise ValueError("max_cash_spend exceeds available_capital")

    return {
        "goal": goal,
        "country": country,
        "available_capital": capital,
        "max_cash_spend": spend,
        "human_hours_per_week": hours,
        "ai_autonomy": autonomy,
        "willingness": {key: willingness[key] for key in sorted(_WILLINGNESS_KEYS)},
        "skills_assets": _text_list(profile["skills_assets"], "skills_assets"),
        "constraints": _text_list(profile["constraints"], "constraints"),
    }


def to_decision_profile(profile: object) -> dict[str, str]:
    """Adapt a V3 profile to the frozen legacy decision-profile contract."""
    canonical = canonicalize_user_profile(profile)
    return {
        "operator_jurisdiction": canonical["country"],
        "available_capital": canonical["available_capital"],
        "max_cash_spend": canonical["max_cash_spend"],
        "max_human_hours": canonical["human_hours_per_week"],
        "objective": (
            f"Goal: {canonical['goal']}; AI autonomy: {canonical['ai_autonomy']}"
        ),
    }
