"""Email/password accounts through Firebase Authentication (REST API, no extra package)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

import streamlit as st

from core import config

USER_KEY = "user"
API = "https://identitytoolkit.googleapis.com/v1/accounts:"


class AuthError(Exception):
    """Raised with a friendly message when auth fails."""


def explain(code: str) -> str:
    c = code.upper()
    if "EMAIL_EXISTS" in c:
        return "This email is already registered. Use the Log in tab."
    if any(k in c for k in ("INVALID_LOGIN_CREDENTIALS", "INVALID_PASSWORD", "EMAIL_NOT_FOUND")):
        return "Wrong email or password, or this account does not exist yet. Try signing up first."
    if "WEAK_PASSWORD" in c:
        return "Password is too weak. Use at least 6 characters."
    if "INVALID_EMAIL" in c:
        return "That email address does not look valid."
    if "TOO_MANY_ATTEMPTS" in c:
        return "Too many attempts. Wait a few minutes and try again."
    if "USER_DISABLED" in c:
        return "This account has been disabled."
    if "OPERATION_NOT_ALLOWED" in c:
        return "Email/password sign-in is off. In Firebase: Authentication → Sign-in method → enable Email/Password."
    if "API_KEY" in c or "API KEY" in c:
        return "Firebase rejected the API key. Check FIREBASE_API_KEY (Project settings → General → Web API Key)."
    if "CONFIGURATION_NOT_FOUND" in c:
        return "Firebase Authentication is not set up yet. In the Firebase console open Authentication and click Get started."
    return "Sign-in service said: " + code[:160]


def _post(endpoint: str, payload: dict) -> dict:
    key = config.firebase_key()
    if not key:
        raise AuthError("Firebase is not configured. Add FIREBASE_API_KEY to your .env.")
    req = urllib.request.Request(
        API + endpoint + "?key=" + key,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            msg = json.loads(exc.read().decode("utf-8")).get("error", {}).get("message", "") or str(exc)
        except Exception:
            msg = str(exc)
        raise AuthError(explain(msg)) from exc
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        raise AuthError("Cannot reach the sign-in service. Check your internet connection.") from exc


def current_user() -> dict | None:
    return st.session_state.get(USER_KEY)


def current_user_id() -> str:
    user = current_user()
    if not user:
        raise AuthError("Please log in first.")
    return user["id"]


def _send_verification(id_token: str) -> None:
    _post("sendOobCode", {"requestType": "VERIFY_EMAIL", "idToken": id_token})


def _is_verified(id_token: str) -> bool:
    users = _post("lookup", {"idToken": id_token}).get("users") or []
    return bool(users and users[0].get("emailVerified"))


def sign_up(email: str, password: str) -> str:
    email = email.strip()
    if not email or len(password) < 6:
        raise AuthError("Enter an email and a password of at least 6 characters.")
    res = _post("signUp", {"email": email, "password": password, "returnSecureToken": True})
    if not config.require_email_verification():
        st.session_state[USER_KEY] = {"id": res["localId"], "email": email}
        return "Account created. Welcome to Pivio!"
    try:
        _send_verification(res["idToken"])
    except AuthError:
        pass
    return (
    f"Account created successfully! A verification email was requested for {email}. "
    "Please check your inbox and spam/junk folder for the verification link. "
    "Click the link before logging in." )


def sign_in(email: str, password: str) -> None:
    email = email.strip()
    if not email or not password:
        raise AuthError("Enter your email and password.")
    res = _post("signInWithPassword", {"email": email, "password": password, "returnSecureToken": True})
    if config.require_email_verification() and not _is_verified(res["idToken"]):
        try:
            _send_verification(res["idToken"])
        except AuthError:
            pass
        raise AuthError("Your email is not verified yet. We just sent a new verification link. "
                        "Click it, then log in again.")
    st.session_state[USER_KEY] = {"id": res["localId"], "email": res.get("email", email)}


def sign_out() -> None:
    st.session_state.clear()
