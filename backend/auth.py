import hashlib
import hmac
import os
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Literal, Optional

import bcrypt
import jwt
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from pymongo.errors import DuplicateKeyError

from database import otps, users

load_dotenv()

router = APIRouter(prefix="/auth", tags=["auth"])

bearer = HTTPBearer(auto_error=False)

JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-secret")

JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

SMTP_USER = os.getenv("SMTP_USER", "").strip().strip("\"'")

SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip("\"'")

OTP_MINUTES = 10

OTP_MAX_ATTEMPTS = 5

OTP_RESEND_SECONDS = 30

print(
    "Email sending:",
    "ON" if SMTP_USER and SMTP_PASSWORD else "OFF - dev mode, codes print here"
)


# ---------------------------------------------------------
# request models
# ---------------------------------------------------------

class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=30,
        pattern=r"^[A-Za-z0-9\_.]+$"
    )

    email: str = Field(
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )

    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    username: str
    password: str


class PasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class AccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    username: str = Field(min_length=3, max_length=80)

    email: str = Field(
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    )


class VerifyIn(BaseModel):
    email: str
    code: str = Field(min_length=6, max_length=6)


class ResendIn(BaseModel):
    email: str
    purpose: Literal["signup", "reset"]


class ForgotIn(BaseModel):
    email: str


class ResetIn(BaseModel):
    email: str
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8, max_length=128)


# ---------------------------------------------------------
# helpers
# ---------------------------------------------------------

