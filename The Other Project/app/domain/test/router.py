"""SMS 서비스 테스트용 라우터.

개발/QA 목적의 임시 엔드포인트입니다. 실제 운영 트리거(호스팅 신청/체크인 등)와
무관하게 sms 서비스 함수를 직접 호출해 발송 여부를 확인합니다.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.database import get_db
from app.domain.hosting.models import AlarmType, Hosting
from app.domain.match.models import MatchingInfo, MatchStatus
from app.domain.review.models import Review
from app.domain.senior.models import GenderEnum, Senior
from app.domain.user.models import CertFlag, User, UserRole
from app.services.ai import update_senior_ai_summary
from app.services.sms import send_auth_sms, send_sms

router = APIRouter()


class AuthSmsRequest(BaseModel):
    receiver_phone: str
    auth_code: str = "123456"


class NotificationSmsRequest(BaseModel):
    hosting_id: int
    receiver_id: int
    alarm_type: AlarmType  # MATCH | CHECKIN | CHECKOUT | UPDATE
    volunteer_id: int | None = None
    use_long_message: bool = False


class SeedRequest(BaseModel):
    receiver_phone: str  # 보호자(수신자) 실제 번호 — 본인 번호 권장
    volunteer_phone: str | None = None


@router.post("/match/seed")
async def seed_match_test_data(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """매칭 테스트용 더미 데이터를 생성합니다.

    봉사자 User → 보호자 User → 어르신 Senior → 호스팅 Hosting 순으로 만들고
    로그인 정보와 생성된 ID들을 반환합니다.
    """
    suffix = datetime.now().strftime("%Y%m%d%H%M%S")
    password = "test1234"

    volunteer = User(
        name="테스트봉사자",
        email=f"test-vt-{suffix}@example.com",
        password=hash_password(password),
        phone_number="",
        address="테스트 주소",
        user_role=UserRole.VOLUNTEER,
        cert_flag=CertFlag.APPROVED,
    )
    db.add(volunteer)

    guardian = User(
        name="테스트보호자",
        email=f"test-guardian-{suffix}@example.com",
        password=hash_password(password),
        phone_number="",
        address="테스트 주소",
        user_role=UserRole.GUARDIAN,
        cert_flag=CertFlag.APPROVED,
    )
    db.add(guardian)
    await db.flush()

    qr = str(uuid.uuid4())
    senior = Senior(
        guardian_id=guardian.user_id,
        name="테스트어르신",
        gender=GenderEnum.FEMALE,
        age=80,
        road_address="경기도 고양시 일산동구 테스트로 1",
        sigungu="고양시 일산동구",
        detail_address="101호",
        max_people=2,
        qr_code=qr,
    )
    db.add(senior)
    await db.flush()

    hosting = Hosting(
        senior_id=senior.senior_id,
        menu="된장찌개",
        hosting_at=datetime.now(timezone.utc),
        hosting_end=datetime.now(timezone.utc) + timedelta(hours=2),
        max_people=2,
        road_address="경기도 고양시 일산동구 테스트로 1",
        sigungu="고양시 일산동구",
        detail_address="101호",
    )
    db.add(hosting)
    await db.flush()

    match = MatchingInfo(
        hosting_id=hosting.hosting_id,
        vt_id=volunteer.user_id,
        senior_id=senior.senior_id,
        match_status=MatchStatus.APPROVED,
    )
    db.add(match)
    await db.flush()

    await db.commit()

    return {
        "volunteer_email": volunteer.email,
        "volunteer_password": password,
        "volunteer_id": volunteer.user_id,
        "hosting_id": hosting.hosting_id,
        "senior_id": senior.senior_id,
        "qr_uuid": qr,
    }


@router.post("/apply/seed")
async def seed_apply_test_data(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """매칭 신청 테스트용 더미 데이터를 생성합니다. (내일 호스팅 — 신청 가능 상태)"""
    suffix = datetime.now().strftime("%Y%m%d%H%M%S")
    password = "test1234"

    volunteer = User(
        name="테스트봉사자",
        email=f"test-vt-{suffix}@example.com",
        password=hash_password(password),
        phone_number="",
        address="테스트 주소",
        user_role=UserRole.VOLUNTEER,
        cert_flag=CertFlag.APPROVED,
    )
    db.add(volunteer)

    guardian = User(
        name="테스트보호자",
        email=f"test-guardian-{suffix}@example.com",
        password=hash_password(password),
        phone_number="",
        address="테스트 주소",
        user_role=UserRole.GUARDIAN,
        cert_flag=CertFlag.APPROVED,
    )
    db.add(guardian)
    await db.flush()

    qr = str(uuid.uuid4())
    senior = Senior(
        guardian_id=guardian.user_id,
        name="테스트어르신",
        gender=GenderEnum.FEMALE,
        age=80,
        road_address="경기도 고양시 일산동구 테스트로 1",
        sigungu="고양시 일산동구",
        detail_address="101호",
        max_people=2,
        qr_code=qr,
    )
    db.add(senior)
    await db.flush()

    hosting = Hosting(
        senior_id=senior.senior_id,
        menu="된장찌개",
        hosting_at=datetime.now(timezone.utc) + timedelta(days=1),
        hosting_end=datetime.now(timezone.utc) + timedelta(days=1, hours=2),
        max_people=2,
        road_address="경기도 고양시 일산동구 테스트로 1",
        sigungu="고양시 일산동구",
        detail_address="101호",
    )
    db.add(hosting)
    await db.flush()

    await db.commit()

    return {
        "volunteer_email": volunteer.email,
        "volunteer_password": password,
        "volunteer_id": volunteer.user_id,
        "hosting_id": hosting.hosting_id,
        "senior_id": senior.senior_id,
        "qr_uuid": qr,
    }


@router.post("/review/seed")
async def seed_review_test_data(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """AI 요약 테스트용 후기 3개 더미 데이터를 생성합니다."""
    suffix = datetime.now().strftime("%Y%m%d%H%M%S")
    password = "test1234"
    now = datetime.now(timezone.utc)

    volunteer = User(
        name="테스트봉사자",
        email=f"test-vt-{suffix}@example.com",
        password=hash_password(password),
        phone_number="",
        address="테스트 주소",
        user_role=UserRole.VOLUNTEER,
        cert_flag=CertFlag.APPROVED,
    )
    db.add(volunteer)

    guardian = User(
        name="테스트보호자",
        email=f"test-guardian-{suffix}@example.com",
        password=hash_password(password),
        phone_number="",
        address="테스트 주소",
        user_role=UserRole.GUARDIAN,
        cert_flag=CertFlag.APPROVED,
    )
    db.add(guardian)
    await db.flush()

    senior = Senior(
        guardian_id=guardian.user_id,
        name="테스트어르신",
        gender=GenderEnum.FEMALE,
        age=80,
        road_address="경기도 고양시 일산동구 테스트로 1",
        sigungu="고양시 일산동구",
        detail_address="101호",
        max_people=3,
    )
    db.add(senior)
    await db.flush()

    contents_list = [
        "정말 따뜻하게 맞아주셔서 감사했습니다. 다음에 또 뵙고 싶어요.",
        "어르신이 직접 만들어주신 음식이 너무 맛있었어요. 행복한 시간이었습니다.",
        "혼자 계시는 게 안쓰러웠는데 제가 조금이나마 도움이 됐으면 좋겠어요.",
    ]

    for i, contents in enumerate(contents_list):
        hosting = Hosting(
            senior_id=senior.senior_id,
            menu="된장찌개",
            hosting_at=now - timedelta(days=i + 1),
            hosting_end=now - timedelta(days=i + 1) + timedelta(hours=2),
            max_people=3,
            road_address="경기도 고양시 일산동구 테스트로 1",
            sigungu="고양시 일산동구",
            detail_address="101호",
        )
        db.add(hosting)
        await db.flush()

        match = MatchingInfo(
            hosting_id=hosting.hosting_id,
            vt_id=volunteer.user_id,
            senior_id=senior.senior_id,
            match_status=MatchStatus.APPROVED,
            check_in_time=now - timedelta(days=i + 1, hours=2),
            check_out_time=now - timedelta(days=i + 1),
        )
        db.add(match)
        await db.flush()

        review = Review(
            matching_id=match.matching_id,
            vt_id=volunteer.user_id,
            contents=contents,
        )
        db.add(review)
        await db.flush()

    await db.commit()

    try:
        await update_senior_ai_summary(senior.senior_id, db)
    except Exception:
        logging.getLogger(__name__).exception("AI 요약 생성 실패 (senior_id=%s)", senior.senior_id)

    return {
        "senior_id": senior.senior_id,
        "volunteer_email": volunteer.email,
        "volunteer_password": password,
        "message": "후기 3개 생성 완료. ai/seniors/{senior_id}/summary에서 확인하세요.",
    }


@router.post("/qr/seed")
async def seed_qr_test_data(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """QR 코드 테스트용 보호자 + 어르신 더미 데이터를 생성합니다."""

    suffix = datetime.now().strftime("%Y%m%d%H%M%S")
    password = "test1234"

    guardian = User(
        name="테스트보호자",
        email=f"test-guardian-{suffix}@example.com",
        password=hash_password(password),
        phone_number="",
        address="테스트 주소",
        user_role=UserRole.GUARDIAN,
        cert_flag=CertFlag.APPROVED,
    )
    db.add(guardian)
    await db.flush()

    qr = str(uuid.uuid4())
    senior = Senior(
        guardian_id=guardian.user_id,
        name="테스트어르신",
        gender=GenderEnum.FEMALE,
        age=80,
        road_address="경기도 고양시 일산동구 테스트로 1",
        sigungu="고양시 일산동구",
        detail_address="101호",
        max_people=2,
        qr_code=qr,
    )
    db.add(senior)
    await db.commit()

    return {
        "guardian_email": guardian.email,
        "guardian_password": password,
        "senior_id": senior.senior_id,
        "qr_uuid": qr,
        "message": f"GET /api/v1/seniors/{senior.senior_id}/qr 로 QR 이미지 확인하세요.",
    }


@router.post("/sms/seed")
async def seed_sms_test_data(
    payload: SeedRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """알림 SMS 테스트용 더미 데이터를 생성합니다.

    보호자 User → 어르신 Senior → 호스팅 Hosting → 봉사자 User 순으로 만들고
    생성된 ID들을 반환합니다. 반환된 hosting_id/receiver_id/volunteer_id를
    아래 알림 SMS 폼에 그대로 입력하면 됩니다.
    """
    suffix = datetime.now().strftime("%Y%m%d%H%M%S")

    guardian = User(
        name="테스트보호자",
        email=f"test-guardian-{suffix}@example.com",
        password="x",
        phone_number=payload.receiver_phone,
        address="테스트 주소",
        user_role=UserRole.GUARDIAN,
        cert_flag=CertFlag.APPROVED,
    )
    db.add(guardian)
    await db.flush()

    volunteer = User(
        name="테스트봉사자",
        email=f"test-volunteer-{suffix}@example.com",
        password="x",
        # 봉사자 phone은 SMS 수신에 쓰이지 않지만, 잘못된 트리거로 발송될 위험을 막기 위해
        # 별도 입력이 없으면 보호자(receiver)와 동일한 번호로 둔다.
        phone_number=payload.volunteer_phone or payload.receiver_phone,
        address="테스트 주소",
        user_role=UserRole.VOLUNTEER,
        cert_flag=CertFlag.APPROVED,
    )
    db.add(volunteer)
    await db.flush()

    senior = Senior(
        guardian_id=guardian.user_id,
        name="테스트어르신",
        gender=GenderEnum.FEMALE,
        age=80,
        road_address="경기도 고양시 일산동구 테스트로 1",
        sigungu="고양시 일산동구",
        detail_address="101호",
        max_people=2,
    )
    db.add(senior)
    await db.flush()

    hosting = Hosting(
        senior_id=senior.senior_id,
        menu="된장찌개",
        hosting_at=datetime.now(timezone.utc) + timedelta(days=1),
        hosting_end=datetime.now(timezone.utc) + timedelta(days=1, hours=2),
        max_people=2,
        road_address="경기도 고양시 일산동구 테스트로 1",
        sigungu="고양시 일산동구",
        detail_address="101호",
    )
    db.add(hosting)
    await db.flush()

    await db.commit()

    return {
        "hosting_id": hosting.hosting_id,
        "receiver_id": guardian.user_id,
        "volunteer_id": volunteer.user_id,
        "senior_id": senior.senior_id,
    }


@router.post("/sms/auth")
async def test_auth_sms(payload: AuthSmsRequest) -> dict:
    """인증 SMS 발송 테스트 (DB 불필요)."""
    ok = await send_auth_sms(payload.receiver_phone, payload.auth_code)
    if not ok:
        raise HTTPException(status_code=500, detail="SMS 발송 실패")
    return {"success": True}


@router.post("/sms/notification")
async def test_notification_sms(
    payload: NotificationSmsRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """호스팅 알림 SMS 발송 테스트 (DB에 hosting/user 데이터 필요)."""
    ok = await send_sms(
        db=db,
        hosting_id=payload.hosting_id,
        receiver_id=payload.receiver_id,
        alarm_type=payload.alarm_type,
        volunteer_id=payload.volunteer_id,
        use_long_message=payload.use_long_message,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="SMS 발송 실패 (수신자 정보/발송 오류 확인)")
    return {"success": True}
