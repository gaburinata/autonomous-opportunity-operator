"""Bounded capture of public HTTPS primary-source evidence."""

from collections.abc import Mapping
from html.parser import HTMLParser
import hashlib
import http.client
import ipaddress
import re
import socket
import ssl
from urllib.parse import urljoin, urlsplit


_KEYS = (
    "status", "reason_codes", "source_url", "final_url", "redirect_chain",
    "content_type", "byte_length", "source_sha256", "text_length",
    "text_sha256", "text",
)


def _failure(source_url, reason, **values):
    result = dict.fromkeys(_KEYS, "")
    result.update({
        "status": "FAIL_CLOSED",
        "reason_codes": [reason],
        "source_url": source_url,
        "redirect_chain": [],
        "byte_length": 0,
        "text_length": 0,
        "text_sha256": "",
        "text": "",
    })
    result.update(values)
    result["text_length"] = 0
    result["text_sha256"] = ""
    result["text"] = ""
    return result


def _default_resolver(host):
    return sorted({item[4][0] for item in socket.getaddrinfo(host, 443)})


def _validate_url(url, resolver):
    if not isinstance(url, str):
        return "INVALID_SOURCE_URL", []
    try:
        parsed = urlsplit(url)
        if (parsed.scheme.lower() != "https" or not parsed.hostname or
                parsed.username is not None or parsed.password is not None or
                (parsed.port is not None and parsed.port != 443)):
            return "INVALID_SOURCE_URL", []
        if parsed.hostname.lower() == "localhost":
            return "NON_PUBLIC_SOURCE", []
        addresses = resolver(parsed.hostname)
        if not addresses:
            return "NON_PUBLIC_SOURCE", []
        if any(not ipaddress.ip_address(address).is_global for address in addresses):
            return "NON_PUBLIC_SOURCE", []
    except (TypeError, ValueError, OSError, socket.gaierror):
        return "NON_PUBLIC_SOURCE", []
    return None, list(addresses)


