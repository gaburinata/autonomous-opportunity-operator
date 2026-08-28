from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Mapping


_REQUIRED_FIELDS = {
    "memory_id",
    "hypothesis",
    "environment",
    "parameter_regime",
    "failure_class",
    "evidence",
    "similarity_signature",
    "reconsideration_conditions",
}

_SHA256 = re.compile(
    r"^[0-9a-f]{64}$"
)


class FailureMemoryLibraryError(ValueError):
    pass


def _default_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "failure_memory"
        / "library.jsonl"
    )


def resolve_failure_memory_path(
    path: str | Path | None = None,
) -> Path:
    if path is not None:
        return Path(path)

    override = os.environ.get(
        "AOO_FAILURE_MEMORY_PATH",
        "",
    ).strip()

    if override:
        return Path(override)

    return _default_path()


def _text(
    value: Any,
    field: str,
    *,
    max_length: int = 2000,
) -> str:
    if not isinstance(value, str):
        raise FailureMemoryLibraryError(
            f"{field}:NOT_STRING"
        )

    value = value.strip()

    if not value:
        raise FailureMemoryLibraryError(
            f"{field}:EMPTY"
        )

    if len(value) > max_length:
        raise FailureMemoryLibraryError(
            f"{field}:TOO_LONG"
        )

    return value


def validate_failure_record(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise FailureMemoryLibraryError(
            "RECORD:NOT_MAPPING"
        )

    if set(record) != _REQUIRED_FIELDS:
        raise FailureMemoryLibraryError(
            "RECORD:FIELD_SET_MISMATCH"
        )

    memory_id = _text(
        record["memory_id"],
        "memory_id",
        max_length=200,
    )

    hypothesis = _text(
        record["hypothesis"],
        "hypothesis",
    )

    environment = _text(
        record["environment"],
        "environment",
    )

    failure_class = _text(
        record["failure_class"],
        "failure_class",
        max_length=200,
    )

    regime = record["parameter_regime"]

    if not isinstance(regime, Mapping):
        raise FailureMemoryLibraryError(
            "parameter_regime:NOT_MAPPING"
        )

    normalized_regime = {}

    for key, value in regime.items():
        key = _text(
            key,
            "parameter_regime.key",
            max_length=200,
        )

        value = _text(
            value,
            "parameter_regime.value",
            max_length=1000,
        )

        normalized_regime[key] = value

    evidence = record["evidence"]

    if (
        not isinstance(evidence, list)
        or not evidence
    ):
        raise FailureMemoryLibraryError(
            "evidence:INVALID"
        )

    normalized_evidence = []
    seen_sources = set()

    for item in evidence:
        if (
            not isinstance(item, Mapping)
            or set(item)
            != {"source_id", "digest"}
        ):
            raise FailureMemoryLibraryError(
                "evidence:ITEM_INVALID"
            )

        source_id = _text(
            item["source_id"],
            "evidence.source_id",
            max_length=500,
        )

        digest = _text(
            item["digest"],
            "evidence.digest",
            max_length=64,
        ).lower()

        if not _SHA256.fullmatch(digest):
            raise FailureMemoryLibraryError(
                "evidence.digest:NOT_SHA256"
            )

        if source_id in seen_sources:
            raise FailureMemoryLibraryError(
                "evidence:DUPLICATE_SOURCE"
            )

        seen_sources.add(source_id)

        normalized_evidence.append(
            {
                "source_id": source_id,
                "digest": digest,
            }
        )

    signature = record[
        "similarity_signature"
    ]

    if (
        not isinstance(signature, list)
        or not signature
    ):
        raise FailureMemoryLibraryError(
            "similarity_signature:INVALID"
        )

    normalized_signature = []
    seen_terms = set()

    for value in signature:
        value = _text(
            value,
            "similarity_signature.item",
            max_length=200,
        ).lower()

        if value in seen_terms:
            continue

        seen_terms.add(value)
        normalized_signature.append(value)

    reconsideration = record[
        "reconsideration_conditions"
    ]

    if not isinstance(
        reconsideration,
        list,
    ):
        raise FailureMemoryLibraryError(
            "reconsideration_conditions:NOT_LIST"
        )

    normalized_reconsideration = [
        _text(
            value,
            "reconsideration_conditions.item",
        )
        for value in reconsideration
    ]

    return {
        "memory_id":
            memory_id,
        "hypothesis":
            hypothesis,
        "environment":
            environment,
        "parameter_regime":
            normalized_regime,
        "failure_class":
            failure_class,
        "evidence":
            normalized_evidence,
        "similarity_signature":
            normalized_signature,
        "reconsideration_conditions":
            normalized_reconsideration,
    }


def _canonical(
    value: Mapping[str, Any],
) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def load_failure_records(
    path: str | Path | None = None,
) -> tuple[dict[str, Any], ...]:
    resolved = resolve_failure_memory_path(
        path
    )

    if not resolved.is_file():
        raise FailureMemoryLibraryError(
            "FAILURE_MEMORY_LIBRARY_MISSING"
        )

    records = []
    seen_ids = set()

    for line_number, line in enumerate(
        resolved.read_text(
            encoding="utf-8"
        ).splitlines(),
        1,
    ):
        if not line.strip():
            continue

        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise FailureMemoryLibraryError(
                "INVALID_JSON_LINE:"
                + str(line_number)
            ) from exc

        record = validate_failure_record(
            raw
        )

        memory_id = record["memory_id"]

        if memory_id in seen_ids:
            raise FailureMemoryLibraryError(
                "DUPLICATE_MEMORY_ID:"
                + memory_id
            )

        seen_ids.add(memory_id)
        records.append(record)

    if not records:
        raise FailureMemoryLibraryError(
            "FAILURE_MEMORY_LIBRARY_EMPTY"
        )

    records.sort(
        key=lambda item:
            item["memory_id"]
    )

    return tuple(records)


def append_failure_record(
    record: Mapping[str, Any],
    path: str | Path | None = None,
) -> str:
    """
    Controller-side durable writer.

    Deliberately not exposed as an ADK tool.
    Agents may read authoritative history but cannot
    create, mutate, or overwrite failure memories.
    """
    normalized = validate_failure_record(
        record
    )

    resolved = resolve_failure_memory_path(
        path
    )

    resolved.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    existing = []

    if resolved.exists():
        existing = list(
            load_failure_records(
                resolved
            )
        )

    for prior in existing:
        if (
            prior["memory_id"]
            != normalized["memory_id"]
        ):
            continue

        if (
            _canonical(prior)
            == _canonical(normalized)
        ):
            return "UNCHANGED"

        raise FailureMemoryLibraryError(
            "MEMORY_ID_CONFLICT:"
            + normalized["memory_id"]
        )

    existing.append(
        normalized
    )

    existing.sort(
        key=lambda item:
            item["memory_id"]
    )

    tmp = resolved.with_suffix(
        resolved.suffix + ".tmp"
    )

    tmp.write_text(
        "".join(
            _canonical(item) + "\n"
            for item in existing
        ),
        encoding="utf-8",
    )

    os.replace(
        tmp,
        resolved,
    )

    return "APPENDED"
