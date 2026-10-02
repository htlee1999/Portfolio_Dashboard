"""Authentication: user store compatible with data/users.json + signed session cookies."""

import hashlib
import hmac
import logging
import os
import re
import secrets
from datetime import datetime

from fastapi import Depends, HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .storage import data_path, load_json, save_json

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128
SESSION_COOKIE = "pd_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days
RESET_MAX_AGE = 60 * 30  # password reset links live 30 minutes
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

log = logging.getLogger(__name__)

# ── Password hashing ─────────────────────────────────────────────────────────
# New hashes are PBKDF2-SHA256 with a per-user random salt ("pbkdf2_sha256$iter$salt$hash").
# Hashes from the original Streamlit app (one round of SHA-256 with a shared salt) still
# verify, and are upgraded to the new format the next time that user signs in.

_PBKDF2_ITERATIONS = 600_000  # OWASP 2023 recommendation for PBKDF2-SHA256
_LEGACY_SALT = "portfolio_dashboard_salt_2024"


def _hash_password(password: str, salt: str | None = None, iterations: int = _PBKDF2_ITERATIONS) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def _legacy_hash(password: str) -> str:
    return hashlib.sha256((password + _LEGACY_SALT).encode()).hexdigest()


def _verify_password(password: str, stored: str) -> bool:
    if stored.startswith("pbkdf2_sha256$"):
        _, iterations, salt, _ = stored.split("$", 3)
        return hmac.compare_digest(stored, _hash_password(password, salt, int(iterations)))
    return hmac.compare_digest(stored, _legacy_hash(password))


def _needs_rehash(stored: str) -> bool:
    return not stored.startswith(f"pbkdf2_sha256${_PBKDF2_ITERATIONS}$")


# Verified against when the username doesn't exist, so a failed sign-in takes the
# same time either way and response timing doesn't reveal which usernames exist.
_DUMMY_HASH = _hash_password(secrets.token_urlsafe(16))


def _session_secret() -> str:
    secret = os.getenv("SESSION_SECRET")
    if secret:
        if len(secret) < 32:
            raise RuntimeError("SESSION_SECRET must be at least 32 characters long")
        return secret
    if os.getenv("VERCEL") or os.getenv("REQUIRE_SESSION_SECRET") == "1":
        # Serverless filesystems are read-only or per-instance, so a generated key
        # would differ between instances and sign everyone out at random.
        raise RuntimeError("SESSION_SECRET must be set in production")
    path = data_path(".session_secret")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    secret = secrets.token_urlsafe(48)
    with open(path, "w", encoding="utf-8") as f:
        f.write(secret)
    os.chmod(path, 0o600)
    return secret


_SECRET = _session_secret()
_serializer = URLSafeTimedSerializer(_SECRET, salt="pd-session")
_reset_serializer = URLSafeTimedSerializer(_SECRET, salt="pd-password-reset")


def _users_path() -> str:
    return data_path("users.json")


def load_users() -> dict:
    users = load_json(_users_path(), None)
    if users is None:
        # First run: create an admin. The password comes from ADMIN_PASSWORD, or is
        # generated and printed once, so no deployment starts with a known password.
        password = os.getenv("ADMIN_PASSWORD")
        if password and validate_password(password):
            raise RuntimeError(f"ADMIN_PASSWORD: {validate_password(password)}")
        generated = not password
        password = password or secrets.token_urlsafe(12)
        users = {
            "admin": {
                "password_hash": _hash_password(password),
                "role": "admin",
                "created_at": datetime.now().isoformat(),
                "last_login": None,
            }
        }
        save_json(_users_path(), users)
        if generated:
            print(f"\n  Created the admin account. Username: admin  Password: {password}\n"
                  "  Change it in Settings → Change Password after signing in.\n", flush=True)
    return users


def validate_password(password: str, username: str | None = None) -> str | None:
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters long"
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"Password must be at most {MAX_PASSWORD_LENGTH} characters long"
    if username and username.lower() in password.lower():
        return "Password must not contain your username"
    if password.lower() in _COMMON_PASSWORDS:
        return "That password is too common. Choose another"
    return None


_COMMON_PASSWORDS = {
    "1234567890", "12345678910", "0123456789", "0987654321", "1111111111", "qwertyuiop",
    "password12", "password123", "password1!", "passw0rd123", "iloveyou12", "admin12345",
    "administrator", "letmein123", "welcome123", "qwerty1234", "qwerty12345", "abcdefghij",
    "abc1234567", "1q2w3e4r5t", "1qaz2wsx3edc", "changeme123", "portfolio1", "portfolio123",
}


def check_password(user: dict | None, password: str) -> bool:
    """Constant-time password check that also behaves the same for missing accounts."""
    if not user:
        _verify_password(password, _DUMMY_HASH)
        return False
    return _verify_password(password, user["password_hash"])


def authenticate(username: str, password: str) -> dict | None:
    users = load_users()
    user = users.get(username)
    if not check_password(user, password):
        return None
    if _needs_rehash(user["password_hash"]):
        user["password_hash"] = _hash_password(password)
    user["last_login"] = datetime.now().isoformat()
    save_json(_users_path(), users)
    return {"username": username, "role": user.get("role", "user")}


def normalize_email(email: str | None) -> str | None:
    """Validate and lower-case an email; empty means "no email"."""
    email = (email or "").strip().lower()
    if not email:
        return None
    if not _EMAIL_RE.match(email) or len(email) > 254:
        raise ValueError("Enter a valid email address")
    return email


