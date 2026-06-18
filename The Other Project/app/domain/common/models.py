"""공통 SQLAlchemy ORM 모델."""

from datetime import datetime, timezone

from sqlalchemy import TIMESTAMP, Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Address(Base):
    """주소 정보를 저장하는 공통 모델. seniors, hostings, users가 1:1로 참조."""

    __tablename__ = "addresses"

    address_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    road_address: Mapped[str] = mapped_column(String(255), nullable=False)
    jibun_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    zonecode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sigungu: Mapped[str] = mapped_column(String(100), nullable=False)
    bname: Mapped[str | None] = mapped_column(String(100), nullable=True)
    detail_address: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    sido: Mapped[str | None] = mapped_column(String(50), nullable=True)
    building_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_apartment: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # lat : 현재 미지원 — 지도 기반 기능 확장 시 사용 예정
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    # lng : 현재 미지원 — 지도 기반 기능 확장 시 사용 예정
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    sigungu_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
