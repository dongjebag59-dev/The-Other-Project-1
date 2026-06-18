"""어르신 요청/응답 스키마."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.domain.common.schemas import AddressCreate, AddressResponse
from app.domain.senior.models import GenderEnum

KST = ZoneInfo("Asia/Seoul")
MIN_SENIOR_AGE = 65


def calculate_age_from_birth_date(birth_date: date, today: date | None = None) -> int:
    """생년월일을 기준으로 현재 만 나이를 계산합니다."""

    base_date = today or datetime.now(KST).date()
    age = base_date.year - birth_date.year

    if (base_date.month, base_date.day) < (birth_date.month, birth_date.day):
        age -= 1

    return age


def validate_birth_date(value: date) -> date:
    """생년월일이 유효한지 검증합니다."""

    today = datetime.now(KST).date()

    if value > today:
        raise ValueError("생년월일은 오늘 이후 날짜로 입력할 수 없습니다.")

    if calculate_age_from_birth_date(value, today=today) < MIN_SENIOR_AGE:
        raise ValueError("어르신은 만 65세 이상이어야 합니다.")

    return value


class SeniorCreateRequest(BaseModel):
    """어르신 등록 요청 스키마입니다."""

    name: str = Field(..., min_length=1, max_length=100, description="어르신 이름")
    gender: GenderEnum = Field(..., description="성별")
    birth_date: date = Field(..., description="생년월일")
    address: AddressCreate = Field(..., description="주소")
    special_note: str | None = Field(default=None, description="특이사항")
    active_flag: bool = Field(default=True, description="활성 여부")
    max_people: int = Field(..., ge=2, le=4, description="최대 봉사자 인원")

    @field_validator("birth_date")
    @classmethod
    def validate_create_birth_date(cls, value: date) -> date:
        """등록 요청의 생년월일을 검증합니다."""

        return validate_birth_date(value)


class SeniorUpdateRequest(BaseModel):
    """어르신 수정 요청 스키마입니다."""

    name: str | None = Field(default=None, min_length=1, max_length=100, description="어르신 이름")
    gender: GenderEnum | None = Field(default=None, description="성별")
    birth_date: date | None = Field(default=None, description="생년월일")
    address: AddressCreate | None = Field(default=None, description="주소 (제공 시 전체 교체)")
    special_note: str | None = Field(default=None, description="특이사항")
    active_flag: bool | None = Field(default=None, description="활성 여부")
    max_people: int | None = Field(default=None, ge=2, le=4, description="최대 봉사자 인원")

    @field_validator("birth_date")
    @classmethod
    def validate_update_birth_date(cls, value: date | None) -> date | None:
        """수정 요청의 생년월일을 검증합니다."""

        if value is None:
            return value

        return validate_birth_date(value)


class SeniorResponse(BaseModel):
    """어르신 응답 스키마입니다."""

    senior_id: int
    guardian_id: int
    name: str
    gender: GenderEnum
    birth_date: date
    address: AddressResponse

    @computed_field
    @property
    def age(self) -> int:
        """생년월일 기준 현재 만 나이."""
        return calculate_age_from_birth_date(self.birth_date)

    special_note: str | None
    active_flag: bool
    ai_summary: str | None
    max_people: int
    qr_code: str | None

    total_hosting_count: int = 0
    open_hosting_count: int = 0
    full_hosting_count: int = 0
    fixed_hosting_count: int = 0
    in_progress_hosting_count: int = 0
    closed_hosting_count: int = 0
    failed_hosting_count: int = 0

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GuardianStatsResponse(BaseModel):
    """보호자 마이페이지 통계 응답 스키마."""

    senior_count: int
    active_hosting_count: int
    cancelled_hosting_count: int
    completed_hosting_count: int