def _check_email_free(users: dict, email: str | None, owner: str | None = None) -> None:
    if email and any(u.get("email") == email for name, u in users.items() if name != owner):
        raise ValueError("That email is already linked to another account")


def create_user(username: str, password: str, role: str = "user", email: str | None = None) -> None:
    username = username.strip()
    if not username or not username.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Username may only contain letters, numbers, '-' and '_'")
    if len(username) > 32:
        raise ValueError("Username must be at most 32 characters long")
    error = validate_password(password, username)
    if error:
        raise ValueError(error)
    users = load_users()
    if username.lower() in (name.lower() for name in users):
        raise ValueError("Username already exists")
    email = normalize_email(email)
    _check_email_free(users, email)
    users[username] = {
        "password_hash": _hash_password(password),
        "role": role,
        "email": email,
        "created_at": datetime.now().isoformat(),
        "last_login": None,
    }
    save_json(_users_path(), users)


def change_password(username: str, current: str, new: str) -> None:
    users = load_users()
    user = users.get(username)
    if not check_password(user, current):
        raise ValueError("Current password is incorrect")
    if current == new:
        raise ValueError("New password must be different from current password")
    error = validate_password(new, username)
    if error:
        raise ValueError(error)
    _set_password(user, new)
    save_json(_users_path(), users)


def _set_password(user: dict, password: str) -> None:
    """Store a new password and sign out every existing session for the account."""
    user["password_hash"] = _hash_password(password)
    user["session_version"] = user.get("session_version", 0) + 1


def set_email(username: str, email: str | None, current_password: str | None = None) -> str | None:
    """Link (or with an empty value, unlink) an email. Requires the password when given."""
    users = load_users()
    user = users.get(username)
    if not user:
        raise ValueError("User not found")
    if current_password is not None and not check_password(user, current_password):
        raise ValueError("Current password is incorrect")
    email = normalize_email(email)
    _check_email_free(users, email, owner=username)
    user["email"] = email
    save_json(_users_path(), users)
    return email


def get_email(username: str) -> str | None:
    return load_users().get(username, {}).get("email")


# ── Password reset ───────────────────────────────────────────────────────────
# Tokens are signed, expire after RESET_MAX_AGE, and embed a fingerprint of the
# current password hash, so a link stops working as soon as it has been used
# (or the password changes any other way). Nothing needs to be stored.

def _fingerprint(user: dict) -> str:
    return hmac.new(_SECRET.encode(), user["password_hash"].encode(), hashlib.sha256).hexdigest()[:20]


def find_user(identifier: str) -> tuple[str, dict] | None:
    """Look an account up by username, or by linked email (case-insensitive)."""
    identifier = identifier.strip()
    users = load_users()
    if identifier in users:
        return identifier, users[identifier]
    lowered = identifier.lower()
    for name, info in users.items():
        if info.get("email") and info["email"] == lowered:
            return name, info
    return None


def make_reset_token(username: str) -> str:
    user = load_users()[username]
    return _reset_serializer.dumps({"u": username, "f": _fingerprint(user)})


def _verify_reset_token(token: str) -> tuple[str, dict, dict]:
    try:
        payload = _reset_serializer.loads(token, max_age=RESET_MAX_AGE)
    except SignatureExpired:
        raise ValueError("This reset link has expired. Request a new one.")
    except BadSignature:
        raise ValueError("This reset link is invalid.")
    users = load_users()
    user = users.get(payload.get("u"))
    if not user or not hmac.compare_digest(payload.get("f", ""), _fingerprint(user)):
        raise ValueError("This reset link has already been used. Request a new one.")
    return payload["u"], user, users


def check_reset_token(token: str) -> str:
    return _verify_reset_token(token)[0]


def reset_password(token: str, new_password: str) -> str:
    username, user, users = _verify_reset_token(token)
    error = validate_password(new_password, username)
    if error:
        raise ValueError(error)
    _set_password(user, new_password)
    save_json(_users_path(), users)
    return username


def list_users() -> list[dict]:
    return [
        {
            "username": name,
            "role": info.get("role", "user"),
            "email": info.get("email"),
            "created_at": info.get("created_at"),
            "last_login": info.get("last_login"),
        }
        for name, info in load_users().items()
    ]


# ── Sessions ─────────────────────────────────────────────────────────────────

def _cookie_secure(request: Request) -> bool:
    """Secure-only cookies when COOKIE_SECURE=1, or (unless it's 0) whenever the site is on HTTPS."""
    setting = os.getenv("COOKIE_SECURE")
    if setting in ("0", "1"):
        return setting == "1"
    return request.headers.get("x-forwarded-proto", request.url.scheme) == "https"


def set_session(request: Request, response: Response, username: str) -> None:
    version = load_users().get(username, {}).get("session_version", 0)
    token = _serializer.dumps({"u": username, "v": version})
    response.set_cookie(
        SESSION_COOKIE, token, max_age=SESSION_MAX_AGE,
        httponly=True, samesite="lax", secure=_cookie_secure(request), path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


def current_user(request: Request) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(401, "Not signed in")
    try:
        payload = _serializer.loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        raise HTTPException(401, "Session expired")
    user = load_users().get(payload.get("u"))
    if not user:
        raise HTTPException(401, "Account no longer exists")
    if payload.get("v", 0) != user.get("session_version", 0):
        raise HTTPException(401, "Signed out because the password was changed")
    return {"username": payload["u"], "role": user.get("role", "user"), "email": user.get("email")}


def admin_user(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Admin privileges required")
    return user
