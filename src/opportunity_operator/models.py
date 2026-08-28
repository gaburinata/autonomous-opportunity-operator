from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


class MechanismClass(StrEnum):
    CONTEST = "contest"
    MACHINE_API = "machine_api"
    TRADING = "trading"


class State(StrEnum):
    DISCOVERED = "DISCOVERED"
    VERIFIED = "VERIFIED"
    INVESTIGATING = "INVESTIGATING"
    TESTED = "TESTED"
    PROMOTE = "PROMOTE"
    WATCH = "WATCH"
    KILL = "KILL"
    DECISION_REQUIRED = "DECISION_REQUIRED"


@dataclass(frozen=True)
class UnitEconomics:
    revenue_per_unit: Decimal
    variable_cost_per_unit: Decimal
    confidence: Decimal

    @property
    def margin_per_unit(self) -> Decimal:
        return self.revenue_per_unit - self.variable_cost_per_unit


@dataclass(frozen=True)
class Opportunity:
    opportunity_id: str
    title: str
    mechanism_class: MechanismClass
    summary: str
    source_ids: tuple[str, ...]
    eligible: bool
    deadline_utc: datetime | None = None
    capital_required: Decimal = Decimal("0")
    requires_account_action: bool = False
    requires_legal_action: bool = False
    similarity_signature: frozenset[str] = frozenset()
    unit_economics: UnitEconomics | None = None

    def __post_init__(self) -> None:
        if not self.source_ids:
            raise ValueError("at least one provenance source is required")
        if self.deadline_utc is not None and self.deadline_utc.tzinfo is None:
            raise ValueError("deadline must be timezone-aware")
        if self.capital_required < 0:
            raise ValueError("capital_required cannot be negative")


@dataclass(frozen=True)
class FailureMemory:
    memory_id: str
    hypothesis: str
    environment: str
    parameter_regime: Mapping[str, str]
    failure_class: str
    evidence_ids: tuple[str, ...]
    similarity_signature: frozenset[str]
    revival_conditions: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameter_regime", MappingProxyType(dict(self.parameter_regime)))
        if not self.evidence_ids or not self.similarity_signature:
            raise ValueError("failure memory requires evidence and a signature")


@dataclass(frozen=True)
class FailureMatch:
    memory_id: str
    score: Decimal
    overlapping_terms: tuple[str, ...]
    warning: bool


@dataclass(frozen=True)
class GateDecision:
    passed: bool
    expensive_work_allowed: bool
    terminal_state: State | None
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class EconomicEvidenceDecision:
    disposition: State
    revenue_per_unit: Decimal | None
    variable_cost_per_unit: Decimal | None
    margin_per_unit: Decimal | None
    confidence: Decimal
    evidence_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
    abstained: bool = False


@dataclass(frozen=True)
class EvidenceEvent:
    event_id: str
    opportunity_id: str
    occurred_at: datetime
    kind: str
    actor: str
    source_ref: str
    payload: Mapping[str, Any]
    payload_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None:
            raise ValueError("event timestamp must be timezone-aware")
        copied = dict(self.payload)
        canonical = json.dumps(copied, sort_keys=True, separators=(",", ":"), default=str)
        object.__setattr__(self, "payload", _freeze(copied))
        object.__setattr__(self, "payload_sha256", sha256(canonical.encode()).hexdigest())

    @classmethod
    def create(cls, opportunity_id: str, kind: str, actor: str, source_ref: str,
               payload: Mapping[str, Any]) -> "EvidenceEvent":
        return cls(str(uuid4()), opportunity_id, datetime.now(timezone.utc), kind, actor, source_ref, payload)
