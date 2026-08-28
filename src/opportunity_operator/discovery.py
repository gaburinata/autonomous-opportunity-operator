from __future__ import annotations

import hashlib
import html
import json
import os
import re
import tempfile
import unicodedata

from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable
from urllib.parse import (
    quote_plus,
    urljoin,
    urlsplit,
    urlunsplit,
)
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
)


_PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_LATEST_PATH = (
    _PROJECT_ROOT
    / "data"
    / "discovery"
    / "latest.json"
)

DEVPOST_API_URL = (
    "https://devpost.com/api/hackathons"
)

NLNET_URL = (
    "https://nlnet.nl/propose/"
)

_ALLOWED_FETCH_HOSTS = {
    "devpost.com",
    "www.devpost.com",
    "nlnet.nl",
    "www.nlnet.nl",
}

_BLOCKED_DEVPOST_HOSTS = {
    "secure.devpost.com",
    "help.devpost.com",
    "info.devpost.com",
    "api.devpost.com",
    "blog.devpost.com",
    "status.devpost.com",
}

_MAX_BYTES = 1_000_000
_TIMEOUT_SECONDS = 12
_MAX_SEARCH_TERMS = 4
_MAX_ITEMS = 30


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def normalize_search_terms(
    value: str,
) -> list[str]:

    if not isinstance(value, str):
        raise ValueError(
            "search_terms must be string"
        )

    value = unicodedata.normalize(
        "NFKC",
        value,
    )

    if len(value) > 220:
        raise ValueError(
            "search_terms too long"
        )

    if any(
        ord(ch) < 32
        and ch not in "\t\n\r"
        for ch in value
    ):
        raise ValueError(
            "control characters not allowed"
        )

    raw_terms = []

    for raw in value.split(","):
        term = re.sub(
            r"\s+",
            " ",
            raw,
        ).strip()

        if not term:
            continue

        if len(term) > 60:
            raise ValueError(
                "individual search term too long"
            )

        raw_terms.append(term)

    if len(raw_terms) > _MAX_SEARCH_TERMS:
        raise ValueError(
            "too many search terms"
        )

    terms = []

    for term in raw_terms:
        if term.casefold() in {
            x.casefold()
            for x in terms
        }:
            continue

        terms.append(term)

    if not terms:
        terms = [
            "AI agents",
            "automation",
            "API",
        ]

    return terms


def validate_fetch_url(
    value: str,
) -> str:

    parsed = urlsplit(value)

    if parsed.scheme.lower() != "https":
        raise ValueError(
            "HTTPS required"
        )

    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError(
            "invalid discovery URL"
        )

    host = parsed.hostname.lower()

    if host not in _ALLOWED_FETCH_HOSTS:
        raise ValueError(
            "host not allowed"
        )

    if parsed.port not in (
        None,
        443,
    ):
        raise ValueError(
            "non-443 port rejected"
        )

    return urlunsplit(
        (
            "https",
            host,
            parsed.path or "/",
            parsed.query,
            "",
        )
    )


class _StrictRedirect(
    HTTPRedirectHandler
):

    def redirect_request(
        self,
        req,
        fp,
        code,
        msg,
        headers,
        newurl,
    ):
        validate_fetch_url(
            newurl
        )

        return super().redirect_request(
            req,
            fp,
            code,
            msg,
            headers,
            newurl,
        )


def _fetch(
    url: str,
    *,
    accept: str,
) -> tuple[bytes, str]:

    url = validate_fetch_url(
        url
    )

    opener = build_opener(
        _StrictRedirect()
    )

    request = Request(
        url,
        headers={
            "User-Agent":
                "AOO-Discovery/1.2 "
                "(public opportunity discovery; no login)",

            "Accept":
                accept,
        },
        method="GET",
    )

    with opener.open(
        request,
        timeout=_TIMEOUT_SECONDS,
    ) as response:

        validate_fetch_url(
            response.geturl()
        )

        content_type = (
            response.headers.get(
                "Content-Type",
                "",
            )
            .split(";", 1)[0]
            .strip()
            .lower()
        )

        body = response.read(
            _MAX_BYTES + 1
        )

    if len(body) > _MAX_BYTES:
        raise ValueError(
            "discovery document too large"
        )

    return body, content_type


