"""어르신 CRUD 로직."""

import asyncio
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.common.models import Address
from app.domain.hosting.models import Hosting, HostingStatus
from app.domain.match.models import MatchingInfo
from app.domain.review.models import Review, ReviewImg
from app.domain.senior.models import Senior
from app.domain.senior.schemas import (
    GuardianStatsResponse,
    SeniorCreateRequest,
    SeniorResponse,
    SeniorUpdateRequest,
)
from app.services.r2 import delete_image

HostingCountMap = dict[str, int]

BLOCKING_HOSTING_STATUSES_FOR_DEACTIVATION = (
    HostingStatus.OPEN,
    HostingStatus.FULL,
    HostingStatus.FIXED,
    HostingStatus.IN_PROGRESS,
)

CANCELLABLE_HOSTING_STATUSES_BEFORE_SENIOR_DELETE = {
    HostingStatus.OPEN,
    HostingStatus.FULL,
}

ADMIN_CONTACT_HOSTING_STATUSES = {
    HostingStatus.FIXED,
    HostingStatus.IN_PROGRESS,
}

BLOCKING_HOSTING_STATUSES_FOR_UPDATE = {
    HostingStatus.OPEN,
    HostingStatus.FULL,
    HostingStatus.FIXED,
    HostingStatus.IN_PROGRESS,
}


def build_senior_response(
    senior: Senior,
    hosting_counts: HostingCountMap | None = None,
) -> SeniorResponse:
    """어르신 응답 데이터를 생성합니다."""

    counts = hosting_counts or {}
    response = SeniorResponse.model_validate(senior)
    response.total_hosting_count = counts.get("total", 0)
    response.open_hosting_count = counts.get("open", 0)
    response.full_hosting_count = counts.get("full", 0)
    response.fixed_hosting_count = counts.get("fixed", 0)
    response.in_progress_hosting_count = counts.get("in_progress", 0)
    response.closed_hosting_count = counts.get("closed", 0)
    response.failed_hosting_count = counts.get("failed", 0)
    return response


async def get_hosting_counts_by_senior(
    session: AsyncSession,
    senior_id: int,
) -> HostingCountMap:
    """어르신 1명의 호스팅 상태별 집계값을 조회합니다."""

    stmt = select(
        func.count(Hosting.hosting_id).label("total_hosting_count"),
        func.count(Hosting.hosting_id)
        .filter(Hosting.hosting_status == HostingStatus.OPEN)
        .label("open_hosting_count"),
        func.count(Hosting.hosting_id)
        .filter(Hosting.hosting_status == HostingStatus.FULL)
        .label("full_hosting_count"),
        func.count(Hosting.hosting_id)
        .filter(Hosting.hosting_status == HostingStatus.FIXED)
        .label("fixed_hosting_count"),
        func.count(Hosting.hosting_id)
        .filter(Hosting.hosting_status == HostingStatus.IN_PROGRESS)
        .label("in_progress_hosting_count"),
        func.count(Hosting.hosting_id)
        .filter(Hosting.hosting_status == HostingStatus.CLOSED)
        .label("closed_hosting_count"),
        func.count(Hosting.hosting_id)
        .filter(Hosting.hosting_status == HostingStatus.FAILED)
        .label("failed_hosting_count"),
    ).where(Hosting.senior_id == senior_id)

    result = await session.execute(stmt)
    row = result.one()

    return {
        "total": row.total_hosting_count or 0,
        "open": row.open_hosting_count or 0,
        "full": row.full_hosting_count or 0,
        "fixed": row.fixed_hosting_count or 0,
        "in_progress": row.in_progress_hosting_count or 0,
        "closed": row.closed_hosting_count or 0,
        "failed": row.failed_hosting_count or 0,
    }


async def get_blocking_hosting_statuses_for_senior(
    session: AsyncSession,
    senior_id: int,
) -> set[HostingStatus]:
    """어르신 삭제/비활성화를 막는 호스팅 상태 목록을 조회합니다."""

    stmt = select(Hosting.hosting_status).where(
        Hosting.senior_id == senior_id,
        Hosting.hosting_status.in_(BLOCKING_HOSTING_STATUSES_FOR_DEACTIVATION),
    )

    result = await session.execute(stmt)
    return set(result.scalars().all())


