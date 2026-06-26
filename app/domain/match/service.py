"""매칭 비즈니스 로직."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.hosting.models import AlarmType, Hosting, HostingStatus
from app.domain.match.models import MatchingInfo, MatchStatus
from app.domain.match.schemas import (
    MyMatchCheckResponse,
    MyMatchListResponse,
    MyMatchResponse,
    VolunteerStatsResponse,
)
from app.domain.review.models import Review
from app.domain.senior.models import Senior
from app.services.sms import send_sms


async def check_my_match(db: AsyncSession, hosting_id: int, vt_id: int) -> MyMatchCheckResponse:
    """봉사자의 호스팅 신청 여부를 조회합니다."""
    result = await db.execute(
        select(MatchingInfo).where(
            MatchingInfo.hosting_id == hosting_id,
            MatchingInfo.vt_id == vt_id,
            MatchingInfo.match_status != MatchStatus.CANCELLED,
        )
    )
    match = result.scalar_one_or_none()
    return MyMatchCheckResponse(
        is_applied=match is not None,
        matching_id=match.matching_id if match else None,
    )


async def create_match(db: AsyncSession, hosting_id: int, vt_id: int) -> MatchingInfo:
    """매칭을 생성합니다."""

    # 1. 호스팅 존재 여부 확인 (동시 요청 대비 row 잠금)
    result = await db.execute(
        select(Hosting).where(Hosting.hosting_id == hosting_id).with_for_update()
    )
    hosting = result.scalar_one_or_none()
    if not hosting:
        raise HTTPException(status_code=404, detail="존재하지 않는 호스팅입니다.")

    # 2. 호스팅 상태 확인 (OPEN 또는 FULL만 신청 가능)
    if hosting.hosting_status not in (HostingStatus.OPEN, HostingStatus.FULL):
        raise HTTPException(status_code=400, detail="신청 불가능한 호스팅입니다.")

    # 3. 같은 날짜 중복 신청 확인 (같은 호스팅 포함, WAITING도 포함)
    result = await db.execute(
        select(MatchingInfo)
        .join(Hosting, MatchingInfo.hosting_id == Hosting.hosting_id)
        .where(
            MatchingInfo.vt_id == vt_id,
            MatchingInfo.match_status != MatchStatus.CANCELLED,
            func.date(Hosting.hosting_at) == func.date(hosting.hosting_at),
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="같은 날짜에 이미 신청한 호스팅이 있습니다.")

    if hosting.hosting_status == HostingStatus.OPEN:
        # 4a. 즉시 승인
        match = MatchingInfo(
            hosting_id=hosting_id,
            vt_id=vt_id,
            senior_id=hosting.senior_id,
            match_status=MatchStatus.APPROVED,
        )
        db.add(match)
        await db.flush()

        # 5. 승인 인원이 max_people에 도달하면 모집완료로 변경
        count_result = await db.execute(
            select(func.count()).where(
                MatchingInfo.hosting_id == hosting_id,
                MatchingInfo.match_status == MatchStatus.APPROVED,
            )
        )
        if count_result.scalar() >= hosting.max_people:
            hosting.hosting_status = HostingStatus.FULL
    else:
        # 4b. 정원 초과 — 대기자 등록
        match = MatchingInfo(
            hosting_id=hosting_id,
            vt_id=vt_id,
            senior_id=hosting.senior_id,
            match_status=MatchStatus.WAITING,
        )
        db.add(match)
        await db.flush()

    await db.commit()
    await db.refresh(match)

    return match


async def list_matches_by_volunteer(
    db: AsyncSession,
    vt_id: int,
    is_completed: bool,
    page: int = 1,
    size: int = 10,
) -> MyMatchListResponse:
    """봉사자의 매칭 목록을 예정/완료 구분 및 페이징하여 조회합니다."""
    where_conditions = [
        MatchingInfo.vt_id == vt_id,
        MatchingInfo.match_status != MatchStatus.CANCELLED,
    ]

    # NOT_VISITED는 체크아웃 없어도 완료 탭에 포함
    if is_completed:
        where_conditions.append(
            (MatchingInfo.check_out_time.isnot(None))
            | (MatchingInfo.match_status == MatchStatus.NOT_VISITED)
            | (Hosting.hosting_status == HostingStatus.FAILED)
        )
    else:
        where_conditions.append(MatchingInfo.check_out_time.is_(None))
        where_conditions.append(MatchingInfo.match_status != MatchStatus.NOT_VISITED)
        where_conditions.append(Hosting.hosting_status != HostingStatus.FAILED)

    query = (
        select(MatchingInfo, Hosting, Senior)
        .join(Hosting, MatchingInfo.hosting_id == Hosting.hosting_id)
        .join(Senior, MatchingInfo.senior_id == Senior.senior_id)
        .options(selectinload(Senior.address))
        .where(*where_conditions)
    )

    # 전체 개수 조회
    count_result = await db.execute(
        select(func.count(MatchingInfo.matching_id))
        .join(Hosting, MatchingInfo.hosting_id == Hosting.hosting_id)
        .where(*where_conditions)
    )
    total = count_result.scalar() or 0

    # 목록 조회 (페이징) — 예정: 가까운 날짜 먼저, 완료: 최근 날짜 먼저
    order = Hosting.hosting_at.asc() if not is_completed else Hosting.hosting_at.desc()
    result = await db.execute(
        query.order_by(order).offset((page - 1) * size).limit(size)
    )
    rows = result.all()

    # 후기 여부 조회 (matching_id → review_id 맵)
    matching_ids = [match.matching_id for match, _, _ in rows]
    review_id_map: dict[int, int] = {}
    if matching_ids:
        review_result = await db.execute(
            select(Review.matching_id, Review.review_id).where(
                Review.matching_id.in_(matching_ids)
            )
        )
        review_id_map = {row.matching_id: row.review_id for row in review_result.all()}

    items = [
        MyMatchResponse(
            matching_id=match.matching_id,
            match_status=match.match_status,
            check_in_time=match.check_in_time,
            check_out_time=match.check_out_time,
            hosting_id=hosting.hosting_id,
            menu=hosting.menu,
            hosting_at=hosting.hosting_at,
            hosting_status=hosting.hosting_status,
            senior_id=senior.senior_id,
            senior_name=senior.name,
            senior_address=senior.address.road_address,
            actual_volunteer_time=match.actual_volunteer_time,
            has_review=review_id_map.get(match.matching_id) is not None,
            review_id=review_id_map.get(match.matching_id),
        )
        for match, hosting, senior in rows
    ]

    return MyMatchListResponse(total=total, items=items)


async def cancel_match(db: AsyncSession, matching_id: int, vt_id: int) -> MatchingInfo:
    """매칭을 취소합니다."""
    match = await db.get(MatchingInfo, matching_id)

    if not match:
        raise HTTPException(status_code=404, detail="존재하지 않는 매칭입니다.")

    # 본인 매칭인지 확인
    if match.vt_id != vt_id:
        raise HTTPException(status_code=403, detail="본인 매칭만 취소할 수 있습니다.")

    # 이미 취소된 매칭 방어
    if match.match_status == MatchStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="이미 취소된 매칭입니다.")

    hosting = await db.get(Hosting, match.hosting_id)

    # 호스팅 12시간 전부터는 취소 불가
    if hosting:
        hosting_at = (
            hosting.hosting_at
            if hosting.hosting_at.tzinfo
            else hosting.hosting_at.replace(tzinfo=timezone.utc)
        )
    if hosting and hosting_at - datetime.now(timezone.utc) <= timedelta(hours=12):
        raise HTTPException(status_code=400, detail="호스팅 12시간 전부터는 취소할 수 없습니다.")

    match.match_status = MatchStatus.CANCELLED
    await db.flush()

    if hosting and hosting.hosting_status == HostingStatus.FULL:
        # 대기자가 있으면 첫 번째 대기자를 승인으로 승격
        waiting_result = await db.execute(
            select(MatchingInfo)
            .where(
                MatchingInfo.hosting_id == match.hosting_id,
                MatchingInfo.match_status == MatchStatus.WAITING,
            )
            .order_by(MatchingInfo.created_at.asc())
            .limit(1)
            .with_for_update()
        )
        next_waiting = waiting_result.scalar_one_or_none()
        if next_waiting:
            next_waiting.match_status = MatchStatus.APPROVED
            # 슬롯이 채워졌으므로 호스팅은 FULL 유지
        else:
            # 대기자 없음 — 슬롯 복구
            count_result = await db.execute(
                select(func.count()).where(
                    MatchingInfo.hosting_id == match.hosting_id,
                    MatchingInfo.match_status == MatchStatus.APPROVED,
                )
            )
            if count_result.scalar() < hosting.max_people:
                hosting.hosting_status = HostingStatus.OPEN

    await db.commit()
    await db.refresh(match)
    return match


async def _get_approved_match(db: AsyncSession, senior_id: int, vt_id: int) -> MatchingInfo:
    """승인된 매칭을 조회합니다. NOT_VISITED(지각생 보정)도 포함합니다."""
    result = await db.execute(
        select(MatchingInfo)
        .join(Hosting, MatchingInfo.hosting_id == Hosting.hosting_id)
        .where(
            MatchingInfo.senior_id == senior_id,
            MatchingInfo.vt_id == vt_id,
            MatchingInfo.match_status.in_([MatchStatus.APPROVED, MatchStatus.NOT_VISITED]),
            func.date(Hosting.hosting_at) == datetime.now(ZoneInfo("Asia/Seoul")).date(),
        )
    )
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="존재하지 않는 매칭입니다.")
    return match


async def _get_guardian_id(db: AsyncSession, senior_id: int) -> int:
    """시니어 담당 보호자 ID를 조회합니다."""
    senior = await db.get(Senior, senior_id)
    if senior is None:
        raise HTTPException(status_code=404, detail="어르신 정보를 찾을 수 없습니다.")
    return senior.guardian_id


async def check_in(db: AsyncSession, senior_id: int, vt_id: int) -> MatchingInfo:
    """체크인합니다."""
    match = await _get_approved_match(db, senior_id, vt_id)

    # 버튼을 여러 번 누르는 실수를 방지하기 위해 중복 체크인 차단
    if match.check_in_time:
        raise HTTPException(status_code=400, detail="이미 체크인 완료된 매칭입니다.")

    match.check_in_time = datetime.now(timezone.utc)

    count_result = await db.execute(
        select(func.count()).where(
            MatchingInfo.hosting_id == match.hosting_id,
            MatchingInfo.check_in_time.isnot(None),
        )
    )
    is_first_checkin = count_result.scalar() == 1
    if is_first_checkin:
        hosting = await db.get(Hosting, match.hosting_id)
        if hosting:
            hosting.hosting_status = HostingStatus.IN_PROGRESS

    await db.commit()
    await db.refresh(match)

    guardian_id = await _get_guardian_id(db, senior_id)
    await send_sms(
        db=db,
        hosting_id=match.hosting_id,
        receiver_id=guardian_id,
        alarm_type=AlarmType.CHECKIN,
        volunteer_id=vt_id,
    )
    await db.commit()

    return match


async def check_out(db: AsyncSession, senior_id: int, vt_id: int) -> MatchingInfo:
    """체크아웃합니다."""
    match = await _get_approved_match(db, senior_id, vt_id)

    # 체크인 없이 체크아웃하면 봉사 시간 계산이 불가능하므로 순서 강제
    if not match.check_in_time:
        raise HTTPException(status_code=400, detail="체크인 후 체크아웃할 수 있습니다.")

    # 버튼을 여러 번 누르는 실수를 방지하기 위해 중복 체크아웃 차단
    if match.check_out_time:
        raise HTTPException(status_code=400, detail="이미 체크아웃 완료된 매칭입니다.")

    match.check_out_time = datetime.now(timezone.utc)

    # NOT_VISITED 상태에서 체크아웃한 경우 APPROVED로 보정 (지각생)
    # check_in_time 존재는 위 가드에서 이미 보장됨 — 여기서 중복 검증 불필요
    if match.match_status == MatchStatus.NOT_VISITED:
        match.match_status = MatchStatus.APPROVED

    await db.commit()
    await db.refresh(match)

    guardian_id = await _get_guardian_id(db, senior_id)
    await send_sms(
        db=db,
        hosting_id=match.hosting_id,
        receiver_id=guardian_id,
        alarm_type=AlarmType.CHECKOUT,
        volunteer_id=vt_id,
    )
    await db.commit()

    return match


async def get_volunteer_stats(db: AsyncSession, vt_id: int) -> VolunteerStatsResponse:
    """봉사자 마이페이지 통계를 조회합니다."""

    match_row = (await db.execute(
        select(
            func.coalesce(func.sum(MatchingInfo.actual_volunteer_time), 0)
            .label("total_volunteer_minutes"),
            func.count().filter(MatchingInfo.check_in_time.is_not(None)).label("visit_count"),
            func.count(MatchingInfo.senior_id.distinct()).filter(
                MatchingInfo.check_in_time.is_not(None)
            ).label("senior_count"),
        ).where(
            MatchingInfo.vt_id == vt_id,
            MatchingInfo.match_status != MatchStatus.CANCELLED,
        )
    )).one()

    review_count: int = (await db.execute(
        select(func.count()).where(Review.vt_id == vt_id)
    )).scalar_one()

    return VolunteerStatsResponse(
        total_volunteer_minutes=match_row.total_volunteer_minutes,
        visit_count=match_row.visit_count,
        review_count=review_count,
        senior_count=match_row.senior_count,
    )