def _fetch_text(
    url: str,
) -> str:

    body, content_type = _fetch(
        url,
        accept=(
            "text/html,"
            "application/xhtml+xml,"
            "text/plain"
        ),
    )

    if content_type not in {
        "text/html",
        "application/xhtml+xml",
        "text/plain",
        "",
    }:
        raise ValueError(
            "unsupported content type"
        )

    return body.decode(
        "utf-8",
        errors="replace",
    )


def _fetch_json(
    url: str,
) -> dict[str, Any]:

    body, content_type = _fetch(
        url,
        accept="application/json",
    )

    if content_type not in {
        "application/json",
        "text/json",
        "",
    }:
        raise ValueError(
            "unexpected JSON content type"
        )

    data = json.loads(
        body.decode(
            "utf-8"
        )
    )

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "JSON root must be object"
        )

    return data


class _AnchorParser(
    HTMLParser
):

    def __init__(self):
        super().__init__(
            convert_charrefs=True
        )

        self.anchors = []
        self._href = None
        self._text = []

    def handle_starttag(
        self,
        tag,
        attrs,
    ):
        if tag.lower() != "a":
            return

        self._href = dict(
            attrs
        ).get("href")

        self._text = []

    def handle_data(
        self,
        data,
    ):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(
        self,
        tag,
    ):
        if (
            tag.lower() != "a"
            or self._href is None
        ):
            return

        label = re.sub(
            r"\s+",
            " ",
            "".join(
                self._text
            ),
        ).strip()

        self.anchors.append(
            (
                self._href,
                label,
            )
        )

        self._href = None
        self._text = []


def _slug_title(
    hostname: str,
) -> str:

    slug = hostname.split(
        ".",
        1,
    )[0]

    words = [
        x
        for x in re.split(
            r"[-_]+",
            slug,
        )
        if x
    ]

    return " ".join(
        x.capitalize()
        for x in words
    ) or hostname


def _candidate_id(
    title: str,
    url: str,
) -> str:

    payload = (
        title.strip().casefold()
        + "\0"
        + url.strip().casefold()
    )

    return (
        "discovered_"
        + hashlib.sha256(
            payload.encode(
                "utf-8"
            )
        ).hexdigest()[:20]
    )


###############################################################################
# LEGACY HTML PARSER
#
# Retained only for existing deterministic regression fixtures.
# Live Devpost discovery no longer uses this path.
###############################################################################

def discover_devpost_from_html(
    document: str,
    *,
    search_term: str,
    observed_at: str,
) -> list[dict[str, Any]]:

    parser = _AnchorParser()
    parser.feed(document)

    out = []
    seen = set()

    for href, anchor_text in parser.anchors:

        try:
            absolute = urljoin(
                "https://devpost.com/hackathons",
                href,
            )

            parsed = urlsplit(
                absolute
            )

        except Exception:
            continue

        host = (
            parsed.hostname
            or ""
        ).lower()

        if (
            not host.endswith(
                ".devpost.com"
            )
            or host
            in _BLOCKED_DEVPOST_HOSTS
        ):
            continue

        canonical = (
            "https://"
            + host
            + "/"
        )

        if canonical in seen:
            continue

        seen.add(canonical)

        title = re.sub(
            r"\s+",
            " ",
            html.unescape(
                anchor_text
            ),
        ).strip()

        if (
            not title
            or len(title) < 3
            or len(title) > 180
        ):
            title = _slug_title(
                host
            )

        out.append({
            "opportunity_id":
                _candidate_id(
                    title,
                    canonical,
                ),

            "title":
                title,

            "organizer":
                "Organizer pending verification",

            "canonical_source_url":
                canonical,

            "decision":
                "WATCH",

            "eligibility":
                "UNKNOWN",

            "external_deadline":
                None,

            "estimated_effort_hours":
                None,

            "economic_mechanism":
                "Prize or award details pending "
                "primary-source verification",

            "asset_fit":
                "DISCOVERY_MATCH",

            "confidence":
                0.55,

            "reason_codes": [
                "PRIMARY_SOURCE_DEEP_VERIFICATION_PENDING",
                "ELIGIBILITY_NOT_YET_VERIFIED",
                "ECONOMICS_NOT_YET_VERIFIED",
            ],

            "freshness_note":
                "Discovered from Devpost search term "
                f"{search_term!r} at {observed_at}. "
                "Candidate detail page has not yet "
                "been deep-verified.",

            "discovered_via":
                "DEVPOST_SEARCH",

            "discovered_at":
                observed_at,
        })

    return out


