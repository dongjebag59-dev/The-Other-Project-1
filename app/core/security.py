import re
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_SPECIAL_CHARS = re.compile(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?]')


def hash_password(password: str) -> str:
    """비밀번호를 해싱합니다."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """비밀번호를 검증합니다."""
    return pwd_context.verify(plain, hashed)


def validate_password_complexity(password: str) -> str:
    """비밀번호 복잡도를 검증합니다 (8자 이상, 숫자 1개 이상, 특수문자 1개 이상)."""
    if len(password) < 8:
        raise ValueError("비밀번호는 8자 이상이어야 합니다.")
    if not re.search(r'\d', password):
        raise ValueError("비밀번호에 숫자가 포함되어야 합니다.")
    if not _SPECIAL_CHARS.search(password):
        raise ValueError("비밀번호에 특수문자가 포함되어야 합니다.")
    return password


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """JWT 액세스 토큰을 생성합니다."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """JWT 리프레시 토큰을 생성합니다 (type='refresh')."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """JWT 토큰을 디코딩합니다. 실패 시 None을 반환합니다."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None
