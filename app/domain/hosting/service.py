"""호스팅 비즈니스 로직."""

import asyncio
import logging
from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


from app.domain.common.models import Address
from app.domain.hosting.models import AlarmType, Hosting, HostingStatus
from app.domain.hosting.schemas import (
    HostingCreateRequest,
    HostingListResponse,
    HostingResponse,
    HostingSeniorResponse,
    HostingUpdateRequest,
)
from app.domain.match.models import MatchingInfo, MatchStatus
from app.domain.senior.models import Senior
from app.services.sms import send_sms

logger = logging.getLogger(__name__)
MIN_HOSTING_INTERVAL = timedelta(days=7)
NON_FAILED_HOSTING_STATUSES = (
    HostingStatus.OPEN,
    HostingStatus.FULL,
    HostingStatus.FIXED,
    HostingStatus.IN_PROGRESS,
    HostingStatus.CLOSED,
)


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


async def get_guardian_hosting_by_id(
    session: AsyncSession,
    guardian_id: int,
    hosting_id: int,
) -> Hosting:
    """보호자 소유의 호스팅 엔티티를 조회합니다."""

    stmt = (
        select(Hosting)
        .join(Senior, Senior.senior_id == Hosting.senior_id)
        .where(
            Hosting.hosting_id == hosting_id,
            Senior.guardian_id == guardian_id,
        )
        .options(selectinload(Hosting.address))
    )

    result = await session.execute(stmt)
    hosting = result.scalar_one_or_none()

    if hosting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 보호자의 호스팅 정보를 찾을 수 없습니다.",
        )

    return hosting


async def get_senior_with_address_by_id(
    session: AsyncSession,
    senior_id: int | None,
) -> Senior | None:
    """어르신 주소를 포함해 어르신 정보를 조회합니다."""

    if senior_id is None:
        return None

    result = await session.execute(
        select(Senior)
        .where(Senior.senior_id == senior_id)
        .options(selectinload(Senior.address))
    )
    return result.scalar_one_or_none()


def get_now_utc() -> datetime:
    """현재 UTC 시간을 반환합니다."""

    return datetime.now(timezone.utc)


def ensure_utc_aware(dt: datetime) -> datetime:
    """datetime을 UTC aware 형태로 맞춥니다."""

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def get_current_people_count(
    session: AsyncSession,
    hosting_id: int,
) -> int:
    """호스팅에 승인된 현재 매칭 인원을 조회합니다."""

    result = await session.execute(
        select(func.count(MatchingInfo.matching_id)).where(
            MatchingInfo.hosting_id == hosting_id,
            MatchingInfo.match_status == MatchStatus.APPROVED,
        )
    )

    return result.scalar_one() or 0


async def get_current_people_count_map(
    session: AsyncSession,
    hosting_ids: list[int],
) -> dict[int, int]:
    """호스팅 ID별 승인된 현재 매칭 인원 맵을 조회합니다."""

    if not hosting_ids:
        return {}

    result = await session.execute(
        select(
            MatchingInfo.hosting_id,
            func.count(MatchingInfo.matching_id).label("current_people"),
        )
        .where(
            MatchingInfo.hosting_id.in_(hosting_ids),
            MatchingInfo.match_status == MatchStatus.APPROVED,
        )
        .group_by(MatchingInfo.hosting_id)
    )

    return {hosting_id: current_people for hosting_id, current_people in result.all()}


def build_hosting_response(
    hosting: Hosting,
    current_people: int = 0,
    senior: Senior | None = None,
) -> HostingResponse:
    """현재 모집 인원과 어르신 요약 정보를 포함한 호스팅 응답을 생성합니다."""

    response = HostingResponse.model_validate(hosting)
    response.current_people = current_people

    if senior is not None:
        response.senior = HostingSeniorResponse.model_validate(senior)

    return response


