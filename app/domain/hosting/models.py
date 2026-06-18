"""호스팅 SQLAlchemy ORM 모델."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.domain.common.models import Address


class HostingStatus(str, enum.Enum):
    """호스팅 상태."""

    OPEN = "OPEN"
    FULL = "FULL"
    FIXED = "FIXED"
    FAILED = "FAILED"
    IN_PROGRESS = "IN_PROGRESS"
    CLOSED = "CLOSED"


class AlarmType(str, enum.Enum):
    """SMS 알림 타입."""

    MATCH = "match"
    CHECKIN = "checkin"
    CHECKOUT = "checkout"
    UPDATE = "update"
    DELETE = "delete"


class Hosting(Base):
    """호스팅 정보를 저장하는 모델입니다."""

    __tablename__ = "hostings"
    __table_args__ = (
        CheckConstraint("max_people >= 2", name="ck_hosting_max_people"),
    )

    hosting_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    senior_id: Mapped[int | None] = mapped_column(
        ForeignKey("seniors.senior_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    menu: Mapped[str] = mapped_column(String(255), nullable=False)
    hosting_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    hosting_end: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
    )
    max_people: Mapped[int] = mapped_column(Integer, nullable=False)

    address_id: Mapped[int] = mapped_column(
        ForeignKey("addresses.address_id"), unique=True, nullable=False
    )
    address: Mapped[Address] = relationship("Address")

    hosting_status: Mapped[HostingStatus] = mapped_column(
        Enum(HostingStatus),
        nullable=False,
        default=HostingStatus.OPEN,
    )

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



class SmsLog(Base):
    """SMS 발송 이력."""

    __tablename__ = "sms_logs"

    sms_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hosting_id: Mapped[int] = mapped_column(
        ForeignKey("hostings.hosting_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receiver_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_send: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    alarm_type: Mapped[AlarmType] = mapped_column(
        Enum(AlarmType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    contents: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