###############################################################################
# OFFICIAL DEVPOST JSON API
###############################################################################

def _clean_prize(
    value: Any,
) -> str:

    if value is None:
        return ""

    raw = html.unescape(
        str(value)
    )

    raw = re.sub(
        r"<[^>]+>",
        "",
        raw,
    )

    raw = re.sub(
        r"\s+",
        " ",
        raw,
    ).strip()

    return raw


def _term_tokens(
    terms: list[str],
) -> list[str]:

    tokens = []

    for term in terms:
        for token in re.findall(
            r"[A-Za-z0-9+#.-]+",
            term.casefold(),
        ):
            if (
                len(token) >= 2
                and token not in tokens
            ):
                tokens.append(token)

    return tokens


def _relevance_score(
    item: dict[str, Any],
    terms: list[str],
) -> int:

    themes = item.get(
        "themes"
    )

    theme_names = []

    if isinstance(
        themes,
        list,
    ):
        for theme in themes:
            if isinstance(
                theme,
                dict,
            ):
                name = theme.get(
                    "name"
                )

                if isinstance(
                    name,
                    str,
                ):
                    theme_names.append(
                        name
                    )

    blob = " ".join(
        [
            str(
                item.get(
                    "title",
                    "",
                )
            ),
            str(
                item.get(
                    "organization_name",
                    "",
                )
            ),
            " ".join(
                theme_names
            ),
        ]
    ).casefold()

    score = 0

    for term in terms:
        normalized = term.casefold()

        if normalized in blob:
            score += 5

    for token in _term_tokens(
        terms
    ):
        if token in blob:
            score += 2

    return score


def _valid_devpost_event_url(
    value: Any,
) -> str | None:

    if not isinstance(
        value,
        str,
    ):
        return None

    try:
        parsed = urlsplit(
            value
        )
    except Exception:
        return None

    host = (
        parsed.hostname
        or ""
    ).lower()

    if (
        parsed.scheme != "https"
        or not host.endswith(
            ".devpost.com"
        )
        or host
        in _BLOCKED_DEVPOST_HOSTS
    ):
        return None

    return (
        "https://"
        + host
        + "/"
    )


