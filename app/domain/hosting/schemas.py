"""호스팅 요청/응답 스키마."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.domain.common.schemas import AddressResponse
from app.domain.hosting.models import HostingStatus
from app.domain.senior.models import GenderEnum
from app.domain.senior.schemas import calculate_age_from_birth_date

KST = ZoneInfo("Asia/Seoul")
MIN_HOSTING_LEAD_TIME = timedelta(hours=24)
MAX_HOSTING_LEAD_TIME = timedelta(days=30)


class HostingCreateRequest(BaseModel):
    """호스팅 등록 요청 스키마입니다."""

    senior_id: int = Field(..., ge=1, description="어르신 ID")
    menu: str = Field(..., min_length=1, max_length=255, description="메뉴")
    hosting_at: datetime = Field(..., description="호스팅 시작 일시")
    hosting_end: datetime = Field(..., description="호스팅 종료 일시")
    max_people: int | None = Field(
        default=None,
        ge=2,
        le=4,
        description="모집 가능 인원 (미입력 시 어르신 기본값 사용)",
    )

    @model_validator(mode="after")
    def validate_hosting_time(self) -> "HostingCreateRequest":
        """호스팅 시간 규칙을 검증합니다."""

        if self.hosting_at.tzinfo is None or self.hosting_end.tzinfo is None:
            raise ValueError("호스팅 시작/종료 일시는 시간대 정보가 포함되어야 합니다.")

        now = datetime.now(timezone.utc)
        min_allowed_hosting_at = now + MIN_HOSTING_LEAD_TIME
        max_allowed_hosting_at = now + MAX_HOSTING_LEAD_TIME

        hosting_at_utc = self.hosting_at.astimezone(timezone.utc)
        hosting_end_utc = self.hosting_end.astimezone(timezone.utc)

        hosting_at_kst = self.hosting_at.astimezone(KST)
        hosting_end_kst = self.hosting_end.astimezone(KST)

        if hosting_at_utc < min_allowed_hosting_at:
            raise ValueError("호스팅 시작 일시는 현재 시각보다 최소 24시간 이후여야 합니다.")

        if hosting_at_utc > max_allowed_hosting_at:
            raise ValueError("호스팅 시작 일시는 현재 시각보다 최대 30일 이내여야 합니다.")

        if hosting_end_utc <= hosting_at_utc:
            raise ValueError("호스팅 종료 일시는 시작 일시보다 늦어야 합니다.")

        if hosting_at_kst.time() < time(7, 0):
            raise ValueError("호스팅 시작 시각은 07:00 이후여야 합니다.")

        if hosting_end_kst.time() > time(22, 0):
            raise ValueError("호스팅 종료 시각은 22:00를 넘을 수 없습니다.")

        min_end_time = hosting_at_utc + timedelta(hours=2)
        max_end_time = hosting_at_utc + timedelta(hours=4)

        if hosting_end_utc < min_end_time:
            raise ValueError("호스팅 종료 일시는 시작 일시보다 최소 2시간 늦어야 합니다.")

        if hosting_end_utc > max_end_time:
            raise ValueError("호스팅 종료 일시는 시작 일시보다 최대 4시간까지만 가능합니다.")

        return self


class HostingSeniorResponse(BaseModel):
    """호스팅 상세에 포함되는 어르신 요약 응답입니다."""

    senior_id: int
    name: str
    gender: GenderEnum
    birth_date: date
    address: AddressResponse
    special_note: str | None
    ai_summary: str | None
    max_people: int

    @computed_field
    @property
    def age(self) -> int:
        """생년월일 기준 현재 만 나이."""

        return calculate_age_from_birth_date(self.birth_date)

    model_config = ConfigDict(from_attributes=True)


class HostingResponse(BaseModel):
    """호스팅 응답 스키마입니다."""

    hosting_id: int
    senior_id: int
    menu: str
    hosting_at: datetime
    hosting_end: datetime
    max_people: int
    current_people: int = Field(default=0, ge=0, description="현재 승인된 매칭 인원")
    address: AddressResponse
    hosting_status: HostingStatus
    created_at: datetime
    updated_at: datetime
    senior: HostingSeniorResponse | None = None

    model_config = ConfigDict(from_attributes=True)