def build_blocking_hosting_message(
    blocking_statuses: set[HostingStatus],
    action_label: str,
) -> str:
    """차단 상태 조합에 맞는 안내 메시지를 생성합니다."""

    has_cancellable_hosting = bool(
        blocking_statuses & CANCELLABLE_HOSTING_STATUSES_BEFORE_SENIOR_DELETE
    )
    has_admin_contact_hosting = bool(blocking_statuses & ADMIN_CONTACT_HOSTING_STATUSES)

    if has_cancellable_hosting and has_admin_contact_hosting:
        return (
            f"{action_label}할 수 없는 호스팅이 연결되어 있습니다. "
            "모집 중/모집완료 호스팅은 먼저 취소하고, "
            "확정/진행 중 호스팅은 관리자에게 문의해 주세요."
        )

    if has_admin_contact_hosting:
        return (
            f"확정 또는 진행 중인 호스팅이 있는 어르신은 {action_label}할 수 없습니다. "
            "변경이 필요하면 관리자에게 문의해 주세요."
        )

    if has_cancellable_hosting:
        return (
            f"진행 전 호스팅이 있는 어르신은 {action_label}할 수 없습니다. "
            "먼저 해당 호스팅을 취소한 뒤 다시 시도해 주세요."
        )

    return f"완료되지 않은 호스팅이 있는 어르신은 {action_label}할 수 없습니다."


async def ensure_senior_has_no_blocking_hostings(
    session: AsyncSession,
    senior_id: int,
    action_label: str,
) -> None:
    """삭제/비활성화를 막는 호스팅이 있으면 예외를 발생시킵니다."""

    blocking_statuses = await get_blocking_hosting_statuses_for_senior(
        session=session,
        senior_id=senior_id,
    )

    if blocking_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=build_blocking_hosting_message(
                blocking_statuses=blocking_statuses,
                action_label=action_label,
            ),
        )


async def ensure_senior_can_be_deactivated(
    session: AsyncSession,
    senior_id: int,
) -> None:
    """완료되지 않은 호스팅이 있으면 어르신 비활성화를 막습니다."""

    await ensure_senior_has_no_blocking_hostings(
        session=session,
        senior_id=senior_id,
        action_label="비활성화",
    )


async def ensure_senior_can_be_updated(
    session: AsyncSession,
    senior_id: int,
) -> None:
    """모집 중/모집완료/확정/진행 중 호스팅이 있으면 어르신 수정을 막습니다."""

    blocking_statuses = await get_blocking_hosting_statuses_for_senior(
        session=session,
        senior_id=senior_id,
    )

    if blocking_statuses & BLOCKING_HOSTING_STATUSES_FOR_UPDATE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "모집 중, 모집완료, 확정 또는 진행 중인 호스팅이 있는 어르신은 수정할 수 없습니다. "
                "해당 호스팅을 취소하거나 관리자에게 문의해 주세요."
            ),
        )


async def _fetch_senior_with_address(
    session: AsyncSession,
    senior_id: int,
) -> Senior:
    """address relationship을 포함해 어르신을 조회하는 내부 헬퍼입니다."""

    result = await session.execute(
        select(Senior)
        .where(Senior.senior_id == senior_id)
        .options(selectinload(Senior.address))
    )
    return result.scalar_one()


async def create_senior(
    session: AsyncSession,
    guardian_id: int,
    request: SeniorCreateRequest,
) -> SeniorResponse:
    """어르신을 등록합니다."""

    address = Address(**request.address.model_dump())
    session.add(address)
    await session.flush()  # address_id 확보

    senior = Senior(
        guardian_id=guardian_id,
        address_id=address.address_id,
        name=request.name,
        gender=request.gender,
        birth_date=request.birth_date,
        special_note=request.special_note,
        active_flag=request.active_flag,
        max_people=request.max_people,
        qr_code=str(uuid.uuid4()),
    )

    session.add(senior)
    await session.commit()

    senior = await _fetch_senior_with_address(session, senior.senior_id)
    hosting_counts = await get_hosting_counts_by_senior(session, senior.senior_id)

    return build_senior_response(senior=senior, hosting_counts=hosting_counts)


