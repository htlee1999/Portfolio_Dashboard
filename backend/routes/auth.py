import os
import threading
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .. import auth, mailer, ratelimit

router = APIRouter(prefix="/api/auth", tags=["auth"])

# One reset request per account per minute, so the endpoint can't be used to spam inboxes.
_RESET_COOLDOWN = 60
_last_reset: dict[str, float] = {}
_reset_lock = threading.Lock()


# Failed password checks: per account from one IP, and per IP across all accounts.
_FAIL_WINDOW = 15 * 60
_FAILS_PER_ACCOUNT = 5
_FAILS_PER_IP = 30
# Account creation per IP.
_SIGNUP_WINDOW = 60 * 60
_SIGNUPS_PER_IP = 5


class Credentials(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=256)


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=256)
    new_password: str = Field(max_length=256)


class ForgotIn(BaseModel):
    identifier: str = Field(min_length=1, max_length=254, description="Username or linked email")


class ResetIn(BaseModel):
    token: str = Field(max_length=512)
    new_password: str = Field(max_length=256)


class EmailIn(BaseModel):
    email: str | None = Field(default=None, max_length=254)
    current_password: str = Field(max_length=256)


def _guard_password_check(request: Request, username: str) -> tuple[str, str]:
    """Refuse further password attempts once an account or IP has failed too often."""
    ip = ratelimit.client_ip(request)
    keys = (f"fail:{username.lower()}:{ip}", f"fail-ip:{ip}")
    ratelimit.check(keys[0], _FAILS_PER_ACCOUNT, _FAIL_WINDOW)
    ratelimit.check(keys[1], _FAILS_PER_IP, _FAIL_WINDOW)
    return keys


def _record_failure(keys: tuple[str, str]) -> None:
    for key in keys:
        ratelimit.hit(key)


@router.post("/login")
def login(body: Credentials, request: Request, response: Response):
    username = body.username.strip()
    keys = _guard_password_check(request, username)
    user = auth.authenticate(username, body.password)
    if not user:
        _record_failure(keys)
        raise HTTPException(401, "Invalid username or password")
    ratelimit.reset(keys[0])
    auth.set_session(request, response, user["username"])
    return user


@router.post("/signup")
def signup(body: Credentials, request: Request, response: Response):
    if os.getenv("ALLOW_SIGNUP", "1") == "0":
        raise HTTPException(403, "Sign-up is closed. Ask an admin for an account.")
    key = f"signup:{ratelimit.client_ip(request)}"
    ratelimit.check(key, _SIGNUPS_PER_IP, _SIGNUP_WINDOW)
    try:
        auth.create_user(body.username, body.password)
    except ValueError as e:
        raise HTTPException(400, str(e))
    ratelimit.hit(key)
    username = body.username.strip()
    auth.set_session(request, response, username)
    return {"username": username, "role": "user"}


@router.post("/logout")
def logout(response: Response):
    auth.clear_session(response)
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(auth.current_user)):
    return user


@router.post("/password")
def change_password(body: PasswordChange, request: Request, response: Response,
                    user: dict = Depends(auth.current_user)):
    keys = _guard_password_check(request, user["username"])
    try:
        auth.change_password(user["username"], body.current_password, body.new_password)
    except ValueError as e:
        if str(e) == "Current password is incorrect":
            _record_failure(keys)
        raise HTTPException(400, str(e))
    # Changing the password signs out other sessions; keep this one signed in.
    auth.set_session(request, response, user["username"])
    return {"ok": True}


@router.put("/email")
def update_email(body: EmailIn, request: Request, user: dict = Depends(auth.current_user)):
    keys = _guard_password_check(request, user["username"])
    try:
        email = auth.set_email(user["username"], body.email, body.current_password)
    except ValueError as e:
        if str(e) == "Current password is incorrect":
            _record_failure(keys)
        raise HTTPException(400, str(e))
    return {"email": email}


@router.post("/forgot")
def forgot_password(body: ForgotIn, request: Request):
    """Start a password reset. The response is the same whether or not the account exists."""
    key = f"forgot:{ratelimit.client_ip(request)}"
    ratelimit.check(key, 10, 60 * 60)
    ratelimit.hit(key)
    found = auth.find_user(body.identifier)
    if found:
        username, info = found
        with _reset_lock:
            recent = time.time() - _last_reset.get(username, 0) < _RESET_COOLDOWN
            if not recent:
                _last_reset[username] = time.time()
        if not recent:
            link = f"{mailer.app_url()}/reset?token={auth.make_reset_token(username)}"
            mailer.send_password_reset(username, info.get("email"), link, auth.RESET_MAX_AGE // 60)
    return {"ok": True, "email_enabled": mailer.smtp_configured()}


@router.get("/reset")
def check_reset(token: str):
    try:
        return {"username": auth.check_reset_token(token)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/reset")
def reset_password(body: ResetIn):
    try:
        username = auth.reset_password(body.token, body.new_password)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"username": username}
