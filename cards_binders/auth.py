#!/usr/bin/env python3
"""
Authentication module for user login and session management.
"""

import hashlib
import secrets
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import database

# Session secret key - in production, this should be in environment variable
SECRET_KEY = secrets.token_urlsafe(32)
SESSION_COOKIE_NAME = "session_token"
SESSION_MAX_AGE = 86400 * 30  # 30 days

# Create serializer for signing session tokens
serializer = URLSafeTimedSerializer(SECRET_KEY)


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash."""
    try:
        salt, stored_hash = password_hash.split(":", 1)
        computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return computed_hash == stored_hash
    except ValueError:
        return False


def create_session_token(user_id: int) -> str:
    """Create a signed session token for a user."""
    return serializer.dumps({"user_id": user_id})


def verify_session_token(token: str) -> Optional[int]:
    """Verify a session token and return user_id if valid."""
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None


def get_current_user(request: Request) -> Optional[int]:
    """Get current user ID from session cookie. Returns None if not logged in."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None
    return verify_session_token(token)


async def get_current_user_dependency(request: Request) -> Optional[int]:
    """Dependency for FastAPI endpoints to get current user."""
    return get_current_user(request)


# Authentication endpoints will be added to collection_ui.py