async def list_seniors_by_guardian(
    session: AsyncSession,
    guardian_id: int,
    active_only: bool = True,
) -> list[SeniorResponse]:
    """보호자 기준 어르신 목록을 조회합니다."""

    stmt = (
        select(
            Senior,
            func.count(Hosting.hosting_id).label("total_hosting_count"),
            func.count(Hosting.hosting_id)
            .filter(Hosting.hosting_status == HostingStatus.OPEN)
            .label("open_hosting_count"),
            func.count(Hosting.hosting_id)
            .filter(Hosting.hosting_status == HostingStatus.FULL)
            .label("full_hosting_count"),
            func.count(Hosting.hosting_id)
            .filter(Hosting.hosting_status == HostingStatus.FIXED)
            .label("fixed_hosting_count"),
            func.count(Hosting.hosting_id)
            .filter(Hosting.hosting_status == HostingStatus.IN_PROGRESS)
            .label("in_progress_hosting_count"),
            func.count(Hosting.hosting_id)
            .filter(Hosting.hosting_status == HostingStatus.CLOSED)
            .label("closed_hosting_count"),
            func.count(Hosting.hosting_id)
            .filter(Hosting.hosting_status == HostingStatus.FAILED)
            .label("failed_hosting_count"),
        )
        .outerjoin(Hosting, Hosting.senior_id == Senior.senior_id)
        .where(Senior.guardian_id == guardian_id)
        .options(selectinload(Senior.address))
    )

    if active_only:
        stmt = stmt.where(Senior.active_flag.is_(True))

    stmt = stmt.group_by(Senior.senior_id).order_by(Senior.created_at.desc())

    result = await session.execute(stmt)
    rows = result.all()

    return [
        build_senior_response(
            senior=senior,
            hosting_counts={
                "total": total_hosting_count or 0,
                "open": open_hosting_count or 0,
                "full": full_hosting_count or 0,
                "fixed": fixed_hosting_count or 0,
                "in_progress": in_progress_hosting_count or 0,
                "closed": closed_hosting_count or 0,
                "failed": failed_hosting_count or 0,
            },
        )
        for (
            senior,
            total_hosting_count,
            open_hosting_count,
            full_hosting_count,
            fixed_hosting_count,
            in_progress_hosting_count,
            closed_hosting_count,
            failed_hosting_count,
        ) in rows
    ]


async def get_senior_by_id(
    session: AsyncSession,
    senior_id: int,
) -> SeniorResponse:
    """ID로 어르신을 조회합니다."""

    result = await session.execute(
        select(Senior)
        .where(Senior.senior_id == senior_id)
        .options(selectinload(Senior.address))
    )
    senior = result.scalar_one_or_none()

    if senior is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="어르신 정보를 찾을 수 없습니다.",
        )

    hosting_counts = await get_hosting_counts_by_senior(session, senior.senior_id)

    return build_senior_response(senior=senior, hosting_counts=hosting_counts)


async def get_guardian_senior_by_id(
    session: AsyncSession,
    guardian_id: int,
    senior_id: int,
) -> Senior:
    """보호자 소유의 어르신 엔티티를 조회합니다."""

    result = await session.execute(
        select(Senior).where(
            Senior.senior_id == senior_id,
            Senior.guardian_id == guardian_id,
        )
    )
    senior = result.scalar_one_or_none()

    if senior is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 보호자의 어르신 정보를 찾을 수 없습니다.",
        )

    return senior


async def update_senior(
    session: AsyncSession,
    guardian_id: int,
    senior_id: int,
    request: SeniorUpdateRequest,
) -> SeniorResponse:
    """어르신 정보를 수정합니다."""

    senior = await get_guardian_senior_by_id(
        session=session,
        guardian_id=guardian_id,
        senior_id=senior_id,
    )

    update_data = request.model_dump(exclude_unset=True, exclude={"address"})

    await ensure_senior_can_be_updated(session=session, senior_id=senior.senior_id)

    if update_data.get("active_flag") is False:
        await ensure_senior_can_be_deactivated(session=session, senior_id=senior.senior_id)

    for field_name, field_value in update_data.items():
        setattr(senior, field_name, field_value)

    if request.address is not None:
        address = await session.get(Address, senior.address_id)
        for field_name, field_value in request.address.model_dump().items():
            setattr(address, field_name, field_value)

    await session.commit()

    senior = await _fetch_senior_with_address(session, senior_id)
    hosting_counts = await get_hosting_counts_by_senior(session, senior.senior_id)

    return build_senior_response(senior=senior, hosting_counts=hosting_counts)