def _url_reason(url, resolver):
    return _validate_url(url, resolver)[0]


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection whose TCP peer is fixed while TLS verifies hostname."""

    def __init__(self, hostname, address, timeout):
        super().__init__(hostname, port=443, timeout=timeout,
                         context=ssl.create_default_context())
        self._validated_address = address

    def connect(self):
        sock = socket.create_connection(
            (self._validated_address, self.port), self.timeout,
            self.source_address,
        )
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def _default_fetch(url, timeout_seconds, max_bytes, resolver, addresses):
    current_url = url
    current_addresses = addresses
    redirect_chain = []
    for hop in range(6):
        parsed = urlsplit(current_url)
        target = parsed.path or "/"
        if parsed.query:
            target += "?" + parsed.query
        connection = _PinnedHTTPSConnection(
            parsed.hostname, current_addresses[0], timeout_seconds,
        )
        try:
            connection.request(
                "GET", target,
                headers={"Host": parsed.hostname,
                         "User-Agent": "AOO-Primary-Source-Intake/1.0"},
            )
            response = connection.getresponse()
            headers = dict(response.getheaders())
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location or hop == 5:
                    raise OSError("invalid or excessive redirect")
                new_url = urljoin(current_url, location)
                reason, current_addresses = _validate_url(new_url, resolver)
                if reason:
                    raise ValueError(reason)
                redirect_chain.append(new_url)
                current_url = new_url
                continue
            body = response.read(max_bytes + 1)
            return {
                "status_code": response.status, "headers": headers,
                "body": body, "final_url": current_url,
                "redirect_chain": redirect_chain,
            }
        finally:
            connection.close()
    raise OSError("redirect limit exceeded")


class _VisibleHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def _normalized_text(body, content_type):
    binary_signatures = (
        b"%PDF-", b"GIF87a", b"GIF89a", b"\x89PNG\r\n\x1a\n",
        b"\xff\xd8\xff", b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08",
        b"\x1f\x8b", b"\x7fELF", b"\x00asm",
    )
    if body.startswith(binary_signatures):
        return None
    charset_match = re.search(r"charset\s*=\s*[\"']?([^;\s\"']+)", content_type, re.I)
    charset = charset_match.group(1) if charset_match else "utf-8"
    try:
        decoded = body.decode(charset, errors="strict")
    except (LookupError, UnicodeDecodeError):
        return None
    # NULs and most C0 controls are strong binary signals in purported text.
    if "\x00" in decoded or any(
            ord(char) < 32 and char not in "\t\n\r\f" for char in decoded):
        return None
    if content_type.split(";", 1)[0].strip().lower() == "text/html":
        parser = _VisibleHTML()
        parser.feed(decoded)
        parser.close()
        decoded = " ".join(parser.parts)
    return " ".join(decoded.split())


def ingest_primary_source(source_url, *, fetcher=None, resolver=None,
                          timeout_seconds=15, max_bytes=1000000):
    """Capture one public HTTPS source as deterministic evidence."""
    resolver = _default_resolver if resolver is None else resolver
    reason, addresses = _validate_url(source_url, resolver)
    if reason:
        return _failure(source_url, reason)
    if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
        return _failure(source_url, "SOURCE_FETCH_FAILED")
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes <= 0:
        return _failure(source_url, "SOURCE_FETCH_FAILED")
    try:
        fetched = (_default_fetch(source_url, timeout_seconds, max_bytes, resolver, addresses)
                   if fetcher is None else fetcher(source_url, timeout_seconds, max_bytes))
        if not isinstance(fetched, Mapping):
            raise TypeError
        status_code = fetched.get("status_code")
        headers = fetched.get("headers", {})
        body = fetched.get("body")
        final_url = fetched.get("final_url")
        redirect_chain = fetched.get("redirect_chain", [])
        if not isinstance(body, bytes) or not isinstance(headers, Mapping):
            raise TypeError
        if not isinstance(redirect_chain, (list, tuple)):
            raise TypeError
    except ValueError as exc:
        code = str(exc)
        return _failure(source_url, code if code in {"INVALID_SOURCE_URL", "NON_PUBLIC_SOURCE"} else "SOURCE_FETCH_FAILED")
    except Exception:
        return _failure(source_url, "SOURCE_FETCH_FAILED")

    # The default transport already validates and pins every hop exactly once.
    # Injected fetchers still need their returned provenance independently checked.
    if fetcher is not None:
        for url in [*redirect_chain, final_url]:
            reason = _url_reason(url, resolver)
            if reason:
                return _failure(source_url, reason, final_url=final_url,
                                redirect_chain=list(redirect_chain))
    if not isinstance(status_code, int) or not 200 <= status_code < 300:
        return _failure(source_url, "SOURCE_HTTP_STATUS_REJECTED", final_url=final_url, redirect_chain=list(redirect_chain))
    if len(body) > max_bytes:
        return _failure(source_url, "SOURCE_TOO_LARGE", final_url=final_url, redirect_chain=list(redirect_chain), byte_length=len(body))

    content_type = str(next((value for key, value in headers.items() if str(key).lower() == "content-type"), ""))
    media_type = content_type.split(";", 1)[0].strip().lower()
    if not (media_type == "text/html" or media_type.startswith("text/")):
        return _failure(source_url, "UNSUPPORTED_CONTENT_TYPE", final_url=final_url, redirect_chain=list(redirect_chain), content_type=content_type, byte_length=len(body), source_sha256=hashlib.sha256(body).hexdigest())
    text = _normalized_text(body, content_type)
    common = dict(final_url=final_url, redirect_chain=list(redirect_chain), content_type=content_type,
                  byte_length=len(body), source_sha256=hashlib.sha256(body).hexdigest())
    if text is None:
        return _failure(source_url, "UNSUPPORTED_CONTENT_TYPE", **common)
    if not text:
        return _failure(source_url, "SOURCE_TEXT_EMPTY", **common)
    if ((not redirect_chain and final_url != source_url)
            or (redirect_chain and redirect_chain[-1] != final_url)):
        return _failure(source_url, "SOURCE_FETCH_FAILED", **common)
    return {
        "status": "PASS", "reason_codes": ["PRIMARY_SOURCE_CAPTURED"],
        "source_url": source_url, **common, "text_length": len(text),
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "text": text,
    }


def build_discovered_event(document, opportunity_id):
    """Build the stable discovered event for successful captured evidence."""
    if (not isinstance(document, Mapping) or document.get("status") != "PASS" or
            not isinstance(opportunity_id, str) or not opportunity_id):
        raise ValueError("successful document and non-empty opportunity_id required")
    if set(document) != set(_KEYS):
        raise ValueError("invalid intake document keys")
    if document["reason_codes"] != ["PRIMARY_SOURCE_CAPTURED"]:
        raise ValueError("invalid success reason")
    string_fields = ("source_url", "final_url", "content_type",
                     "source_sha256", "text_sha256", "text")
    if any(not isinstance(document[key], str) or not document[key]
           for key in string_fields):
        raise ValueError("invalid intake document strings")
    for key in ("byte_length", "text_length"):
        if (not isinstance(document[key], int) or isinstance(document[key], bool)
                or document[key] <= 0):
            raise ValueError("invalid intake document length")
    sha256_pattern = re.compile(r"[0-9a-f]{64}\Z")
    if (not sha256_pattern.fullmatch(document["source_sha256"])
            or not sha256_pattern.fullmatch(document["text_sha256"])):
        raise ValueError("invalid intake document digest")
    if document["text_length"] != len(document["text"]):
        raise ValueError("inconsistent text length")
    expected_text_hash = hashlib.sha256(document["text"].encode("utf-8")).hexdigest()
    if document["text_sha256"] != expected_text_hash:
        raise ValueError("inconsistent text digest")
    chain = document["redirect_chain"]
    if not isinstance(chain, list):
        raise ValueError("invalid redirect chain")
    urls = [document["source_url"], *chain, document["final_url"]]
    if any(not _is_sane_evidence_url(url) for url in urls):
        raise ValueError("invalid source URL evidence")
    if ((not chain and document["source_url"] != document["final_url"])
            or (chain and chain[-1] != document["final_url"])):
        raise ValueError("inconsistent redirect chain")
    digest = hashlib.sha256((opportunity_id + "\x00" + document["text_sha256"]).encode("utf-8")).hexdigest()
    return {
        "event_id": "source-" + digest,
        "event_type": "opportunity.discovered",
        "opportunity_id": opportunity_id,
        "payload": {
            "source_url": document["source_url"], "final_url": document["final_url"],
            "redirect_chain": list(document["redirect_chain"]), "content_type": document["content_type"],
            "byte_length": document["byte_length"], "source_sha256": document["source_sha256"],
            "text_length": document["text_length"], "text_sha256": document["text_sha256"],
            "source_text": document["text"],
        },
    }


def _is_sane_evidence_url(url):
    try:
        parsed = urlsplit(url)
        return bool(
            isinstance(url, str) and parsed.scheme.lower() == "https"
            and parsed.hostname and parsed.username is None
            and parsed.password is None
            and (parsed.port is None or parsed.port == 443)
        )
    except (TypeError, ValueError):
        return False
