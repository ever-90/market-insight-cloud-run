"""Firebase Auth JWT verification + API key fallback.

Two entry points:
  get_current_user — verifies Firebase ID token (Authorization: Bearer ...)
  get_current_user_or_api_key — accepts API key (X-API-Key header) for B2B
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from app.config import get_settings
from app.services.firestore_client import db

log = logging.getLogger(__name__)
_firebase_inited = False


@dataclass
class CurrentUser:
    user_id: str
    email: str
    auth_method: str  # "jwt" | "api_key" | "test"


def _init_firebase():
    global _firebase_inited
    if _firebase_inited:
        return
    s = get_settings()
    if s.test_mode:
        _firebase_inited = True
        return
    try:
        import firebase_admin  # type: ignore
        from firebase_admin import credentials  # type: ignore
        try:
            firebase_admin.get_app()
        except ValueError:
            # In Cloud Run, ADC credentials work without a key file.
            # projectId = Firebase Auth 프로젝트(auth_project) — 토큰 aud 검증 대상.
            #   Firestore용 firebase_project 와 분리 (GCP=foodncare / Auth=foodncare-a2c54).
            firebase_admin.initialize_app(options={"projectId": s.auth_project})
        _firebase_inited = True
    except Exception as e:
        log.warning("firebase admin init failed: %s", e)


def _verify_jwt(token: str) -> CurrentUser:
    s = get_settings()
    if s.test_mode:
        # Test stub: token "test-uid-<email>" -> user_id=test-uid, email=<email>
        if token.startswith("test-"):
            parts = token.split("-", 2)
            return CurrentUser(user_id=parts[1], email=parts[2] if len(parts) > 2 else "test@example.com", auth_method="test")
        raise HTTPException(status_code=401, detail="invalid_test_token")
    _init_firebase()
    try:
        from firebase_admin import auth as fb_auth  # type: ignore
        decoded = fb_auth.verify_id_token(token, check_revoked=False)
        return CurrentUser(
            user_id=decoded["uid"],
            email=decoded.get("email", ""),
            auth_method="jwt",
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"jwt_verify_failed: {e}")


def _verify_api_key(key: str) -> CurrentUser:
    """Look up api_keys collection: api_keys/{key} -> { user_id, email, active }"""
    snap = db().document(f"api_keys/{key}").get()
    if not snap.exists:
        raise HTTPException(status_code=401, detail="invalid_api_key")
    data = snap.to_dict()
    if not data.get("active", True):
        raise HTTPException(status_code=401, detail="api_key_revoked")
    return CurrentUser(user_id=data["user_id"], email=data.get("email", ""), auth_method="api_key")


async def get_current_user(authorization: Optional[str] = Header(None)) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    return _verify_jwt(authorization[7:].strip())


async def get_current_user_or_api_key(
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None),
) -> CurrentUser:
    if x_api_key:
        return _verify_api_key(x_api_key)
    if authorization and authorization.lower().startswith("bearer "):
        return _verify_jwt(authorization[7:].strip())
    raise HTTPException(status_code=401, detail="no_auth_provided")
