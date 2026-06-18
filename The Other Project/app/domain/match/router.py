"""매칭 API 엔드포인트."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.match import service
from app.domain.match.schemas import (
    MatchCreateRequest,
    MatchResponse,
    MyMatchCheckResponse,
    MyMatchListResponse,
)
from app.domain.user.dependency import require_volunteer
from app.domain.user.models import User

router = APIRouter()


@router.post(
    "/",
    response_model=MatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_match(
    request: MatchCreateRequest,
    current_user: User = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
) -> MatchResponse:
    """호스팅에 매칭을 신청합니다."""

    return await service.create_match(
        db=db,
        hosting_id=request.hosting_id,
        vt_id=current_user.user_id,
    )


@router.get(
    "/my/check",
    response_model=MyMatchCheckResponse,
    status_code=status.HTTP_200_OK,
)
async def check_my_match(
    hosting_id: int,
    current_user: User = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
) -> MyMatchCheckResponse:
    """내가 특정 호스팅에 신청했는지 확인합니다."""

    return await service.check_my_match(
        db=db,
        hosting_id=hosting_id,
        vt_id=current_user.user_id,
    )


@router.get(
    "/my",
    response_model=MyMatchListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_my_matches(
    is_completed: bool,
    page: int = 1,
    size: int = 10,
    current_user: User = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
) -> MyMatchListResponse:
    """내 매칭 목록을 예정/완료 구분하여 조회합니다."""

    return await service.list_matches_by_volunteer(
        db=db,
        vt_id=current_user.user_id,
        is_completed=is_completed,
        page=page,
        size=size,
    )


@router.patch(
    "/{matching_id}/cancel",
    response_model=MatchResponse,
    status_code=status.HTTP_200_OK,
)
async def cancel_match(
    matching_id: int,
    current_user: User = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
) -> MatchResponse:
    """매칭을 취소합니다."""

    return await service.cancel_match(
        db=db,
        matching_id=matching_id,
        vt_id=current_user.user_id,
    )


@router.patch(
    "/{senior_id}/checkin",
    response_model=MatchResponse,
    status_code=status.HTTP_200_OK,
)
async def check_in(
    senior_id: int,
    current_user: User = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
) -> MatchResponse:
    """QR 체크인합니다."""

    return await service.check_in(
        db=db,
        senior_id=senior_id,
        vt_id=current_user.user_id,
    )


@router.patch(
    "/{senior_id}/checkout",
    response_model=MatchResponse,
    status_code=status.HTTP_200_OK,
)
async def check_out(
    senior_id: int,
    current_user: User = Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
) -> MatchResponse:
    """QR 체크아웃합니다."""

    return await service.check_out(
        db=db,
        senior_id=senior_id,
        vt_id=current_user.user_id,
    )
