"""매칭 Pydantic 스키마."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.hosting.models import HostingStatus
from app.domain.match.models import MatchStatus


class MatchCreateRequest(BaseModel):
    """매칭 신청 요청 스키마."""

    hosting_id: int = Field(..., ge=1, description="신청할 호스팅 ID")


class MatchResponse(BaseModel):
    """매칭 기본 응답 스키마."""

    matching_id: int
    hosting_id: int
    vt_id: int
    senior_id: int
    match_status: MatchStatus
    check_in_time: datetime | None
    check_out_time: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VolunteerStatsResponse(BaseModel):
    """봉사자 마이페이지 통계 응답 스키마."""

    total_volunteer_minutes: int
    visit_count: int
    review_count: int
    senior_count: int


class MyMatchResponse(BaseModel):
    """내 매칭 목록 조회 전용 응답 스키마."""

    matching_id: int
    match_status: MatchStatus
    check_in_time: datetime | None
    check_out_time: datetime | None

    # 호스팅 정보
    hosting_id: int
    menu: str
    hosting_at: datetime
    hosting_status: HostingStatus

    # 시니어 정보
    senior_id: int
    senior_name: str
    senior_address: str

    # 봉사시간
    actual_volunteer_time: int | None

    # 후기
    has_review: bool
    review_id: int | None

    model_config = ConfigDict(from_attributes=False)


class MyMatchListResponse(BaseModel):
    """내 매칭 목록 페이징 응답 스키마."""

    total: int
    items: list[MyMatchResponse]


class MyMatchCheckResponse(BaseModel):
    """호스팅 신청 여부 조회 응답 스키마."""

    is_applied: bool
    matching_id: int | None