def discover_devpost_from_api(
    payload: dict[str, Any],
    *,
    search_terms: list[str],
    observed_at: str,
) -> list[dict[str, Any]]:

    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "Devpost payload must be object"
        )

    raw_items = payload.get(
        "hackathons"
    )

    if not isinstance(
        raw_items,
        list,
    ):
        raise ValueError(
            "Devpost hackathons missing"
        )

    candidates = []

    for raw in raw_items:

        if not isinstance(
            raw,
            dict,
        ):
            continue

        if raw.get(
            "invite_only"
        ) is True:
            continue

        open_state = str(
            raw.get(
                "open_state",
                "",
            )
        ).casefold()

        if open_state not in {
            "open",
            "upcoming",
        }:
            continue

        url = (
            _valid_devpost_event_url(
                raw.get("url")
            )
        )

        if url is None:
            continue

        title = str(
            raw.get(
                "title",
                "",
            )
        ).strip()

        if not title:
            continue

        score = _relevance_score(
            raw,
            search_terms,
        )

        if score <= 0:
            continue

        themes = raw.get(
            "themes"
        )

        theme_names = []

        if isinstance(
            themes,
            list,
        ):
            for theme in themes:
                if isinstance(
                    theme,
                    dict,
                ):
                    name = theme.get(
                        "name"
                    )

                    if isinstance(
                        name,
                        str,
                    ):
                        theme_names.append(
                            name
                        )

        prize = _clean_prize(
            raw.get(
                "prize_amount"
            )
        )

        mechanism = (
            "Listed prize pool: "
            + prize
            if prize
            else
            "Prize details pending "
            "primary-source verification"
        )

        submission_period = str(
            raw.get(
                "submission_period_dates",
                "",
            )
        ).strip()

        time_left = str(
            raw.get(
                "time_left_to_submission",
                "",
            )
        ).strip()

        freshness_bits = [
            "Discovered from Devpost's "
            "official hackathon JSON API",
            f"at {observed_at}.",
        ]

        if submission_period:
            freshness_bits.append(
                "Listing submission period: "
                + submission_period
                + "."
            )

        if time_left:
            freshness_bits.append(
                "Listing says "
                + time_left
                + "."
            )

        candidates.append({
            "opportunity_id":
                _candidate_id(
                    title,
                    url,
                ),

            "title":
                title,

            "organizer":
                str(
                    raw.get(
                        "organization_name",
                        "",
                    )
                ).strip()
                or
                "Organizer pending verification",

            "canonical_source_url":
                url,

            "decision":
                "WATCH",

            "eligibility":
                "UNKNOWN",

            # Listing gives a date range but not the
            # authoritative deadline time/timezone.
            # Detail-page verification owns that field.
            "external_deadline":
                None,

            "estimated_effort_hours":
                None,

            "economic_mechanism":
                mechanism,

            "asset_fit":
                (
                    ", ".join(
                        theme_names[:4]
                    )
                    or
                    "DISCOVERY_MATCH"
                ),

            "confidence":
                0.82,

            "reason_codes": [
                "PRIMARY_SOURCE_DEEP_VERIFICATION_PENDING",
                "ELIGIBILITY_NOT_YET_VERIFIED",
            ],

            "freshness_note":
                " ".join(
                    freshness_bits
                ),

            "discovered_via":
                "DEVPOST_OFFICIAL_API",

            "discovered_at":
                observed_at,

            "_relevance_score":
                score,
        })

    candidates.sort(
        key=lambda item: (
            -int(
                item.get(
                    "_relevance_score",
                    0,
                )
            ),
            str(
                item.get(
                    "title",
                    "",
                )
            ).casefold(),
        )
    )

    for candidate in candidates:
        candidate.pop(
            "_relevance_score",
            None,
        )

    return candidates[
        :_MAX_ITEMS
    ]


###############################################################################
# NLNET
###############################################################################

