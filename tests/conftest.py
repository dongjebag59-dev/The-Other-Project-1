"""테스트 공통 fixture."""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import app


@pytest.fixture
def client():
    """FastAPI TestClient를 반환합니다."""
    return TestClient(app)


@pytest_asyncio.fixture
async def db():
    """함수 스코프 인메모리 테스트 DB 세션을 반환합니다."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ── 공통 헬퍼 ────────────────────────────────────────────────────────────────

def make_address(**kwargs):
    from app.domain.common.models import Address

    defaults = dict(
        road_address="서울시 강남구 테헤란로 1",
        detail_address="101호",
        sigungu="강남구",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Address(**defaults)


def make_user(address, role="VOLUNTEER", **kwargs):
    from app.domain.user.models import CertFlag, User, UserRole

    defaults = dict(
        name="테스트유저",
        email=f"test_{id(address)}@example.com",
        password="hashed",
        phone_number="01012345678",
        address_id=address.address_id,
        user_role=UserRole[role],
        cert_flag=CertFlag.APPROVED,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return User(**defaults)


def make_senior(guardian, address, **kwargs):
    from app.domain.senior.models import GenderEnum, Senior

    defaults = dict(
        guardian_id=guardian.user_id,
        address_id=address.address_id,
        name="테스트어르신",
        gender=GenderEnum.MALE,
        birth_date=datetime(1940, 1, 1).date(),
        max_people=2,
        active_flag=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Senior(**defaults)


def make_hosting(senior, address, **kwargs):
    from app.domain.hosting.models import Hosting, HostingStatus

    defaults = dict(
        senior_id=senior.senior_id,
        address_id=address.address_id,
        menu="된장찌개",
        hosting_at=datetime(2026, 12, 1, 11, 0, tzinfo=timezone.utc),
        hosting_end=datetime(2026, 12, 1, 13, 0, tzinfo=timezone.utc),
        max_people=2,
        hosting_status=HostingStatus.OPEN,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Hosting(**defaults)
