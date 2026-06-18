"""매칭 SQLAlchemy ORM 모델."""

import enum
from datetime import datetime, timezone

from sqlalchemy import TIMESTAMP, Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MatchStatus(enum.Enum):
    APPROVED = "approved"
    CANCELLED = "cancelled"
    NOT_VISITED = "not_visited"


class MatchingInfo(Base):
    __tablename__ = "matching_info"

    matching_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hosting_id: Mapped[int] = mapped_column(ForeignKey("hostings.hosting_id", ondelete="CASCADE"))
    vt_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))  # 봉사자
    senior_id: Mapped[int] = mapped_column(  # 어르신
        ForeignKey("seniors.senior_id", ondelete="CASCADE")
    )
    match_status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus), default=MatchStatus.APPROVED
    )
    check_in_time: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    check_out_time: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    # 관리자 최종 부여 봉사시간 (분 단위)
    actual_volunteer_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
