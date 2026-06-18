"""유저 인증 의존성."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db
from app.domain.user.models import CertFlag, User, UserRole
from app.domain.user.service import get_user_with_address

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """JWT 토큰에서 현재 유저 추출"""

    # 401 에러시 공통으로 반환하는 예외 객체
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="유효하지 않은 토큰입니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise credentials_exception
    # kakao_setup 등 특수 토큰은 일반 인증에 사용 불가
    if payload.get("type") is not None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # sub 값을 정수로 방어, 정수가 아닌 경우: 401 에러
    try:
        user_id_int = int(user_id)
    except ValueError:
        raise credentials_exception

    user = await get_user_with_address(user_id_int, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유저를 찾을 수 없습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_password_reset_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """password_reset 토큰 전용 의존성 (일반 로그인 토큰으로는 접근 불가)"""
    # 비밀번호 찾기 전용 토큰으로 토큰의 주인 유저 꺼내주는 함수
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="유효하지 않은 토큰입니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(credentials.credentials)
    if payload is None or payload.get("type") != "password_reset":
        raise invalid

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise invalid

    user = await get_user_with_address(user_id, db)
    if user is None:
        raise invalid
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """관리자 권한 확인(관리자만 접근 가능)"""
    if current_user.user_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자만 접근할 수 있습니다.",
        )
    return current_user


async def require_guardian(current_user: User = Depends(get_current_user)) -> User:
    """보호자 권한 확인(보호자만 접근 가능)"""
    if current_user.user_role != UserRole.GUARDIAN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="보호자만 접근할 수 있습니다.",
        )
    return current_user


async def require_volunteer(current_user: User = Depends(get_current_user)) -> User:
    """승인된 봉사자 권한 확인(cert_flag approved 필수)"""
    if current_user.user_role != UserRole.VOLUNTEER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="봉사자만 접근할 수 있습니다.",
        )
    if current_user.cert_flag != CertFlag.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="승인된 봉사자만 접근할 수 있습니다.",
        )
    return current_user