async def validate_hosting_interval(
    session: AsyncSession,
    senior_id: int,
    next_hosting_at: datetime,
) -> None:
    """어르신의 기존 호스팅과 새 호스팅 사이 간격을 검증합니다."""

    stmt = (
        select(Hosting)
        .where(
            Hosting.senior_id == senior_id,
            Hosting.hosting_status.in_(NON_FAILED_HOSTING_STATUSES),
        )
        .order_by(Hosting.hosting_at.asc())
    )

    result = await session.execute(stmt)
    existing_hostings = result.scalars().all()

    for existing_hosting in existing_hostings:
        existing_hosting_at = ensure_utc_aware(existing_hosting.hosting_at)
        time_gap = abs(next_hosting_at - existing_hosting_at)

        if time_gap < MIN_HOSTING_INTERVAL:
            blocked_start_at = existing_hosting_at - MIN_HOSTING_INTERVAL
            blocked_end_at = existing_hosting_at + MIN_HOSTING_INTERVAL

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "이 어르신의 새 호스팅은 기존 호스팅 시작 시각의 전후 7일을 "
                    "피해서 등록해야 합니다. "
                    f"(기존 호스팅 시작: {existing_hosting_at.isoformat()}, "
                    f"차단 구간: {blocked_start_at.isoformat()} ~ {blocked_end_at.isoformat()})"
                ),
            )


def process_hosting_status_by_time(
    hosting: Hosting,
) -> HostingStatus | None:
    """호스팅 1건의 시간 기반 다음 상태를 계산합니다."""

    now = get_now_utc()
    hosting_at = ensure_utc_aware(hosting.hosting_at)
    hosting_end = ensure_utc_aware(hosting.hosting_end)
    deadline_at = hosting_at - timedelta(hours=12)
    current_status = hosting.hosting_status

    if now >= deadline_at and current_status == HostingStatus.OPEN:
        return HostingStatus.FAILED

    if now >= deadline_at and current_status == HostingStatus.FULL:
        return HostingStatus.FIXED

    if now >= hosting_at and current_status == HostingStatus.FIXED:
        return HostingStatus.IN_PROGRESS

    if now >= hosting_end:
        if current_status == HostingStatus.IN_PROGRESS:
            return HostingStatus.CLOSED

        if current_status in {
            HostingStatus.OPEN,
            HostingStatus.FULL,
            HostingStatus.FIXED,
        }:
            return HostingStatus.FAILED

    return None


async def get_approved_volunteer_ids(
    session: AsyncSession,
    hosting_id: int,
) -> list[int]:
    """호스팅에 APPROVED 상태인 봉사자 ID 목록을 반환합니다."""

    result = await session.execute(
        select(MatchingInfo.vt_id).where(
            MatchingInfo.hosting_id == hosting_id,
            MatchingInfo.match_status == MatchStatus.APPROVED,
        )
    )
    return list(result.scalars().all())

async def get_visible_match_id_for_volunteer(
    session: AsyncSession,
    hosting_id: int,
    volunteer_id: int,
) -> int | None:
    """봉사자가 해당 호스팅을 조회할 수 있는 매칭 ID를 반환합니다."""

    result = await session.execute(
        select(MatchingInfo.matching_id).where(
            MatchingInfo.hosting_id == hosting_id,
            MatchingInfo.vt_id == volunteer_id,
            MatchingInfo.match_status.in_(
                [
                    MatchStatus.APPROVED,
                    MatchStatus.NOT_VISITED,
                ]
            ),
        )
    )

    return result.scalar_one_or_none()


async def mark_matches_not_visited(
    session: AsyncSession,
    hosting_id: int,
) -> int:
    """호스팅의 미방문 매칭을 NOT_VISITED로 변경합니다."""

    stmt = select(MatchingInfo).where(
        MatchingInfo.hosting_id == hosting_id,
        MatchingInfo.match_status == MatchStatus.APPROVED,
    )
    result = await session.execute(stmt)
    matches = result.scalars().all()

    changed_count = 0

    for match in matches:
        if match.check_out_time is None:
            match.match_status = MatchStatus.NOT_VISITED
            changed_count += 1

    return changed_count


