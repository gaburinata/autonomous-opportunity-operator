from __future__ import annotations

import copy
import json
import os

from pathlib import Path
from typing import Any


_PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_RADAR_PATH = (
    _PROJECT_ROOT
    / "data"
    / "RADAR_SHORTLIST.json"
)

DEFAULT_DISCOVERY_PATH = (
    _PROJECT_ROOT
    / "data"
    / "discovery"
    / "latest.json"
)


_ALLOWED_ITEM_KEYS = (
    "opportunity_id",
    "title",
    "organizer",
    "decision",
    "eligibility",
    "canonical_source_url",
    "external_deadline",
    "estimated_effort_hours",
    "economic_mechanism",
    "asset_fit",
    "confidence",
    "reason_codes",
    "freshness_note",
    "discovered_via",
    "discovered_at",
)


def _empty(reason: str) -> dict[str, Any]:
    return {
        "status": "EMPTY",
        "reason_codes": [reason],
        "scan_id": None,
        "scanned_at": None,
        "raw_candidate_count": 0,
        "shortlist_count": 0,
        "decision_counts": {
            "PROMOTE": 0,
            "WATCH": 0,
            "KILL": 0,
            "OTHER": 0,
        },
        "items": [],
    }


def _scalar(value: Any) -> Any:
    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
            type(None),
        ),
    ):
        return value

    return None


def _normalize_item(
    raw: dict[str, Any],
) -> dict[str, Any]:

    out = {}

    for key in _ALLOWED_ITEM_KEYS:
        if key not in raw:
            continue

        value = raw[key]

        if key == "reason_codes":
            if isinstance(value, list):
                out[key] = [
                    str(x)
                    for x in value[:12]
                    if isinstance(
                        x,
                        (str, int, float),
                    )
                ]
            continue

        safe = _scalar(value)

        if safe is not None:
            out[key] = safe

    return out


def _read_feed(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
    ):
        return _empty(
            "RADAR_FEED_UNAVAILABLE"
        )

    if not isinstance(data, dict):
        return _empty(
            "RADAR_FEED_INVALID"
        )

    raw_items = data.get("items")

    if not isinstance(raw_items, list):
        return _empty(
            "RADAR_ITEMS_MISSING"
        )

    items = []

    for raw in raw_items:
        if not isinstance(raw, dict):
            continue

        item = _normalize_item(raw)

        if not isinstance(
            item.get("title"),
            str,
        ):
            continue

        items.append(item)

    counts = {
        "PROMOTE": 0,
        "WATCH": 0,
        "KILL": 0,
        "OTHER": 0,
    }

    for item in items:
        decision = str(
            item.get(
                "decision",
                "OTHER",
            )
        ).upper()

        if decision in counts:
            counts[decision] += 1
        else:
            counts["OTHER"] += 1

    return {
        "status":
            "PASS"
            if items
            else data.get(
                "status",
                "EMPTY",
            ),

        "reason_codes":
            data.get(
                "reason_codes",
                [],
            ),

        "scan_id":
            _scalar(
                data.get("scan_id")
            ),

        "scanned_at":
            _scalar(
                data.get("scanned_at")
            ),

        "raw_candidate_count":
            int(
                data.get(
                    "raw_candidate_count",
                    len(items),
                )
                or 0
            ),

        "shortlist_count":
            len(items),

        "decision_counts":
            counts,

        "items":
            items,
    }


def _merge(
    live: dict[str, Any],
    stored: dict[str, Any],
) -> dict[str, Any]:

    merged = []
    seen = set()

    for source in (live, stored):
        for item in source.get("items", []):
            if not isinstance(item, dict):
                continue

            key = (
                str(
                    item.get(
                        "canonical_source_url",
                        "",
                    )
                )
                .strip()
                .casefold(),
                str(
                    item.get(
                        "title",
                        "",
                    )
                )
                .strip()
                .casefold(),
            )

            if key in seen:
                continue

            seen.add(key)
            merged.append(
                copy.deepcopy(item)
            )

    counts = {
        "PROMOTE": 0,
        "WATCH": 0,
        "KILL": 0,
        "OTHER": 0,
    }

    for item in merged:
        decision = str(
            item.get(
                "decision",
                "OTHER",
            )
        ).upper()

        if decision in counts:
            counts[decision] += 1
        else:
            counts["OTHER"] += 1

    return {
        "status": "PASS",
        "reason_codes": [],
        "scan_id":
            live.get("scan_id")
            or stored.get("scan_id"),
        "scanned_at":
            live.get("scanned_at")
            or stored.get("scanned_at"),
        "raw_candidate_count":
            int(
                live.get(
                    "raw_candidate_count",
                    0,
                )
                or 0
            )
            + int(
                stored.get(
                    "raw_candidate_count",
                    0,
                )
                or 0
            ),
        "shortlist_count":
            len(merged),
        "decision_counts":
            counts,
        "items":
            merged,
    }


def load_opportunity_feed(
    path: str | Path | None = None,
) -> dict[str, Any]:

    if path is not None:
        return copy.deepcopy(
            _read_feed(
                Path(path)
            )
        )

    configured = os.environ.get(
        "AOO_RADAR_SHORTLIST_PATH"
    )

    radar_path = (
        Path(configured)
        if configured
        else DEFAULT_RADAR_PATH
    )

    stored = _read_feed(
        radar_path
    )

    live = _read_feed(
        DEFAULT_DISCOVERY_PATH
    )

    if (
        live.get("status") == "PASS"
        and live.get("items")
    ):
        return copy.deepcopy(
            _merge(
                live,
                stored,
            )
        )

    return copy.deepcopy(stored)
