"""매칭 핵심 비즈니스 로직 테스트."""

import pytest
import pytest_asyncio

from app.domain.hosting.models import HostingStatus
from app.domain.match.models import MatchStatus
from app.domain.match.service import cancel_match, create_match

from tests.conftest import make_address, make_hosting, make_senior, make_user


@pytest_asyncio.fixture
async def base_objects(db):
    """테스트용 공통 DB 객체(주소, 유저, 어르신, 호스팅)를 생성합니다."""
    # 보호자
    grd_addr = make_address(road_address="서울시 강남구 1번지", detail_address="A동")
    db.add(grd_addr)
    await db.flush()

    guardian = make_user(grd_addr, role="GUARDIAN", email="guardian@test.com", phone_number="01011110001")
    db.add(guardian)
    await db.flush()

    # 어르신
    sr_addr = make_address(road_address="서울시 강남구 2번지", detail_address="B동")
    db.add(sr_addr)
    await db.flush()

    senior = make_senior(guardian, sr_addr)
    db.add(senior)
    await db.flush()

    # 호스팅 주소
    h_addr = make_address(road_address="서울시 강남구 3번지", detail_address="C동")
    db.add(h_addr)
    await db.flush()

    hosting = make_hosting(senior, h_addr, max_people=2)
    db.add(hosting)
    await db.flush()

    # 봉사자 2명
    vt1_addr = make_address(road_address="서울시 강남구 4번지", detail_address="D동")
    vt2_addr = make_address(road_address="서울시 강남구 5번지", detail_address="E동")
    vt3_addr = make_address(road_address="서울시 강남구 6번지", detail_address="F동")
    db.add_all([vt1_addr, vt2_addr, vt3_addr])
    await db.flush()

    vt1 = make_user(vt1_addr, email="vt1@test.com", phone_number="01022220001")
    vt2 = make_user(vt2_addr, email="vt2@test.com", phone_number="01022220002")
    vt3 = make_user(vt3_addr, email="vt3@test.com", phone_number="01022220003")
    db.add_all([vt1, vt2, vt3])
    await db.flush()

    await db.commit()
    return {"hosting": hosting, "vt1": vt1, "vt2": vt2, "vt3": vt3}


@pytest.mark.asyncio
async def test_hosting_goes_full_when_max_people_reached(db, base_objects):
    """max_people(=2) 만큼 신청하면 호스팅이 FULL로 바뀐다."""
    hosting = base_objects["hosting"]
    vt1 = base_objects["vt1"]
    vt2 = base_objects["vt2"]

    await create_match(db, hosting.hosting_id, vt1.user_id)
    await create_match(db, hosting.hosting_id, vt2.user_id)

    await db.refresh(hosting)
    assert hosting.hosting_status == HostingStatus.FULL


@pytest.mark.asyncio
async def test_waitlist_on_full_hosting(db, base_objects):
    """정원 초과 시 WAITING 상태로 대기자 등록된다."""
    hosting = base_objects["hosting"]
    vt1 = base_objects["vt1"]
    vt2 = base_objects["vt2"]
    vt3 = base_objects["vt3"]

    await create_match(db, hosting.hosting_id, vt1.user_id)
    await create_match(db, hosting.hosting_id, vt2.user_id)  # → FULL

    match3 = await create_match(db, hosting.hosting_id, vt3.user_id)  # → WAITING
    assert match3.match_status == MatchStatus.WAITING


@pytest.mark.asyncio
async def test_cancel_promotes_waiting_to_approved(db, base_objects):
    """승인자가 취소하면 대기자가 APPROVED로 자동 승격된다."""
    hosting = base_objects["hosting"]
    vt1 = base_objects["vt1"]
    vt2 = base_objects["vt2"]
    vt3 = base_objects["vt3"]

    match1 = await create_match(db, hosting.hosting_id, vt1.user_id)
    await create_match(db, hosting.hosting_id, vt2.user_id)  # → FULL
    match3 = await create_match(db, hosting.hosting_id, vt3.user_id)  # → WAITING

    # vt1 취소 — hosting 12시간 전 제한을 우회하기 위해 12시간 이상 남은 hosting_at 확인
    await cancel_match(db, match1.matching_id, vt1.user_id)

    await db.refresh(match3)
    assert match3.match_status == MatchStatus.APPROVED

    # 호스팅은 FULL 상태 유지 (vt2 + vt3로 채워짐)
    await db.refresh(hosting)
    assert hosting.hosting_status == HostingStatus.FULL


@pytest.mark.asyncio
async def test_cancel_restores_open_when_no_waitlist(db, base_objects):
    """대기자 없이 취소하면 호스팅이 OPEN으로 복구된다."""
    hosting = base_objects["hosting"]
    vt1 = base_objects["vt1"]
    vt2 = base_objects["vt2"]

    match1 = await create_match(db, hosting.hosting_id, vt1.user_id)
    await create_match(db, hosting.hosting_id, vt2.user_id)  # → FULL

    await cancel_match(db, match1.matching_id, vt1.user_id)

    await db.refresh(hosting)
    assert hosting.hosting_status == HostingStatus.OPEN