async def run_hosting_status_scheduler(
    session: AsyncSession,
) -> int:
    """시간 조건이 도래한 호스팅과 매칭 상태를 일괄 처리합니다."""

    stmt = select(Hosting).where(
        Hosting.hosting_status.in_(
            [
                HostingStatus.OPEN,
                HostingStatus.FULL,
                HostingStatus.FIXED,
                HostingStatus.IN_PROGRESS,
            ]
        )
    )

    result = await session.execute(stmt)
    hostings = result.scalars().all()

    changed_count = 0
    notification_map: dict[int, tuple[AlarmType, int, list[int]]] = {}

    for hosting in hostings:
        new_status = process_hosting_status_by_time(hosting=hosting)
        if new_status is None:
            continue

        if hosting.hosting_status != new_status:
            prev_status = hosting.hosting_status
            hosting.hosting_status = new_status
            changed_count += 1
            logger.info(
                "호스팅 ID=%d 상태 전환: %s → %s",
                hosting.hosting_id,
                prev_status,
                new_status,
            )

        if new_status in {HostingStatus.FAILED, HostingStatus.FIXED}:
            vt_ids = await get_approved_volunteer_ids(session, hosting.hosting_id)
            senior = await session.get(Senior, hosting.senior_id)
            if senior is not None:
                alarm_type = (
                    AlarmType.DELETE
                    if new_status == HostingStatus.FAILED
                    else AlarmType.MATCH
                )
                notification_map[hosting.hosting_id] = (
                    alarm_type,
                    senior.guardian_id,
                    vt_ids,
                )

        if new_status in {HostingStatus.FAILED, HostingStatus.CLOSED}:
            await mark_matches_not_visited(
                session=session,
                hosting_id=hosting.hosting_id,
            )

    if changed_count > 0:
        await session.commit()
        logger.info("스케줄러 커밋 완료: 호스팅 %d건 상태 변경", changed_count)

    sms_tasks = []
    for hid, (alarm_type, guardian_id, vt_ids) in notification_map.items():
        sms_tasks.append(
            send_sms(
                db=session,
                hosting_id=hid,
                receiver_id=guardian_id,
                alarm_type=alarm_type,
                use_long_message=True,
            )
        )
        for vt_id in vt_ids:
            sms_tasks.append(
                send_sms(
                    db=session,
                    hosting_id=hid,
                    receiver_id=vt_id,
                    alarm_type=alarm_type,
                    use_long_message=True,
                )
            )

    results = await asyncio.gather(*sms_tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logger.warning("SMS 발송 실패: %s", result)

    if sms_tasks:
        await session.commit()

    return changed_count


async def create_hosting(
    session: AsyncSession,
    guardian_id: int,
    request: HostingCreateRequest,
) -> HostingResponse:
    """호스팅을 등록합니다."""

    senior = await get_guardian_senior_by_id(
        session=session,
        guardian_id=guardian_id,
        senior_id=request.senior_id,
    )

    if not senior.active_flag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="비활성화된 어르신으로는 호스팅을 등록할 수 없습니다.",
        )

    hosting_at = ensure_utc_aware(request.hosting_at)
    hosting_end = ensure_utc_aware(request.hosting_end)

    await validate_hosting_interval(
        session=session,
        senior_id=senior.senior_id,
        next_hosting_at=hosting_at,
    )

    hosting_max_people = request.max_people
    if hosting_max_people is None:
        hosting_max_people = senior.max_people

    # 어르신 주소를 호스팅 시점 스냅샷으로 복사 (이후 senior 주소 변경과 무관)
    senior_address = await session.get(Address, senior.address_id)
    address_snapshot = Address(
        road_address=senior_address.road_address,
        jibun_address=senior_address.jibun_address,
        zonecode=senior_address.zonecode,
        sigungu=senior_address.sigungu,
        bname=senior_address.bname,
        detail_address=senior_address.detail_address,
        sido=senior_address.sido,
        building_name=senior_address.building_name,
        is_apartment=senior_address.is_apartment,
        lat=senior_address.lat,
        lng=senior_address.lng,
        sigungu_code=senior_address.sigungu_code,
    )
    session.add(address_snapshot)
    await session.flush()  # address_id 확보

    hosting = Hosting(
        senior_id=senior.senior_id,
        address_id=address_snapshot.address_id,
        menu=request.menu,
        hosting_at=hosting_at,
        hosting_end=hosting_end,
        max_people=hosting_max_people,
        hosting_status=HostingStatus.OPEN,
    )

    session.add(hosting)
    await session.commit()

    # commit 후 address relationship 포함해 재조회
    result = await session.execute(
        select(Hosting)
        .where(Hosting.hosting_id == hosting.hosting_id)
        .options(selectinload(Hosting.address))
    )
    hosting = result.scalar_one()
    senior = await get_senior_with_address_by_id(session, hosting.senior_id)

    return build_hosting_response(hosting=hosting, current_people=0, senior=senior)


