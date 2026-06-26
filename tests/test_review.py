"""후기 비즈니스 로직 테스트."""

from datetime import datetime, timezone

import pytest
import pytest_asyncio

from app.domain.hosting.models import HostingStatus
from app.domain.match.models import MatchStatus, MatchingInfo
from app.domain.review.service import create_review, update_review

from tests.conftest import make_address, make_hosting, make_senior, make_user


@pytest_asyncio.fixture
async def completed_match(db):
    """체크아웃 완료된 매칭 픽스처를 반환합니다."""
    grd_addr = make_address(road_address="서울시 종로구 1번지", detail_address="A동")
    db.add(grd_addr)
    await db.flush()

    guardian = make_user(grd_addr, role="GUARDIAN", email="grd2@test.com", phone_number="01033330001")
    db.add(guardian)
    await db.flush()

    sr_addr = make_address(road_address="서울시 종로구 2번지", detail_address="B동")
    db.add(sr_addr)
    await db.flush()

    senior = make_senior(guardian, sr_addr)
    db.add(senior)
    await db.flush()

    h_addr = make_address(road_address="서울시 종로구 3번지", detail_address="C동")
    db.add(h_addr)
    await db.flush()

    hosting = make_hosting(senior, h_addr, hosting_status=HostingStatus.CLOSED)
    db.add(hosting)
    await db.flush()

    vt_addr = make_address(road_address="서울시 종로구 4번지", detail_address="D동")
    db.add(vt_addr)
    await db.flush()

    volunteer = make_user(vt_addr, email="vt_rv@test.com", phone_number="01044440001")
    db.add(volunteer)
    await db.flush()

    match = MatchingInfo(
        hosting_id=hosting.hosting_id,
        vt_id=volunteer.user_id,
        senior_id=senior.senior_id,
        match_status=MatchStatus.APPROVED,
        check_in_time=datetime(2026, 12, 1, 11, 0, tzinfo=timezone.utc),
        check_out_time=datetime(2026, 12, 1, 13, 0, tzinfo=timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    db.add(match)
    await db.commit()

    return {"match": match, "volunteer": volunteer}


@pytest.mark.asyncio
async def test_update_review_sets_updated_at(db, completed_match):
    """후기 수정 시 updated_at이 채워진다."""
    match = completed_match["match"]
    volunteer = completed_match["volunteer"]

    review = await create_review(db, match.matching_id, volunteer.user_id, "좋아요", [])
    assert review.updated_at is None  # 최초 작성 시 None

    updated = await update_review(db, review.review_id, volunteer.user_id, "더 좋아요")
    assert updated.updated_at is not None


@pytest.mark.asyncio
async def test_create_review_duplicate_raises(db, completed_match):
    """동일 매칭에 후기를 두 번 작성하면 409를 반환한다."""
    from fastapi import HTTPException

    match = completed_match["match"]
    volunteer = completed_match["volunteer"]

    await create_review(db, match.matching_id, volunteer.user_id, "첫 번째", [])

    with pytest.raises(HTTPException) as exc_info:
        await create_review(db, match.matching_id, volunteer.user_id, "두 번째", [])

    assert exc_info.value.status_code == 409
