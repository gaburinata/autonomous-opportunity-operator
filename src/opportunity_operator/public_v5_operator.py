"""Public-safe deterministic V5 opportunity personalization.

This layer deliberately does not call Gemini, the network, Firestore,
wallets, exchanges, submission systems, or any consequential service.

It applies a person's economic/resource profile to the stored opportunity
snapshot without inventing missing facts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
import json
import re
from typing import Any


_PROFILE_KEYS = {
    "profile_version",
    "goal",
    "residence_country",
    "citizenships",
    "currency",
    "available_money",
    "max_cash_spend_or_risk",
    "human_hours_per_week",
    "exclusions",
    "skills_assets",
}

_GOALS = {
    "income",
    "time",
    "both",
}

_ALLOWED_EXCLUSIONS = {
    "competitions",
    "grants",
    "financial_trading",
    "customer_work",
    "selling_content",
}

_DECIMAL = re.compile(
    r"[0-9]+(?:\.[0-9]+)?\Z",
    re.ASCII,
)

_CURRENCY = re.compile(
    r"[A-Z0-9]{3,8}\Z",
    re.ASCII,
)

_MAX_TEXT = 160
_MAX_LIST = 32

_CONTEST_TERMS = (
    "hackathon",
    "competition",
    "challenge",
    "contest",
    "prize",
)

_GRANT_TERMS = (
    "grant",
    "funding call",
    "funding programme",
    "funding program",
    "fellowship",
)

_FINANCIAL_TERMS = (
    "trading",
    "arbitrage",
    "market making",
    "market-making",
    "defi",
    "financial protocol",
    "prediction market",
    "perpetual",
    "futures",
    "yield strategy",
    "investment",
)

_CUSTOMER_TERMS = (
    "client service",
    "customer service",
    "consulting",
    "freelance",
    "agency",
    "client work",
)

_SELLING_CONTENT_TERMS = (
    "sales",
    "selling",
    "cold outreach",
    "content creator",
    "influencer",
    "newsletter",
)

_JOB_TERMS = (
    "job opening",
    "job vacancy",
    "employment vacancy",
    "full-time role",
    "part-time role",
    "salary position",
    "career vacancy",
)

_TIME_SAVING_TERMS = (
    "workflow automation",
    "business automation",
    "productivity automation",
    "process automation",
    "save time",
    "time saving",
    "time-saving",
)

_TEXT_FIELDS = (
    "title",
    "organizer",
    "economic_mechanism",
    "asset_fit",
    "discovered_via",
    "type",
    "category",
    "description",
)


def _text(
    value: object,
    name: str,
) -> str:

    if not isinstance(value, str):
        raise TypeError(
            f"{name} must be text"
        )

    value = value.strip()

    if (
        not value
        or len(value) > _MAX_TEXT
    ):
        raise ValueError(
            f"invalid {name}"
        )

    return value


def _optional_text(
    value: object,
) -> str | None:

    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    return value[:500]


def _decimal(
    value: object,
    name: str,
) -> tuple[str, Decimal]:

    if (
        not isinstance(value, str)
        or not _DECIMAL.fullmatch(value)
    ):
        raise ValueError(
            f"invalid {name}"
        )

    number = Decimal(value)

    integer, separator, fraction = (
        value.partition(".")
    )

    integer = (
        integer.lstrip("0")
        or "0"
    )

    fraction = fraction.rstrip("0")

    canonical = (
        integer
        + (
            separator + fraction
            if fraction
            else ""
        )
    )

    return canonical, number


def _safe_decimal(
    value: object,
) -> Decimal | None:

    if (
        value is None
        or isinstance(value, bool)
    ):
        return None

    try:
        result = Decimal(
            str(value)
        )
    except (
        InvalidOperation,
        ValueError,
    ):
        return None

    if (
        not result.is_finite()
        or result < 0
    ):
        return None

    return result


def _text_list(
    value: object,
    name: str,
) -> list[str]:

    if (
        not isinstance(
            value,
            Sequence,
        )
        or isinstance(
            value,
            (str, bytes),
        )
        or len(value) > _MAX_LIST
    ):
        raise ValueError(
            f"invalid {name}"
        )

    result: list[str] = []

    for item in value:
        text = _text(
            item,
            name,
        )

        if text not in result:
            result.append(text)

    return result


def canonicalize_v5_profile(
    profile: object,
) -> dict[str, object]:

    if (
        not isinstance(
            profile,
            Mapping,
        )
        or set(profile)
        != _PROFILE_KEYS
    ):
        raise ValueError(
            "invalid V5 profile keys"
        )

    if profile.get(
        "profile_version"
    ) != "5":
        raise ValueError(
            "invalid profile version"
        )

    goal = profile["goal"]

    if not isinstance(
        goal,
        str,
    ):
        raise ValueError(
            "invalid goal"
        )

    goal = goal.strip()

    if goal not in _GOALS:
        raise ValueError(
            "invalid goal"
        )

    residence = _text(
        profile[
            "residence_country"
        ],
        "residence_country",
    )

    citizenships = _text_list(
        profile["citizenships"],
        "citizenships",
    )

    if not citizenships:
        raise ValueError(
            "at least one citizenship is required"
        )

    currency = _text(
        profile["currency"],
        "currency",
    ).upper()

    if not _CURRENCY.fullmatch(
        currency
    ):
        raise ValueError(
            "invalid currency"
        )

    available, available_value = (
        _decimal(
            profile[
                "available_money"
            ],
            "available_money",
        )
    )

    spend, spend_value = (
        _decimal(
            profile[
                "max_cash_spend_or_risk"
            ],
            "max_cash_spend_or_risk",
        )
    )

    hours, _ = _decimal(
        profile[
            "human_hours_per_week"
        ],
        "human_hours_per_week",
    )

    if spend_value > available_value:
        raise ValueError(
            "max cash spend/risk exceeds available money"
        )

    exclusions_raw = _text_list(
        profile["exclusions"],
        "exclusions",
    )

    exclusions = set(
        exclusions_raw
    )

    if not exclusions.issubset(
        _ALLOWED_EXCLUSIONS
    ):
        raise ValueError(
            "invalid exclusions"
        )

    skills = _text_list(
        profile["skills_assets"],
        "skills_assets",
    )

    return {
        "profile_version": "5",
        "goal": goal,
        "residence_country":
            residence,
        "citizenships":
            citizenships,
        "currency":
            currency,
        "available_money":
            available,
        "max_cash_spend_or_risk":
            spend,
        "human_hours_per_week":
            hours,
        "exclusions":
            sorted(exclusions),
        "skills_assets":
            skills,
    }


def _repo_root() -> Path:
    return (
        Path(__file__)
        .resolve()
        .parents[2]
    )


def _load_snapshot_items() -> list[dict[str, Any]]:

    path = (
        _repo_root()
        / "data"
        / "discovery"
        / "latest.json"
    )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        data,
        Mapping,
    ):
        return []

    items = data.get(
        "items",
        [],
    )

    if not isinstance(
        items,
        list,
    ):
        return []

    return [
        dict(item)
        for item in items
        if isinstance(
            item,
            Mapping,
        )
    ]


def _classification_text(
    item: Mapping[str, object],
) -> str:

    values = []

    for field in _TEXT_FIELDS:

        value = item.get(field)

        if isinstance(
            value,
            str,
        ):
            values.append(value)

    return " ".join(
        values
    ).casefold()


def _contains_any(
    text: str,
    terms: tuple[str, ...],
) -> bool:

    return any(
        term in text
        for term in terms
    )


def _classify(
    item: Mapping[str, object],
) -> dict[str, bool]:

    text = _classification_text(
        item
    )

    competition = _contains_any(
        text,
        _CONTEST_TERMS,
    )

    grant = (
        not competition
        and _contains_any(
            text,
            _GRANT_TERMS,
        )
    )

    financial = _contains_any(
        text,
        _FINANCIAL_TERMS,
    )

    customer = _contains_any(
        text,
        _CUSTOMER_TERMS,
    )

    selling = _contains_any(
        text,
        _SELLING_CONTENT_TERMS,
    )

    traditional_job = _contains_any(
        text,
        _JOB_TERMS,
    )

    time_saving = (
        not competition
        and not grant
        and _contains_any(
            text,
            _TIME_SAVING_TERMS,
        )
    )

    return {
        "competition":
            competition,
        "grant":
            grant,
        "financial":
            financial,
        "customer":
            customer,
        "selling":
            selling,
        "traditional_job":
            traditional_job,
        "time_saving":
            time_saving,
    }


def _category(
    flags: Mapping[str, bool],
) -> str:

    if flags["competition"]:
        return "Competition"

    if flags["grant"]:
        return "Grant / funding"

    if flags["financial"]:
        return "Financial / trading"

    if flags["time_saving"]:
        return "Automation"

    return "Opportunity"


def _source_url(
    item: Mapping[str, object],
) -> str | None:

    value = item.get(
        "canonical_source_url"
    )

    if (
        isinstance(value, str)
        and value.startswith(
            "https://"
        )
    ):
        return value

    return None


def _confidence(
    item: Mapping[str, object],
) -> float:

    value = item.get(
        "confidence"
    )

    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
    ):
        return max(
            0.0,
            min(
                1.0,
                float(value),
            ),
        )

    return 0.0


def _capital_currency(
    item: Mapping[str, object],
) -> str | None:

    for key in (
        "capital_currency",
        "required_capital_currency",
    ):
        value = item.get(key)

        if (
            isinstance(value, str)
            and _CURRENCY.fullmatch(
                value.strip().upper()
            )
        ):
            return value.strip().upper()

    return None


def _money_needed(
    item: Mapping[str, object],
) -> tuple[str, bool]:

    amount = _safe_decimal(
        item.get(
            "capital_required"
        )
    )

    currency = _capital_currency(
        item
    )

    if (
        amount is None
        or currency is None
    ):
        return (
            "Not verified yet",
            False,
        )

    return (
        f"{amount.normalize()} {currency}",
        True,
    )


def _human_time(
    item: Mapping[str, object],
) -> tuple[str, bool]:

    hours = _safe_decimal(
        item.get(
            "estimated_effort_hours"
        )
    )

    if hours is None:
        return (
            "Not verified yet",
            False,
        )

    return (
        f"{hours.normalize()} hours estimated",
        True,
    )


def _ai_share(
    item: Mapping[str, object],
) -> tuple[str, bool]:

    value = item.get(
        "ai_executability"
    )

    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
    ):
        number = float(value)

        if 0 <= number <= 1:
            number *= 100

        if 0 <= number <= 100:
            return (
                f"{round(number)}%",
                True,
            )

    if isinstance(value, str):
        value = value.strip()

        if value:
            return (
                value,
                True,
            )

    return (
        "Not verified yet",
        False,
    )


def _upside(
    item: Mapping[str, object],
) -> tuple[str, bool]:

    for key in (
        "estimated_upside",
        "prize_amount",
        "funding_amount",
    ):
        amount = _safe_decimal(
            item.get(key)
        )

        if amount is None:
            continue

        currency = None

        for currency_key in (
            "upside_currency",
            "prize_currency",
            "funding_currency",
            "currency",
        ):
            raw = item.get(
                currency_key
            )

            if isinstance(
                raw,
                str,
            ):
                raw = raw.strip().upper()

                if _CURRENCY.fullmatch(
                    raw
                ):
                    currency = raw
                    break

        if currency:
            return (
                f"{amount.normalize()} {currency}",
                True,
            )

    return (
        "Not verified yet",
        False,
    )


def _eligibility_for_person(
    item: Mapping[str, object],
) -> str:

    raw = str(
        item.get(
            "eligibility",
            "UNKNOWN",
        )
    ).strip().upper()

    if raw == "INELIGIBLE":
        return "Ineligible"

    # The stored discovery snapshot was not created from this V5
    # residence + citizenship profile, so even a generic ELIGIBLE
    # flag must not be promoted into a person-specific claim.
    return (
        "Needs residence and citizenship verification"
    )


def _why(
    category: str,
) -> str:

    base = (
        "It survived the hard filters AOO can verify from the "
        "current evidence."
    )

    if category == "Competition":
        return (
            base
            + " You did not exclude competitions."
        )

    if category == "Grant / funding":
        return (
            base
            + " You did not exclude grants or funding."
        )

    if category == "Financial / trading":
        return (
            base
            + " You allowed financial and trading opportunities."
        )

    return base


def build_public_v5_view(
    profile: object,
    *,
    items: Sequence[
        Mapping[str, object]
    ] | None = None,
) -> dict[str, object]:

    canonical = (
        canonicalize_v5_profile(
            profile
        )
    )

    if items is None:
        items = _load_snapshot_items()

    exclusions = set(
        canonical["exclusions"]
    )

    goal = str(
        canonical["goal"]
    )

    user_currency = str(
        canonical["currency"]
    )

    max_spend = Decimal(
        str(
            canonical[
                "max_cash_spend_or_risk"
            ]
        )
    )

    counts = {
        "traditional_jobs":
            0,
        "goal_mismatch":
            0,
        "competitions":
            0,
        "grants":
            0,
        "financial_trading":
            0,
        "customer_work":
            0,
        "selling_content":
            0,
        "known_ineligible":
            0,
        "same_currency_over_budget":
            0,
    }

    ranked: list[
        tuple[
            float,
            int,
            dict[str, object],
        ]
    ] = []

    for index, raw in enumerate(
        items
    ):

        if not isinstance(
            raw,
            Mapping,
        ):
            continue

        item = dict(raw)

        title = (
            _optional_text(
                item.get("title")
            )
            or "Untitled opportunity"
        )

        flags = _classify(
            item
        )

        if flags[
            "traditional_job"
        ]:
            counts[
                "traditional_jobs"
            ] += 1
            continue

        if (
            goal == "time"
            and not flags[
                "time_saving"
            ]
        ):
            counts[
                "goal_mismatch"
            ] += 1
            continue

        if (
            flags["competition"]
            and "competitions"
            in exclusions
        ):
            counts[
                "competitions"
            ] += 1
            continue

        if (
            flags["grant"]
            and "grants"
            in exclusions
        ):
            counts[
                "grants"
            ] += 1
            continue

        if (
            flags["financial"]
            and "financial_trading"
            in exclusions
        ):
            counts[
                "financial_trading"
            ] += 1
            continue

        if (
            flags["customer"]
            and "customer_work"
            in exclusions
        ):
            counts[
                "customer_work"
            ] += 1
            continue

        if (
            flags["selling"]
            and "selling_content"
            in exclusions
        ):
            counts[
                "selling_content"
            ] += 1
            continue

        eligibility = str(
            item.get(
                "eligibility",
                "UNKNOWN",
            )
        ).strip().upper()

        if eligibility == "INELIGIBLE":
            counts[
                "known_ineligible"
            ] += 1
            continue

        capital = _safe_decimal(
            item.get(
                "capital_required"
            )
        )

        capital_currency = (
            _capital_currency(
                item
            )
        )

        if (
            capital is not None
            and capital_currency
            == user_currency
            and capital
            > max_spend
        ):
            counts[
                "same_currency_over_budget"
            ] += 1
            continue

        category = _category(
            flags
        )

        money_text, money_known = (
            _money_needed(
                item
            )
        )

        time_text, time_known = (
            _human_time(
                item
            )
        )

        ai_text, ai_known = (
            _ai_share(
                item
            )
        )

        upside_text, upside_known = (
            _upside(
                item
            )
        )

        still_checking: list[str] = []

        if not money_known:
            still_checking.append(
                "How much cash is actually required"
            )

        if not time_known:
            still_checking.append(
                "How much of your time it would require"
            )

        if not ai_known:
            still_checking.append(
                "How much of the work AI can actually do"
            )

        if not upside_known:
            still_checking.append(
                "The realistic economic upside"
            )

        still_checking.append(
            "Whether your residence and citizenship satisfy every rule"
        )

        source = _source_url(
            item
        )

        score = _confidence(
            item
        )

        if source:
            score += 0.05

        if eligibility == "ELIGIBLE":
            score += 0.03

        result = {
            "candidate_id":
                str(
                    item.get(
                        "opportunity_id"
                    )
                    or item.get(
                        "candidate_id"
                    )
                    or f"stored-{index}"
                ),
            "title":
                title,
            "category":
                category,
            "verdict":
                "CHECK",
            "why_this_fits":
                _why(category),
            "potential_upside":
                upside_text,
            "money_needed":
                money_text,
            "human_time_needed":
                time_text,
            "ai_share_of_work":
                ai_text,
            "eligibility":
                _eligibility_for_person(
                    item
                ),
            "still_needs_checking":
                still_checking,
            "source_url":
                source,
        }

        ranked.append(
            (
                score,
                index,
                result,
            )
        )

    ranked.sort(
        key=lambda value: (
            -value[0],
            value[1],
            str(
                value[2][
                    "title"
                ]
            ).casefold(),
        )
    )

    recommendations = [
        row[2]
        for row in ranked[:3]
    ]

    effects: list[str] = []

    labels = {
        "traditional_jobs":
            "traditional jobs",
        "goal_mismatch":
            "opportunities that do not match your selected goal",
        "competitions":
            "competitions",
        "grants":
            "grants/funding opportunities",
        "financial_trading":
            "financial/trading opportunities",
        "customer_work":
            "customer-facing opportunities",
        "selling_content":
            "selling/content opportunities",
        "known_ineligible":
            "opportunities already known to be ineligible",
        "same_currency_over_budget":
            "same-currency opportunities above your cash/risk limit",
    }

    for key, count in counts.items():

        if count:
            effects.append(
                f"Removed {count} {labels[key]}."
            )

    warnings = [
        (
            "Residence and citizenship are now part of the profile. "
            "AOO will not claim personal eligibility until the "
            "opportunity rules and required platforms/tools have "
            "been checked against them."
        ),
        (
            "Currency is explicit. AOO does not compare amounts "
            "across different currencies unless the candidate "
            "contains a compatible currency denomination."
        ),
    ]

    if not recommendations:

        if goal == "time":
            empty_reason = (
                "The current stored shortlist contains no "
                "verified time-saving opportunity that survives "
                "your filters. AOO will not substitute a random "
                "money-making opportunity."
            )
        else:
            empty_reason = (
                "Nothing in the current stored shortlist survives "
                "the limits AOO can verify. AOO will not invent a "
                "recommendation to fill the page."
            )

    else:
        empty_reason = None

    return {
        "status":
            "PASS",
        "profile":
            canonical,
        "recommendations":
            recommendations,
        "considered_count":
            len(items),
        "surviving_count":
            len(ranked),
        "profile_effects":
            effects,
        "warnings":
            warnings,
        "empty_reason":
            empty_reason,
        "external_actions_taken":
            0,
        "model_calls":
            0,
    }