async def list_hostings_by_guardian(
    session: AsyncSession,
    guardian_id: int,
) -> list[HostingResponse]:
    """보호자 기준 호스팅 목록을 조회합니다."""

    stmt = (
        select(Hosting)
        .join(Senior, Senior.senior_id == Hosting.senior_id)
        .where(Senior.guardian_id == guardian_id)
        .options(selectinload(Hosting.address))
        .order_by(Hosting.created_at.desc())
    )

    result = await session.execute(stmt)
    hostings = result.scalars().all()
    hosting_ids = [hosting.hosting_id for hosting in hostings]
    current_people_map = await get_current_people_count_map(
        session=session,
        hosting_ids=hosting_ids,
    )

    return [
        build_hosting_response(
            hosting=hosting,
            current_people=current_people_map.get(hosting.hosting_id, 0),
        )
        for hosting in hostings
    ]


async def get_hosting_detail(
    session: AsyncSession,
    guardian_id: int,
    hosting_id: int,
) -> HostingResponse:
    """보호자의 호스팅 상세 정보를 조회합니다."""

    hosting = await get_guardian_hosting_by_id(
        session=session,
        guardian_id=guardian_id,
        hosting_id=hosting_id,
    )
    current_people = await get_current_people_count(
        session=session,
        hosting_id=hosting.hosting_id,
    )
    senior = await get_senior_with_address_by_id(session, hosting.senior_id)

    return build_hosting_response(
        hosting=hosting,
        current_people=current_people,
        senior=senior,
    )


async def cancel_hosting(
    session: AsyncSession,
    guardian_id: int,
    hosting_id: int,
) -> HostingResponse:
    """호스팅을 취소합니다."""

    hosting = await get_guardian_hosting_by_id(
        session=session,
        guardian_id=guardian_id,
        hosting_id=hosting_id,
    )

    if hosting.hosting_status in {
        HostingStatus.FIXED,
        HostingStatus.IN_PROGRESS,
        HostingStatus.CLOSED,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="호스팅 확정 / 진행 중 / 완료 시에는 취소할 수 없습니다.",
        )

    hosting.hosting_status = HostingStatus.FAILED
    vt_ids = await get_approved_volunteer_ids(session, hosting_id)
    await mark_matches_not_visited(session=session, hosting_id=hosting_id)

    await session.commit()
    await session.refresh(hosting)

    sms_tasks = []
    for vt_id in vt_ids:
        sms_tasks.append(
            send_sms(
                db=session,
                hosting_id=hosting_id,
                receiver_id=vt_id,
                alarm_type=AlarmType.DELETE,
                use_long_message=True,
            )
        )
    results = await asyncio.gather(*sms_tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            logger.warning("SMS 발송 실패: %s", result)

    if sms_tasks:
        await session.commit()

    hosting = await get_guardian_hosting_by_id(
        session=session,
        guardian_id=guardian_id,
        hosting_id=hosting_id,
    )
    current_people = await get_current_people_count(
        session=session,
        hosting_id=hosting.hosting_id,
    )
    senior = await get_senior_with_address_by_id(session, hosting.senior_id)

    return build_hosting_response(
        hosting=hosting,
        current_people=current_people,
        senior=senior,
    )


async def update_hosting(
    session: AsyncSession,
    guardian_id: int,
    hosting_id: int,
    request: HostingUpdateRequest,
) -> HostingResponse:
    """호스팅 정보를 수정합니다 (OPEN/FULL 상태에서만 허용)."""

    hosting = await get_guardian_hosting_by_id(
        session=session,
        guardian_id=guardian_id,
        hosting_id=hosting_id,
    )

    if hosting.hosting_status not in {HostingStatus.OPEN, HostingStatus.FULL}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="모집 중 또는 모집완료 상태의 호스팅만 수정할 수 있습니다.",
        )

    if request.menu is not None:
        hosting.menu = request.menu
    if request.max_people is not None:
        current_people = await get_current_people_count(session, hosting_id)
        if request.max_people < current_people:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"현재 승인된 인원({current_people}명)보다 적은 인원으로 변경할 수 없습니다.",
            )
        hosting.max_people = request.max_people

    await session.commit()

    hosting = await get_guardian_hosting_by_id(session, guardian_id, hosting_id)
    current_people = await get_current_people_count(session, hosting.hosting_id)
    senior = await get_senior_with_address_by_id(session, hosting.senior_id)

    return build_hosting_response(hosting=hosting, current_people=current_people, senior=senior)