async def deactivate_senior(
    session: AsyncSession,
    guardian_id: int,
    senior_id: int,
) -> None:
    """어르신 정보를 비활성화합니다."""

    senior = await get_guardian_senior_by_id(
        session=session,
        guardian_id=guardian_id,
        senior_id=senior_id,
    )

    await ensure_senior_can_be_deactivated(session=session, senior_id=senior.senior_id)

    senior.active_flag = False
    await session.commit()


async def activate_senior(
    session: AsyncSession,
    guardian_id: int,
    senior_id: int,
) -> None:
    """어르신 정보를 활성화합니다."""

    senior = await get_guardian_senior_by_id(
        session=session,
        guardian_id=guardian_id,
        senior_id=senior_id,
    )

    senior.active_flag = True
    await session.commit()


async def delete_senior(
    session: AsyncSession,
    guardian_id: int,
    senior_id: int,
) -> None:
    """어르신 정보를 삭제합니다."""

    senior = await get_guardian_senior_by_id(
        session=session,
        guardian_id=guardian_id,
        senior_id=senior_id,
    )

    await ensure_senior_has_no_blocking_hostings(
        session=session,
        senior_id=senior.senior_id,
        action_label="삭제",
    )

    # R2 후기 이미지 먼저 삭제 (senior 삭제 후 CASCADE로 DB는 사라지지만 R2 파일은 안 사라짐)
    img_result = await session.execute(
        select(ReviewImg)
        .join(Review, ReviewImg.review_id == Review.review_id)
        .join(MatchingInfo, Review.matching_id == MatchingInfo.matching_id)
        .where(MatchingInfo.senior_id == senior_id)
    )
    review_imgs = img_result.scalars().all()
    await asyncio.gather(
        *[delete_image(img.image_url) for img in review_imgs], return_exceptions=True
    )

    address_id = senior.address_id
    await session.delete(senior)
    await session.flush()  # senior row 먼저 제거 (hosting.senior_id SET NULL 처리됨)

    address = await session.get(Address, address_id)
    if address:
        await session.delete(address)

    await session.commit()


async def get_senior_id_by_qr(
    session: AsyncSession,
    qr_uuid: str,
) -> int:
    """QR UUID로 senior_id를 역조회합니다."""

    result = await session.execute(
        select(Senior.senior_id).where(Senior.qr_code == qr_uuid)
    )
    senior_id = result.scalar_one_or_none()

    if senior_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="유효하지 않은 QR 코드입니다.",
        )

    return senior_id


async def get_guardian_stats(
    session: AsyncSession,
    guardian_id: int,
) -> GuardianStatsResponse:
    """보호자 마이페이지 통계를 조회합니다."""

    active_statuses = [
        HostingStatus.OPEN,
        HostingStatus.FULL,
        HostingStatus.FIXED,
        HostingStatus.IN_PROGRESS,
    ]

    stmt = (
        select(
            func.count(Senior.senior_id.distinct()).label("senior_count"),
            func.count(Hosting.hosting_id)
            .filter(Hosting.hosting_status.in_(active_statuses))
            .label("active_hosting_count"),
            func.count(Hosting.hosting_id)
            .filter(Hosting.hosting_status == HostingStatus.FAILED)
            .label("cancelled_hosting_count"),
            func.count(Hosting.hosting_id)
            .filter(Hosting.hosting_status == HostingStatus.CLOSED)
            .label("completed_hosting_count"),
        )
        .select_from(Senior)
        .outerjoin(Hosting, Hosting.senior_id == Senior.senior_id)
        .where(Senior.guardian_id == guardian_id, Senior.active_flag.is_(True))
    )

    result = await session.execute(stmt)
    row = result.one()

    return GuardianStatsResponse(
        senior_count=row.senior_count,
        active_hosting_count=row.active_hosting_count,
        cancelled_hosting_count=row.cancelled_hosting_count,
        completed_hosting_count=row.completed_hosting_count,
    )
