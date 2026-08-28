"""Firestore persistence adapter for terminal workflow outcomes."""

from collections.abc import Mapping
import copy
import json
import re


_COLLECTION = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_KEY = re.compile(r"^[A-Za-z0-9_-]{1,256}$")


def _json_mapping(value):
    if not isinstance(value, Mapping):
        raise ValueError("outcome must be a mapping")
    try:
        return json.loads(json.dumps(dict(value), allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError("outcome must be JSON-compatible") from exc


class FirestoreWorkflowStore:
    """Atomic claim/completion storage using one document per idempotency key."""

    def __init__(self, collection="aoo_workflows", *, database="(default)", client=None):
        if not isinstance(collection, str) or not _COLLECTION.fullmatch(collection):
            raise ValueError("invalid collection")
        if not isinstance(database, str) or not database or len(database) > 128:
            raise ValueError("invalid database")
        if client is None:
            from google.cloud import firestore
            client = firestore.Client(database=database)
        self._client = client
        self._collection = collection

    def _document(self, key):
        if not isinstance(key, str) or not _KEY.fullmatch(key):
            raise ValueError("invalid key")
        return self._client.collection(self._collection).document(key)

    def load(self, key):
        snapshot = self._document(key).get()
        if not getattr(snapshot, "exists", False):
            return None
        value = snapshot.to_dict()
        if not isinstance(value, Mapping) or value.get("state") != "COMPLETED":
            return None
        try:
            return copy.deepcopy(_json_mapping(value.get("outcome")))
        except ValueError:
            return None

    def claim(self, key):
        document = self._document(key)
        try:
            document.create({"state": "CLAIMED"})
            return True
        except Exception:
            # Atomic create is authoritative. Suppress only an existing document.
            if getattr(document.get(), "exists", False):
                return False
            raise

    def complete(self, key, outcome):
        document = self._document(key)
        stored = _json_mapping(outcome)
        lock = getattr(self._client, "lock", None)
        if lock is not None:  # deterministic Firestore-shaped test seam
            with lock:
                snapshot = document.get()
                value = snapshot.to_dict() if snapshot.exists else None
                if value != {"state": "CLAIMED"}:
                    raise ValueError("workflow is not claimed")
                document.set({"state": "COMPLETED", "outcome": copy.deepcopy(stored)})
            return

        from google.cloud import firestore
        transaction = self._client.transaction()

        @firestore.transactional
        def finish(txn):
            snapshot = document.get(transaction=txn)
            value = snapshot.to_dict() if snapshot.exists else None
            if value != {"state": "CLAIMED"}:
                raise ValueError("workflow is not claimed")
            txn.set(document, {"state": "COMPLETED", "outcome": stored})

        finish(transaction)