def _now():
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    """MongoDB returns naive UTC datetimes; make them timezone-aware."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _public(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "username": user["username"],
        "email": user["email"],
    }


def _token(user_id: str) -> str:
    exp = _now() + timedelta(hours=JWT_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": user_id, "exp": exp},
        JWT_SECRET,
        algorithm="HS256"
    )


def _hash_pw(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())


def _check(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hashed)


def _unique_username(base: str) -> str:
    username, n = base, 1

    while users.find_one({"username": username}):
        n += 1
        username = f"{base} {n}"

    return username


def _send_email(to: str, subject: str, body: str) -> None:

    # Not configured yet? Print the code in the backend terminal so you can still test.
    if not (SMTP_USER and SMTP_PASSWORD):
        print(
            f"\n[DEV MODE - SMTP not set] To: {to}\n"
            f"{subject}\n"
            f"{body}\n"
        )
        return

    msg = EmailMessage()

    msg["From"] = f"FinGuide <{SMTP_USER}>"

    msg["To"] = to

    msg["Subject"] = subject

    msg.set_content(body)

    try:
        with smtplib.SMTP(
            "smtp.gmail.com",
            587,
            timeout=20
        ) as s:

            s.ehlo()

            s.starttls(
                context=ssl.create_default_context()
            )

            s.ehlo()

            s.login(
                SMTP_USER,
                SMTP_PASSWORD
            )

            s.send_message(msg)

        print(f"EMAIL SENT successfully to {to}")

    except smtplib.SMTPAuthenticationError as e:

        print(
            "EMAIL ERROR (Gmail refused the login):",
            repr(e)
        )

        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Gmail refused the login. Check SMTP_USER and the app password in backend/.env, then restart the backend.",
        )

    except Exception as e:

        print(
            "EMAIL ERROR:",
            repr(e)
        )

        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "Couldn't reach Gmail. Check your internet connection and try again.",
        )


def _hash_code(email: str, purpose: str, code: str) -> str:
    return hmac.new(
        JWT_SECRET.encode(),
        f"{email}:{purpose}:{code}".encode(),
        hashlib.sha256
    ).hexdigest()


def _issue_otp(
    email: str,
    purpose: str,
    pending: Optional[dict] = None
) -> None:

    """Create a 6-digit code, store only its hash, and email it."""

    now = _now()

    old = otps.find_one({
        "email": email,
        "purpose": purpose
    })

    if old and (
        now - _aware(old["created_at"])
    ).total_seconds() < OTP_RESEND_SECONDS:

        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Please wait a few seconds before requesting another code."
        )

    code = f"{secrets.randbelow(1_000_000):06d}"

    result = otps.update_one(
        
        {
            "email": email,
            "purpose": purpose
        },
        {
            "$set": {
                "code_hash": _hash_code(
                    email,
                    purpose,
                    code
                ),
                "attempts": 0,
                "created_at": now,
                "expires_at": now + timedelta(
                    minutes=OTP_MINUTES
                ),
                "pending": pending,
            }
        },
        upsert=True,
    )
    print(
    "OTP DB RESULT:",
    "matched =", result.matched_count,
    "modified =", result.modified_count,
    "upserted =", result.upserted_id
)
    what = (
        "verify your email"
        if purpose == "signup"
        else "reset your password"
    )

    try:

        _send_email(
            email,
            f"Your FinGuide code: {code}",
            f"Use this code to {what}:\n\n    {code}\n\n"
            f"It expires in {OTP_MINUTES} minutes. "
            f"If you didn't ask for this, you can ignore this email.",
        )

    except HTTPException:

        otps.delete_one({
            "email": email,
            "purpose": purpose
        })

        raise


def _check_otp(
    email: str,
    purpose: str,
    code: str
) -> dict:

    doc = otps.find_one({
        "email": email,
        "purpose": purpose
    })

    if not doc or _aware(doc["expires_at"]) < _now():

        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "That code has expired. Please request a new one."
        )

    if doc["attempts"] >= OTP_MAX_ATTEMPTS:

        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many wrong attempts. Please request a new code."
        )

    if not hmac.compare_digest(
        doc["code_hash"],
        _hash_code(email, purpose, code)
    ):

        otps.update_one(
            {"_id": doc["_id"]},
            {"$inc": {"attempts": 1}}
        )

        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Incorrect code. Please try again."
        )

    return doc


def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer)
) -> dict:

    if not creds:

        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Not authenticated"
        )

    try:

        user_id = jwt.decode(
            creds.credentials,
            JWT_SECRET,
            algorithms=["HS256"]
        )["sub"]

        user = users.find_one({
            "_id": ObjectId(user_id)
        })

    except Exception:

        user = None

    if not user:

        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Session expired. Please log in again."
        )

    return user


# ---------------------------------------------------------
# sign up with email verification (new users only)
# ---------------------------------------------------------

@router.post("/signup")
def signup(body: SignupIn):

    """Step 1: check the details and email a code. The account is only
    created after the code is verified."""

    email = body.email.lower()

    if users.find_one({"email": email}):

        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "An account with this email already exists."
        )

    pending = {
        "name": body.name.strip(),
        "username": (body.username or body.name).strip(),
        "password_hash": _hash_pw(body.password),
    }

    _issue_otp(
        email,
        "signup",
        pending
    )

    return {
        "verify": True,
        "email": email
    }


@router.post("/verify-signup", status_code=201)
def verify_signup(body: VerifyIn):

    """Step 2: right code -> create the verified account and log in."""

    email = body.email.strip().lower()

    doc = _check_otp(
        email,
        "signup",
        body.code
    )

    p = doc["pending"]

    user = {
        "name": p["name"],
        "username": _unique_username(p["username"]),
        "email": email,
        "password_hash": p["password_hash"],
        "verified": True,
        "created_at": _now(),
    }

    try:

        user["_id"] = users.insert_one(user).inserted_id

    except DuplicateKeyError:

        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "An account with this email already exists."
        )

    otps.delete_one({
        "_id": doc["_id"]
    })

    return {
        "token": _token(str(user["_id"])),
        "user": _public(user)
    }


# ---------------------------------------------------------
# forgot password
# ---------------------------------------------------------

def _send_reset_code(email: str) -> None:

    # same response whether or not the email exists, so accounts can't be probed
    if users.find_one({"email": email}):

        _issue_otp(
            email,
            "reset"
        )


@router.post("/forgot-password")
def forgot_password(body: ForgotIn):

    _send_reset_code(
        body.email.strip().lower()
    )

    return {"ok": True}


@router.post("/reset-password")
def reset_password(body: ResetIn):

    email = body.email.strip().lower()

    doc = _check_otp(
        email,
        "reset",
        body.code
    )

    users.update_one(
        {"email": email},
        {
            "$set": {
                "password_hash": _hash_pw(
                    body.new_password
                )
            }
        }
    )

    otps.delete_one({
        "_id": doc["_id"]
    })

    return {"ok": True}


@router.post("/resend-otp")
def resend_otp(body: ResendIn):

    email = body.email.strip().lower()

    if body.purpose == "signup":

        old = otps.find_one({
            "email": email,
            "purpose": "signup"
        })

        if not old:

            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Please sign up again."
            )

        _issue_otp(
            email,
            "signup",
            old["pending"]
        )

    else:

        _send_reset_code(email)

    return {"ok": True}


# ---------------------------------------------------------
# login + account
# ---------------------------------------------------------

@router.post("/login")
def login(body: LoginIn):

    ident = body.username.strip()

    user = users.find_one({
        "$or": [
            {"email": ident.lower()},
            {"username": ident}
        ]
    })

    if not user or not _check(
        body.password,
        user["password_hash"]
    ):

        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password."
        )

    return {
        "token": _token(str(user["_id"])),
        "user": _public(user)
    }


@router.get("/me")
def me(
    user: dict = Depends(get_current_user)
):

    return _public(user)


@router.put("/me")
def update_me(
    body: AccountIn,
    user: dict = Depends(get_current_user)
):

    try:

        users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "name": body.name.strip(),
                    "username": body.username.strip(),
                }
            },
        )

    except DuplicateKeyError:

        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Username already in use."
        )

    return _public(
        users.find_one({
            "_id": user["_id"]
        })
    )


@router.put("/password")
def change_password(
    body: PasswordIn,
    user: dict = Depends(get_current_user)
):

    if not _check(
        body.current_password,
        user["password_hash"]
    ):

        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Current password is incorrect."
        )

    users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password_hash": _hash_pw(
                    user["current_password"]
                )
            }
        }
    )

    return {"ok": True}