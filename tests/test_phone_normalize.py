"""전화번호 정규화 validator 테스트."""

import pytest
from pydantic import ValidationError

from app.domain.user.schemas import (
    KakaoSetupRequest,
    SmsSendRequest,
    SmsVerifyRequest,
    UserRegisterRequest,
)
from app.domain.common.schemas import AddressCreate
from app.domain.user.models import UserRole


# ── 정규화 통과 케이스 ─────────────────────────────────────────────
@pytest.mark.parametrize("raw, expected", [
    ("01012345678",      "01012345678"),  # 이미 정규화된 형태
    ("010-1234-5678",    "01012345678"),  # 하이픈 제거
    ("010 1234 5678",    "01012345678"),  # 공백 제거
    (" 010-1234-5678 ", "01012345678"),  # 앞뒤 공백 + 하이픈
])
def test_normalize_phone_valid(raw, expected):
    req = SmsSendRequest(phone_number=raw)
    assert req.phone_number == expected


# ── 정규화 거부 케이스 ─────────────────────────────────────────────
@pytest.mark.parametrize("raw", [
    "0101234567",    # 10자리 (짧음)
    "010123456789",  # 12자리 (김)
    "02-1234-5678",  # 02 시작
    "011-1234-5678", # 011 시작
    "abc",
])
def test_normalize_phone_invalid(raw):
    with pytest.raises(ValidationError):
        SmsSendRequest(phone_number=raw)


# ── 4개 스키마 모두 validator 붙어있는지 확인 ───────────────────────
def test_sms_verify_request_normalizes():
    req = SmsVerifyRequest(phone_number="010-1234-5678", code="123456")
    assert req.phone_number == "01012345678"


def test_user_register_request_normalizes():
    address = AddressCreate(
        road_address="서울특별시 성북구 정릉로 77",
        detail_address="101호",
        sigungu="성북구",
    )
    req = UserRegisterRequest(
        email="test@example.com",
        password="password123",
        password_confirm="password123",
        name="테스트",
        phone_number="010-1234-5678",
        user_role=UserRole.VOLUNTEER,
        address=address,
    )
    assert req.phone_number == "01012345678"


def test_kakao_setup_request_normalizes():
    address = AddressCreate(
        road_address="서울특별시 성북구 정릉로 77",
        detail_address="101호",
        sigungu="성북구",
    )
    req = KakaoSetupRequest(
        setup_token="dummy_token",
        name="테스트",
        phone_number="010-1234-5678",
        user_role=UserRole.GUARDIAN,
        address=address,
    )
    assert req.phone_number == "01012345678"
