"""Firebase Authentication pour Scout.

Supporte deux modes :
- Firebase Auth (utilisateurs généraux via Google/Email/Phone)
- Legacy JWT maison (professionnels médicaux B2B, rétrocompatibilité)

Endpoints lecture (GET) : accès libre (visiteurs anonymes).
Endpoints écriture (POST/PUT/DELETE) : token Firebase ou legacy JWT requis.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional, Tuple

from fastapi import Request
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)

# --- Firebase Admin SDK initialization ---
_firebase_app = None
_firebase_initialized = False


def _init_firebase() -> bool:
    """Initialise Firebase Admin SDK (une seule fois)."""
    global _firebase_app, _firebase_initialized
    if _firebase_initialized:
        return _firebase_app is not None
    _firebase_initialized = True
    try:
        import firebase_admin
        from firebase_admin import credentials

        # Option 1: JSON string dans une variable d'env (Render)
        creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if creds_json:
            cred_dict = json.loads(creds_json)
            cred = credentials.Certificate(cred_dict)
            _firebase_app = firebase_admin.initialize_app(cred)
            log.info("[AUTH] Firebase Admin SDK initialisé (env JSON).")
            return True

        # Option 2: fichier GOOGLE_APPLICATION_CREDENTIALS
        creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_file and os.path.isfile(creds_file):
            cred = credentials.Certificate(creds_file)
            _firebase_app = firebase_admin.initialize_app(cred)
            log.info("[AUTH] Firebase Admin SDK initialisé (fichier).")
            return True

        log.warning("[AUTH] Aucun credentials Firebase trouvé. Auth Firebase désactivée.")
        return False
    except ImportError:
        log.warning("[AUTH] firebase-admin non installé. Auth Firebase désactivée.")
        return False
    except Exception as e:
        log.error("[AUTH] Échec initialisation Firebase : %s", e)
        return False


def verify_firebase_token(id_token: str) -> Optional[dict]:
    """Vérifie un ID token Firebase et retourne les claims."""
    if not _init_firebase():
        return None
    try:
        from firebase_admin import auth
        decoded = auth.verify_id_token(id_token)
        return {
            "uid": decoded.get("uid"),
            "email": decoded.get("email"),
            "name": decoded.get("name", ""),
            "picture": decoded.get("picture", ""),
            "provider": "firebase",
        }
    except Exception as e:
        log.debug("[AUTH] Token Firebase invalide : %s", e)
        return None


def extract_bearer(authorization: Optional[str]) -> Optional[str]:
    """Extrait le token Bearer depuis le header Authorization."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip()


def authenticate_request(
    authorization: Optional[str],
) -> Tuple[Optional[dict], Optional[str]]:
    """Authentifie une requête via Firebase ou legacy JWT.

    Returns:
        (user_info, error_message)
        - user_info: dict avec uid/email/name/provider, ou None si anonyme
        - error_message: str si le token est présent mais invalide, None sinon
    """
    token = extract_bearer(authorization)
    if not token:
        return None, None  # Pas de token → anonyme (OK pour GET)

    # 1. Essayer Firebase
    firebase_user = verify_firebase_token(token)
    if firebase_user:
        return firebase_user, None

    # 2. Essayer legacy JWT (professionnels médicaux)
    try:
        from bot.auth import decode_token
        legacy_payload = decode_token(token)
        if legacy_payload:
            return {
                "uid": str(legacy_payload.get("uid", "")),
                "email": legacy_payload.get("sub", ""),
                "name": "",
                "provider": "legacy_jwt",
                "license": legacy_payload.get("license", ""),
            }, None
    except Exception:
        pass

    # Token présent mais invalide
    return None, "Token invalide ou expiré."


# --- Routes protégées ---
# GET endpoints (lecture) : accès libre
# POST/PUT/DELETE endpoints (écriture) : auth requise

# Endpoints qui ne nécessitent JAMAIS d'auth (même en POST)
_PUBLIC_WRITE_ENDPOINTS = {
    "/api/auth/register",
    "/api/auth/login",
    "/api/auth/firebase",
    "/api/chat",
    "/api/learn/explain",
    "/api/push/subscribe",
    "/api/predictions/bet",
}

# Endpoints GET qui nécessitent quand même l'auth (données sensibles)
_PROTECTED_READ_ENDPOINTS: set = set()


def require_auth_for_request(
    request: Request, authorization: Optional[str]
) -> Tuple[Optional[dict], Optional[JSONResponse]]:
    """Middleware d'authentification unifié.

    - GET : accès libre (retourne user=None si pas de token)
    - POST/PUT/DELETE : auth obligatoire (retourne 401 si pas de token valide)
    - Exceptions : _PUBLIC_WRITE_ENDPOINTS (register/login)

    Returns:
        (user, error_response)
    """
    user, error = authenticate_request(authorization)

    path = request.url.path
    method = request.method.upper()

    # Endpoints publics en écriture (register, login)
    if path in _PUBLIC_WRITE_ENDPOINTS:
        return user, None

    # Endpoints lecture protégés
    if method == "GET" and path in _PROTECTED_READ_ENDPOINTS:
        if not user:
            return None, JSONResponse(
                {"error": "Authentification requise."},
                status_code=401,
            )
        return user, None

    # Lecture standard : accès libre
    if method == "GET":
        return user, None

    # Écriture : auth requise
    if not user:
        if error:
            return None, JSONResponse({"error": error}, status_code=401)
        return None, JSONResponse(
            {"error": "Authentification requise pour cette action."},
            status_code=401,
        )

    return user, None