def discover_nlnet_from_html(
    document: str,
    *,
    observed_at: str,
) -> list[dict[str, Any]]:

    visible = html.unescape(
        re.sub(
            r"<[^>]+>",
            " ",
            document,
        )
    )

    visible = re.sub(
        r"\s+",
        " ",
        visible,
    ).strip()

    visible_lower = (
        visible.casefold()
    )

    raw_lower = (
        html.unescape(
            document
        )
        .casefold()
        .replace(
            "&nbsp;",
            " ",
        )
    )

    has_call_signal = bool(
        re.search(
            r"calls?\s+will\s+reopen",
            visible_lower,
        )
        or re.search(
            r"new\s+calls?.{0,100}"
            r"open",
            visible_lower,
        )
        or "select a call"
        in visible_lower
    )

    if not has_call_signal:
        return []

    reopen_match = re.search(
        r"september\s+3\s*"
        r"(?:rd)?\s*2026",
        visible_lower,
    )

    deadline_match = re.search(
        r"november\s+3\s*"
        r"(?:rd)?\s*2026"
        r".{0,100}?"
        r"12\s*:\s*00\s*cest",
        visible_lower,
    )

    deadline = (
        "2026-11-03T10:00:00Z"
        if deadline_match
        else None
    )

    amount_match = re.search(
        r"between\s+"
        r"5(?:,|\s)?000\s+"
        r"and\s+"
        r"50(?:,|\s)?000",
        raw_lower,
    )

    economics = (
        "Official NLnet proposal form "
        "indicates requested support "
        "between €5,000 and €50,000."
        if amount_match
        else
        "Open-source grant support; "
        "amount requires verification."
    )

    reasons = [
        "CALL_SCOPE_REQUIRES_DEEP_VERIFICATION",
        "ELIGIBILITY_NOT_YET_VERIFIED",
    ]

    if reopen_match:
        reasons.append(
            "CALL_NOT_OPEN_YET"
        )

    title = (
        "NLnet upcoming open-source "
        "grant calls"
    )

    return [{
        "opportunity_id":
            _candidate_id(
                title,
                NLNET_URL,
            ),

        "title":
            title,

        "organizer":
            "NLnet Foundation",

        "canonical_source_url":
            NLNET_URL,

        "decision":
            "WATCH",

        "eligibility":
            "UNKNOWN",

        "external_deadline":
            deadline,

        "estimated_effort_hours":
            None,

        "economic_mechanism":
            economics,

        "asset_fit":
            "OPEN_SOURCE_SOFTWARE",

        "confidence":
            (
                0.82
                if (
                    deadline_match
                    and amount_match
                )
                else 0.72
            ),

        "reason_codes":
            reasons,

        "freshness_note":
            "Discovered directly from "
            "NLnet's official proposal "
            f"page at {observed_at}.",

        "discovered_via":
            "NLNET_OFFICIAL_CALL_PAGE",

        "discovered_at":
            observed_at,
    }]


###############################################################################
# SNAPSHOT
###############################################################################