async def list_hostings_for_volunteer(
    session: AsyncSession,
    page: int = 1,
    size: int = 20,
    sido: str | None = None,
    sigungu: str | None = None,
    hosting_date: date_type | None = None,
) -> HostingListResponse:
    """봉사자가 탐색 가능한 공개 호스팅 목록을 페이지네이션/필터링과 함께 조회합니다."""

    visible_statuses = (HostingStatus.OPEN, HostingStatus.FULL)
    KST = ZoneInfo("Asia/Seoul")

    base_stmt = (
        select(Hosting)
        .join(Address, Address.address_id == Hosting.address_id)
        .where(Hosting.hosting_status.in_(visible_statuses))
    )

    if sido:
        base_stmt = base_stmt.where(Address.sido == sido)
    if sigungu:
        base_stmt = base_stmt.where(Address.sigungu == sigungu)
    if hosting_date:
        start_kst = datetime(hosting_date.year, hosting_date.month, hosting_date.day, 0, 0, 0, tzinfo=KST)
        end_kst = datetime(hosting_date.year, hosting_date.month, hosting_date.day, 23, 59, 59, tzinfo=KST)
        base_stmt = base_stmt.where(
            Hosting.hosting_at >= start_kst.astimezone(timezone.utc),
            Hosting.hosting_at <= end_kst.astimezone(timezone.utc),
        )

    total_result = await session.execute(select(func.count()).select_from(base_stmt.subquery()))
    total = total_result.scalar_one()

    paged_stmt = (
        base_stmt
        .options(selectinload(Hosting.address))
        .order_by(Hosting.hosting_at.asc(), Hosting.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )

    result = await session.execute(paged_stmt)
    hostings = result.scalars().all()
    hosting_ids = [hosting.hosting_id for hosting in hostings]
    current_people_map = await get_current_people_count_map(session=session, hosting_ids=hosting_ids)

    items = [
        build_hosting_response(
            hosting=hosting,
            current_people=current_people_map.get(hosting.hosting_id, 0),
        )
        for hosting in hostings
    ]

    return HostingListResponse(items=items, total=total, page=page, size=size)


async def get_public_hosting_detail(
    session: AsyncSession,
    hosting_id: int,
    volunteer_id: int,
) -> HostingResponse:
    """봉사자가 조회 가능한 공개 호스팅 상세 정보를 반환합니다."""

    public_visible_statuses = (
        HostingStatus.OPEN,
        HostingStatus.FULL,
    )

    applicant_visible_statuses = (
        HostingStatus.FIXED,
        HostingStatus.IN_PROGRESS,
        HostingStatus.CLOSED,
        HostingStatus.FAILED,
    )

    stmt = (
        select(Hosting)
        .where(Hosting.hosting_id == hosting_id)
        .options(selectinload(Hosting.address))
    )

    result = await session.execute(stmt)
    hosting = result.scalar_one_or_none()

    if hosting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="조회 가능한 호스팅 정보를 찾을 수 없습니다.",
        )

    is_public_visible = hosting.hosting_status in public_visible_statuses
    is_applicant_visible = False

    if hosting.hosting_status in applicant_visible_statuses:
        matching_id = await get_visible_match_id_for_volunteer(
            session=session,
            hosting_id=hosting.hosting_id,
            volunteer_id=volunteer_id,
        )
        is_applicant_visible = matching_id is not None

    if not is_public_visible and not is_applicant_visible:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="조회 가능한 호스팅 정보를 찾을 수 없습니다.",
        )

    senior = None
    if hosting.senior_id is not None:
        senior_result = await session.execute(
            select(Senior)
            .where(Senior.senior_id == hosting.senior_id)
            .options(selectinload(Senior.address))
        )
        senior = senior_result.scalar_one_or_none()

    current_people = await get_current_people_count(
        session=session,
        hosting_id=hosting.hosting_id,
    )

    return build_hosting_response(
        hosting=hosting,
        current_people=current_people,
        senior=senior,
    )
