"""Firestore client + in-memory test backend.

Collections (user-partitioned):
  users/{user_id}                            — { email, plan, created_at }
  users/{user_id}/brand_mappings/{auto_id}   — { category, brand, display_name, ... }
  users/{user_id}/category_mappings/{auto_id}
  users/{user_id}/favorites/{auto_id}
  users/{user_id}/search_history/{auto_id}
  users/{user_id}/monthly_snapshots/{auto_id}
  users/{user_id}/error_logs/{auto_id}

Shared:
  global_category_pricing/{category}  — opt-in shared pricing data
"""
from __future__ import annotations
import logging
from typing import Any, Iterable

from app.config import get_settings

log = logging.getLogger(__name__)
_client = None


def init_firestore():
    global _client
    s = get_settings()
    if s.test_mode:
        _client = _InMemoryFirestore()
        log.info("firestore: in-memory test backend")
        return
    try:
        from google.cloud import firestore  # type: ignore
        _client = firestore.Client(project=s.firebase_project)
        log.info("firestore: real client project=%s", s.firebase_project)
    except Exception as e:
        log.warning("firestore client init failed (%s) — falling back to in-memory", e)
        _client = _InMemoryFirestore()


def db():
    if _client is None:
        init_firestore()
    return _client


# ── In-memory test backend ────────────────────────────────────────────────────
class _InMemoryDoc:
    def __init__(self, store: dict, path: str):
        self._store = store
        self._path = path

    def set(self, data: dict, merge: bool = False):
        if merge and self._path in self._store:
            self._store[self._path].update(data)
        else:
            self._store[self._path] = dict(data)

    def get(self):
        return _InMemorySnapshot(self._path, self._store.get(self._path))

    def update(self, data: dict):
        if self._path not in self._store:
            self._store[self._path] = {}
        self._store[self._path].update(data)

    def delete(self):
        self._store.pop(self._path, None)


class _InMemorySnapshot:
    def __init__(self, path: str, data: dict | None):
        self._path = path
        self._data = data
        self.exists = data is not None
        self.id = path.rsplit("/", 1)[-1]

    def to_dict(self):
        return dict(self._data) if self._data else None


class _InMemoryCol:
    def __init__(self, store: dict, prefix: str):
        self._store = store
        self._prefix = prefix
        self._filters: list[tuple] = []
        self._limit: int | None = None
        self._order: tuple | None = None

    def document(self, doc_id: str | None = None):
        if doc_id is None:
            import uuid
            doc_id = uuid.uuid4().hex[:12]
        return _InMemoryDoc(self._store, f"{self._prefix}/{doc_id}")

    def add(self, data: dict):
        doc = self.document()
        doc.set(data)
        return None, doc

    def where(self, field: str, op: str, value: Any):
        new = _InMemoryCol(self._store, self._prefix)
        new._filters = self._filters + [(field, op, value)]
        new._limit, new._order = self._limit, self._order
        return new

    def order_by(self, field: str, direction: str = "ASCENDING"):
        new = _InMemoryCol(self._store, self._prefix)
        new._filters = list(self._filters)
        new._limit = self._limit
        new._order = (field, direction)
        return new

    def limit(self, n: int):
        new = _InMemoryCol(self._store, self._prefix)
        new._filters = list(self._filters)
        new._order = self._order
        new._limit = n
        return new

    def stream(self) -> Iterable[_InMemorySnapshot]:
        rows = []
        for path, data in self._store.items():
            if not path.startswith(self._prefix + "/"):
                continue
            ok = True
            for field, op, val in self._filters:
                v = data.get(field)
                if op == "==" and v != val: ok = False; break
                if op == ">=" and not (v is not None and v >= val): ok = False; break
                if op == "<=" and not (v is not None and v <= val): ok = False; break
                if op == ">" and not (v is not None and v > val): ok = False; break
                if op == "<" and not (v is not None and v < val): ok = False; break
            if ok:
                rows.append((path, data))
        if self._order:
            f, d = self._order
            rows.sort(key=lambda x: x[1].get(f, 0), reverse=(d == "DESCENDING"))
        if self._limit:
            rows = rows[: self._limit]
        for path, data in rows:
            yield _InMemorySnapshot(path, data)


class _InMemoryFirestore:
    def __init__(self):
        self._store: dict = {}

    def collection(self, name: str):
        return _InMemoryCol(self._store, name)

    def document(self, path: str):
        return _InMemoryDoc(self._store, path)


# ── Helpers ───────────────────────────────────────────────────────────────────
def user_col(user_id: str, name: str):
    """users/{uid}/{name}"""
    return db().collection(f"users/{user_id}/{name}")


def user_doc(user_id: str):
    return db().document(f"users/{user_id}")