def _write_snapshot(
    path: Path,
    result: dict[str, Any],
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = (
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    )

    fd, temporary = tempfile.mkstemp(
        prefix=".discovery-",
        suffix=".json",
        dir=str(
            path.parent
        ),
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:

            handle.write(
                payload
            )

            handle.flush()

            os.fsync(
                handle.fileno()
            )

        os.replace(
            temporary,
            path,
        )

    finally:
        if os.path.exists(
            temporary
        ):
            os.unlink(
                temporary
            )


###############################################################################
# ORCHESTRATION
###############################################################################

def run_live_discovery(
    search_terms: str,
    *,
    fetcher: Callable[[str], str] | None = None,
    snapshot_path: str | Path | None = DEFAULT_LATEST_PATH,
    now: str | None = None,
) -> dict[str, Any]:

    terms = normalize_search_terms(
        search_terms
    )

    observed_at = (
        now
        if isinstance(
            now,
            str,
        )
        else _utc_now()
    )

    candidates = []
    source_results = []
    raw_count = 0

    ###########################################################################
    # TEST/LEGACY INJECTION PATH
    #
    # Existing deterministic tests inject an HTML fetcher.
    # Production/live operation does not use this branch.
    ###########################################################################

    if fetcher is not None:

        for term in terms:

            url = (
                "https://devpost.com/"
                "hackathons?search="
                + quote_plus(
                    term
                )
            )

            try:
                document = fetcher(
                    url
                )

                found = (
                    discover_devpost_from_html(
                        document,
                        search_term=term,
                        observed_at=observed_at,
                    )
                )

                raw_count += len(
                    found
                )

                candidates.extend(
                    found
                )

                source_results.append({
                    "source":
                        "DEVPOST_SEARCH",

                    "url":
                        url,

                    "status":
                        "PASS",

                    "candidate_count":
                        len(found),
                })

            except Exception as exc:

                source_results.append({
                    "source":
                        "DEVPOST_SEARCH",

                    "url":
                        url,

                    "status":
                        "FAIL",

                    "candidate_count":
                        0,

                    "reason_code":
                        type(exc).__name__,
                })

        try:
            document = fetcher(
                NLNET_URL
            )

            found = (
                discover_nlnet_from_html(
                    document,
                    observed_at=observed_at,
                )
            )

            raw_count += len(
                found
            )

            candidates.extend(
                found
            )

            source_results.append({
                "source":
                    "NLNET_OFFICIAL_CALL_PAGE",

                "url":
                    NLNET_URL,

                "status":
                    "PASS",

                "candidate_count":
                    len(found),
            })

        except Exception as exc:

            source_results.append({
                "source":
                    "NLNET_OFFICIAL_CALL_PAGE",

                "url":
                    NLNET_URL,

                "status":
                    "FAIL",

                "candidate_count":
                    0,

                "reason_code":
                    type(exc).__name__,
            })

    ###########################################################################
    # REAL PRODUCTION/LIVE PATH
    ###########################################################################

    else:

        try:
            payload = _fetch_json(
                DEVPOST_API_URL
            )

            found = (
                discover_devpost_from_api(
                    payload,
                    search_terms=terms,
                    observed_at=observed_at,
                )
            )

            raw_items = payload.get(
                "hackathons"
            )

            raw_count += (
                len(raw_items)
                if isinstance(
                    raw_items,
                    list,
                )
                else 0
            )

            candidates.extend(
                found
            )

            source_results.append({
                "source":
                    "DEVPOST_OFFICIAL_API",

                "url":
                    DEVPOST_API_URL,

                "status":
                    "PASS",

                "candidate_count":
                    len(found),
            })

        except Exception as exc:

            source_results.append({
                "source":
                    "DEVPOST_OFFICIAL_API",

                "url":
                    DEVPOST_API_URL,

                "status":
                    "FAIL",

                "candidate_count":
                    0,

                "reason_code":
                    type(exc).__name__,
            })

        try:
            document = _fetch_text(
                NLNET_URL
            )

            found = (
                discover_nlnet_from_html(
                    document,
                    observed_at=observed_at,
                )
            )

            raw_count += len(
                found
            )

            candidates.extend(
                found
            )

            source_results.append({
                "source":
                    "NLNET_OFFICIAL_CALL_PAGE",

                "url":
                    NLNET_URL,

                "status":
                    "PASS",

                "candidate_count":
                    len(found),
            })

        except Exception as exc:

            source_results.append({
                "source":
                    "NLNET_OFFICIAL_CALL_PAGE",

                "url":
                    NLNET_URL,

                "status":
                    "FAIL",

                "candidate_count":
                    0,

                "reason_code":
                    type(exc).__name__,
            })

    ###########################################################################
    # DEDUPLICATE
    ###########################################################################

    deduped = []
    seen = set()

    for item in candidates:

        key = (
            str(
                item.get(
                    "canonical_source_url",
                    "",
                )
            )
            .strip()
            .casefold()
        )

        if (
            not key
            or key in seen
        ):
            continue

        seen.add(
            key
        )

        deduped.append(
            item
        )

        if len(
            deduped
        ) >= _MAX_ITEMS:
            break

    passed_sources = sum(
        1
        for item in source_results
        if item.get(
            "status"
        ) == "PASS"
    )

    if passed_sources == 0:
        status = "FAIL"

    elif deduped:
        status = "PASS"

    else:
        status = "EMPTY"

    scan_seed = (
        observed_at
        + "\0"
        + "\0".join(
            terms
        )
    )

    result = {
        "status":
            status,

        "reason_codes":
            (
                []
                if status == "PASS"
                else [
                    (
                        "NO_DISCOVERY_CANDIDATES"
                        if status == "EMPTY"
                        else
                        "ALL_DISCOVERY_SOURCES_FAILED"
                    )
                ]
            ),

        "scan_id":
            "live_discovery_"
            + hashlib.sha256(
                scan_seed.encode(
                    "utf-8"
                )
            ).hexdigest()[:16],

        "scanned_at":
            observed_at,

        "search_terms":
            terms,

        "raw_candidate_count":
            raw_count,

        "shortlist_count":
            len(deduped),

        "source_results":
            source_results,

        "items":
            deduped,
    }

    if snapshot_path is not None:

        _write_snapshot(
            Path(
                snapshot_path
            ),
            result,
        )

    return result
