"""후기 Pydantic 스키마."""

from datetime import datetime

from pydantic import BaseModel, Field


class ReviewImageResponse(BaseModel):
    """후기 이미지 응답 스키마."""

    image_id: int
    image_url: str

    model_config = {"from_attributes": True}


class ReviewCreateRequest(BaseModel):
    """후기 작성 요청 스키마."""

    match_id: int
    contents: str = Field(min_length=1, max_length=500)


class ReviewResponse(BaseModel):
    """후기 응답 스키마."""

    review_id: int
    matching_id: int
    vt_id: int
    contents: str
    images: list[ReviewImageResponse]
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": False}


class ReviewUpdateRequest(BaseModel):
    """후기 수정 요청 스키마."""

    contents: str = Field(min_length=1, max_length=500)
