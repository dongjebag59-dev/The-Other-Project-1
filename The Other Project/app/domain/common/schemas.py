"""공통 Pydantic 스키마."""

from pydantic import BaseModel, ConfigDict


class AddressCreate(BaseModel):
    """주소 생성 스키마."""

    road_address: str
    jibun_address: str | None = None
    zonecode: str | None = None
    sigungu: str
    bname: str | None = None
    detail_address: str = ""
    sido: str | None = None
    building_name: str | None = None
    is_apartment: bool | None = None
    lat: float | None = None
    lng: float | None = None
    sigungu_code: str | None = None


class AddressResponse(AddressCreate):
    """주소 응답 스키마."""

    address_id: int

    model_config = ConfigDict(from_attributes=True)
