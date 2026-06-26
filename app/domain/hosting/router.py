"""호스팅 API 라우터."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.hosting.schemas import (
    HostingCreateRequest,
    HostingListResponse,
    HostingResponse,
    HostingUpdateRequest,
)
from app.domain.hosting.service import (
    cancel_hosting,
    create_hosting,
    get_hosting_detail,
    get_public_hosting_detail,
    list_hostings_by_guardian,
    list_hostings_for_volunteer,
    update_hosting,
)
from app.domain.user.dependency import (
    get_current_user,
    require_guardian,
    require_volunteer,
)
from app.domain.user.models import CertFlag, User, UserRole

router = APIRouter()


@router.post(
    "/",
    response_model=HostingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_hosting_endpoint(
    request: HostingCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_guardian=Depends(require_guardian),
) -> HostingResponse:
    """호스팅을 등록합니다."""

    return await create_hosting(
        session=session,
        guardian_id=current_guardian.user_id,
        request=request,
    )


@router.get(
    "/",
    response_model=list[HostingResponse],
    status_code=status.HTTP_200_OK,
)
async def list_hostings_endpoint(
    session: AsyncSession = Depends(get_db),
    current_guardian=Depends(require_guardian),
) -> list[HostingResponse]:
    """보호자의 호스팅 목록을 조회합니다."""

    return await list_hostings_by_guardian(
        session=session,
        guardian_id=current_guardian.user_id,
    )


@router.get(
    "/public",
    response_model=HostingListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_public_hostings_endpoint(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    sido: str | None = Query(default=None),
    sigungu: str | None = Query(default=None),
    hosting_date: date | None = Query(default=None, alias="date"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HostingListResponse:
    """승인된 봉사자 또는 관리자가 탐색 가능한 공개 호스팅 목록을 조회합니다."""

    is_approved_volunteer = (
        current_user.user_role == UserRole.VOLUNTEER
        and current_user.cert_flag == CertFlag.APPROVED
    )
    if current_user.user_role != UserRole.ADMIN and not is_approved_volunteer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="승인된 봉사자만 호스팅을 탐색할 수 있습니다.",
        )

    return await list_hostings_for_volunteer(
        session=session,
        page=page,
        size=size,
        sido=sido,
        sigungu=sigungu,
        hosting_date=hosting_date,
    )


@router.get(
    "/public/{hosting_id}",
    response_model=HostingResponse,
    status_code=status.HTTP_200_OK,
)
async def get_public_hosting_detail_endpoint(
    hosting_id: int,
    session: AsyncSession = Depends(get_db),
    current_volunteer: User = Depends(require_volunteer),
) -> HostingResponse:
    """승인된 봉사자가 조회 가능한 공개 호스팅 상세 정보를 조회합니다."""

    return await get_public_hosting_detail(
        session=session,
        hosting_id=hosting_id,
        volunteer_id=current_volunteer.user_id,
    )


@router.get(
    "/{hosting_id}",
    response_model=HostingResponse,
    status_code=status.HTTP_200_OK,
)
async def get_hosting_detail_endpoint(
    hosting_id: int,
    session: AsyncSession = Depends(get_db),
    current_guardian=Depends(require_guardian),
) -> HostingResponse:
    """보호자의 호스팅 상세 정보를 조회합니다."""

    return await get_hosting_detail(
        session=session,
        guardian_id=current_guardian.user_id,
        hosting_id=hosting_id,
    )


@router.patch(
    "/{hosting_id}",
    response_model=HostingResponse,
    status_code=status.HTTP_200_OK,
)
async def update_hosting_endpoint(
    hosting_id: int,
    request: HostingUpdateRequest,
    session: AsyncSession = Depends(get_db),
    current_guardian=Depends(require_guardian),
) -> HostingResponse:
    """호스팅 정보를 수정합니다 (메뉴, 최대 인원)."""

    return await update_hosting(
        session=session,
        guardian_id=current_guardian.user_id,
        hosting_id=hosting_id,
        request=request,
    )


@router.patch(
    "/{hosting_id}/cancel",
    response_model=HostingResponse,
    status_code=status.HTTP_200_OK,
)
async def cancel_hosting_endpoint(
    hosting_id: int,
    session: AsyncSession = Depends(get_db),
    current_guardian=Depends(require_guardian),
) -> HostingResponse:
    """호스팅을 취소 처리합니다."""

    return await cancel_hosting(
        session=session,
        guardian_id=current_guardian.user_id,
        hosting_id=hosting_id,
    )
