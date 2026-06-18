"""어르신 API 라우터."""

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.senior.schemas import (
    SeniorCreateRequest,
    SeniorResponse,
    SeniorUpdateRequest,
)
from app.domain.senior.service import (
    activate_senior,
    create_senior,
    deactivate_senior,
    delete_senior,
    get_guardian_senior_by_id,
    get_senior_by_id,
    get_senior_id_by_qr,
    list_seniors_by_guardian,
    update_senior,
)
from app.domain.user.dependency import require_guardian, require_volunteer
from app.services.qr import build_checkin_url, generate_qr_image

router = APIRouter()


@router.post(
    "/",
    response_model=SeniorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_senior_endpoint(
    request: SeniorCreateRequest,
    session: AsyncSession = Depends(get_db),
    current_guardian=Depends(require_guardian),
) -> SeniorResponse:
    """어르신을 등록합니다."""

    return await create_senior(
        session=session,
        guardian_id=current_guardian.user_id,
        request=request,
    )


@router.get(
    "/",
    response_model=list[SeniorResponse],
    status_code=status.HTTP_200_OK,
)
async def list_seniors_endpoint(
    active_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_db),
    current_guardian=Depends(require_guardian),
) -> list[SeniorResponse]:
    """보호자의 어르신 목록을 조회합니다."""

    return await list_seniors_by_guardian(
        session=session,
        guardian_id=current_guardian.user_id,
        active_only=active_only,
    )


@router.get(
    "/{senior_id}",
    response_model=SeniorResponse,
    status_code=status.HTTP_200_OK,
)
async def get_senior_detail_endpoint(
    senior_id: int,
    session: AsyncSession = Depends(get_db),
    current_guardian=Depends(require_guardian),
) -> SeniorResponse:
    """보호자의 어르신 상세 정보를 조회합니다."""

    await get_guardian_senior_by_id(
        session=session,
        guardian_id=current_guardian.user_id,
        senior_id=senior_id,
    )

    return await get_senior_by_id(
        session=session,
        senior_id=senior_id,
    )


@router.patch(
    "/{senior_id}",
    response_model=SeniorResponse,
    status_code=status.HTTP_200_OK,
)
async def update_senior_endpoint(
    senior_id: int,
    request: SeniorUpdateRequest,
    session: AsyncSession = Depends(get_db),
    current_guardian=Depends(require_guardian),
) -> SeniorResponse:
    """어르신 정보를 수정합니다."""

    return await update_senior(
        session=session,
        guardian_id=current_guardian.user_id,
        senior_id=senior_id,
        request=request,
    )


@router.patch(
    "/{senior_id}/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def deactivate_senior_endpoint(
    senior_id: int,
    session: AsyncSession = Depends(get_db),
    current_guardian=Depends(require_guardian),
) -> Response:
    """어르신 정보를 비활성화합니다."""

    await deactivate_senior(
        session=session,
        guardian_id=current_guardian.user_id,
        senior_id=senior_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/{senior_id}/activate",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def activate_senior_endpoint(
    senior_id: int,
    session: AsyncSession = Depends(get_db),
    current_guardian=Depends(require_guardian),
) -> Response:
    """어르신 정보를 활성화합니다."""

    await activate_senior(
        session=session,
        guardian_id=current_guardian.user_id,
        senior_id=senior_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/qr/{qr_uuid}",
    status_code=status.HTTP_200_OK,
)
async def get_senior_id_by_qr_endpoint(
    qr_uuid: str,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_volunteer),
) -> dict:
    """QR UUID로 senior_id를 반환합니다. 봉사자가 QR 스캔 후 체크인/아웃 API 호출에 활용합니다."""
    senior_id = await get_senior_id_by_qr(session=session, qr_uuid=qr_uuid)
    return {"senior_id": senior_id}


@router.get(
    "/{senior_id}/qr",
    status_code=status.HTTP_200_OK,
)
async def get_senior_qr_endpoint(
    senior_id: int,
    session: AsyncSession = Depends(get_db),
    current_guardian=Depends(require_guardian),
) -> StreamingResponse:
    """어르신 QR 코드 이미지를 반환합니다.

    QR UUID는 어르신 1명당 1개로 고정되며 영구 유효 — 재발급 API는 의도적으로 제공하지 않음.
    Cache-Control: no-store 로 브라우저 캐시만 차단.
    """
    senior = await get_guardian_senior_by_id(
        session=session,
        guardian_id=current_guardian.user_id,
        senior_id=senior_id,
    )

    if not senior.qr_code:
        raise HTTPException(status_code=404, detail="QR 코드가 존재하지 않습니다.")

    checkin_url = build_checkin_url(senior.qr_code)
    image_bytes = await asyncio.to_thread(generate_qr_image, checkin_url)
    return StreamingResponse(
        iter([image_bytes]),
        media_type="image/png",
        headers={
            "Content-Disposition": "inline; filename=qr.png",
            "Cache-Control": "no-store",
        },
    )


@router.delete(
    "/{senior_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_senior_endpoint(
    senior_id: int,
    session: AsyncSession = Depends(get_db),
    current_guardian=Depends(require_guardian),
) -> Response:
    """어르신 정보를 삭제합니다."""

    await delete_senior(
        session=session,
        guardian_id=current_guardian.user_id,
        senior_id=senior_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
