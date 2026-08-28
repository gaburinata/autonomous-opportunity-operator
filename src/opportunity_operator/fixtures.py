"""Synthetic, offline-only examples. They do not describe real returns."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from .models import FailureMemory, MechanismClass, Opportunity, UnitEconomics


FIXTURE_NOW = datetime(2026, 8, 13, tzinfo=timezone.utc)


def contest_opportunity(*, eligible: bool = True, capital: str = "0") -> Opportunity:
    return Opportunity("contest-1", "Synthetic agent contest", MechanismClass.CONTEST,
                       "Build an offline synthetic entry", ("primary:contest-rules",), eligible,
                       FIXTURE_NOW + timedelta(days=10), Decimal(capital), unit_economics=UnitEconomics(
                           Decimal("1000"), Decimal("50"), Decimal("0.75")))


def terrible_api_opportunity() -> Opportunity:
    return Opportunity("api-1", "Synthetic paid API wrapper", MechanismClass.MACHINE_API,
                       "Automated calls with adverse unit economics", ("synthetic:api-pricing",), True,
                       unit_economics=UnitEconomics(Decimal("0.01"), Decimal("0.20"), Decimal("0.95")),
                       similarity_signature=frozenset({"api", "per-call"}))


def historical_trading_failure() -> FailureMemory:
    return FailureMemory(
        "failure-short-vol", "Premium exceeds tail losses", "Synthetic stressed market",
        {"leverage": "high", "liquidity": "normal-only"}, "HIDDEN_TAIL_RISK", ("evidence:stress-1",),
        frozenset({"trading", "short-vol", "tail-risk", "crowded"}),
        ("Capped downside is independently demonstrated", "Stress-regime liquidity is measured"))


def failure_like_trading_opportunity() -> Opportunity:
    return Opportunity("trade-1", "Synthetic short-volatility strategy", MechanismClass.TRADING,
                       "Backtest a crowded short-volatility signal", ("synthetic:market-study",), True,
                       unit_economics=UnitEconomics(Decimal("1.20"), Decimal("1.00"), Decimal("0.85")),
                       similarity_signature=frozenset({"trading", "short-vol", "tail-risk", "crowded"}))
