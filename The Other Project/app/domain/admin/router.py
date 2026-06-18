"""관리자 API 엔드포인트."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.hosting.models import Hosting, SmsLog
from app.domain.match.models import MatchingInfo, MatchStatus
from app.domain.senior.models import Senior
from app.domain.user.dependency import require_admin
from app.domain.user.models import CertFlag, Document, User, UserRole

router = APIRouter()


class RejectBody(BaseModel):
    cert_reject_reason: str | None = Field(default=None, max_length=500)


class VolunteerTimeRequest(BaseModel):
    actual_volunteer_time: int  # 분 단위


def _fmt(dt: datetime | None) -> str | None:
    """datetime을 UTC aware isoformat으로 직렬화합니다.

    SQLite는 naive datetime을 반환하므로 UTC로 간주하여 tzinfo를 보정합니다.
    PostgreSQL은 이미 aware datetime을 반환하므로 그대로 사용합니다.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


# ── 공개 통계 (랜딩페이지용, 인증 불필요) ────────────────────────────────────

@router.get("/public-stats")
async def get_public_stats(db: AsyncSession = Depends(get_db)) -> dict:
    """랜딩페이지 표시용 공개 통계를 반환합니다."""
    seniors = await db.scalar(
        select(func.count()).select_from(Senior)
        .where(Senior.active_flag.is_(True))
    )
    volunteers = await db.scalar(
        select(func.count()).select_from(User)
        .where(User.user_role == UserRole.VOLUNTEER, User.cert_flag == CertFlag.APPROVED)
    )
    total_meals = await db.scalar(
        select(func.count()).select_from(MatchingInfo)
        .where(MatchingInfo.check_out_time.is_not(None))
    )
    total_minutes = await db.scalar(
        select(func.coalesce(func.sum(MatchingInfo.actual_volunteer_time), 0))
        .select_from(MatchingInfo)
        .where(MatchingInfo.actual_volunteer_time.is_not(None))
    )
    return {
        "seniors": seniors,
        "volunteers": volunteers,
        "total_meals": total_meals,
        "total_volunteer_hours": int(total_minutes) // 60,
    }


# ── 통계 ──────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    """대시보드 통계를 반환합니다."""
    doc_pending = await db.scalar(
        select(func.count(User.user_id.distinct()))
        .select_from(Document)
        .join(User, Document.user_id == User.user_id)
        .where(User.cert_flag == CertFlag.PENDING)
    )
    approved_volunteers = await db.scalar(
        select(func.count()).select_from(User)
        .where(User.user_role == UserRole.VOLUNTEER, User.cert_flag == CertFlag.APPROVED)
    )
    total_volunteers = await db.scalar(
        select(func.count()).select_from(User)
        .where(User.user_role == UserRole.VOLUNTEER)
    )
    seniors = await db.scalar(
        select(func.count()).select_from(Senior)
        .where(Senior.active_flag.is_(True))
    )
    time_pending = await db.scalar(
        select(func.count()).select_from(MatchingInfo)
        .where(
            MatchingInfo.check_out_time.is_not(None),
            MatchingInfo.actual_volunteer_time.is_(None),
        )
    )
    # KST 기준 오늘 범위를 UTC로 변환해서 비교 (저장은 UTC, 비교는 KST 자정 기준)
    _kst = ZoneInfo("Asia/Seoul")
    today_start = datetime.now(_kst).replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    today_matches = await db.scalar(
        select(func.count()).select_from(MatchingInfo)
        .where(
            MatchingInfo.created_at >= today_start.astimezone(timezone.utc),
            MatchingInfo.created_at < today_end.astimezone(timezone.utc),
        )
    )

    return {
        "doc_pending": doc_pending,
        "approved_volunteers": approved_volunteers,
        "total_volunteers": total_volunteers,
        "seniors": seniors,
        "time_pending": time_pending,
        "today_matches": today_matches,
    }


# ── 서류 승인/반려 ──────────────────────────────────────────────────────────────

@router.get("/documents/pending")
async def list_pending_documents(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[dict]:
    """승인 대기 중인 서류 목록을 반환합니다."""
    result = await db.execute(
        select(Document, User)
        .join(User, Document.user_id == User.user_id)
        .where(User.cert_flag == CertFlag.PENDING)
        .order_by(User.created_at.asc(), Document.created_at.asc())
    )
    rows = result.all()

    # 유저별로 서류를 묶어서 반환
    grouped: dict[int, dict] = {}
    for doc, user in rows:
        if user.user_id not in grouped:
            grouped[user.user_id] = {
                "user_id": user.user_id,
                "user_name": user.name,
                "user_email": user.email,
                "user_role": user.user_role.value,
                "is_social_login": user.kakao_id is not None,
                "created_at": _fmt(user.created_at),
                "documents": [],
            }
        grouped[user.user_id]["documents"].append({
            "document_id": doc.document_id,
            "document_type": doc.document_type.value,
            "document_url": doc.document_url,
        })

    return list(grouped.values())


@router.patch("/users/{user_id}/approve", status_code=status.HTTP_200_OK)
async def approve_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    """유저를 승인하고 cert_flag를 approved로 변경합니다."""
    user_result = await db.execute(select(User).where(User.user_id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="유저를 찾을 수 없습니다."
        )

    user.cert_flag = CertFlag.APPROVED
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"user_id": user.user_id, "cert_flag": user.cert_flag.value}


@router.patch("/users/{user_id}/reject", status_code=status.HTTP_200_OK)
async def reject_user(
    user_id: int,
    body: RejectBody = RejectBody(),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    """유저를 반려하고 cert_flag를 rejected로 변경합니다."""
    user_result = await db.execute(select(User).where(User.user_id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="유저를 찾을 수 없습니다."
        )

    user.cert_flag = CertFlag.REJECTED
    user.cert_reject_reason = body.cert_reject_reason
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"user_id": user.user_id, "cert_flag": user.cert_flag.value}


# ── 최근 매칭 신청 ────────────────────────────────────────────────────────────

@router.get("/matches/recent")
async def list_recent_matches(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
    limit: int = 5,
) -> list[dict]:
    """최근 매칭 신청 목록을 반환합니다."""
    result = await db.execute(
        select(MatchingInfo, User, Hosting, Senior)
        .join(User, MatchingInfo.vt_id == User.user_id)
        .join(Hosting, MatchingInfo.hosting_id == Hosting.hosting_id)
        .join(Senior, Hosting.senior_id == Senior.senior_id)
        .order_by(MatchingInfo.created_at.desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "matching_id": m.matching_id,
            "volunteer_name": u.name,
            "senior_name": s.name,
            "hosting_at": _fmt(h.hosting_at),
            "match_status": m.match_status.value,
            "created_at": _fmt(m.created_at),
        }
        for m, u, h, s in rows
    ]


# ── 봉사시간 부여 ──────────────────────────────────────────────────────────────

@router.get("/matches/completed")
async def list_completed_matches(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[dict]:
    """체크아웃 완료 후 봉사시간 미부여 매칭 목록을 반환합니다."""
    result = await db.execute(
        select(MatchingInfo, User, Hosting, Senior)
        .join(User, MatchingInfo.vt_id == User.user_id)
        .join(Hosting, MatchingInfo.hosting_id == Hosting.hosting_id)
        .join(Senior, Hosting.senior_id == Senior.senior_id)
        .where(
            MatchingInfo.check_out_time.is_not(None),
            MatchingInfo.actual_volunteer_time.is_(None),
        )
        .order_by(MatchingInfo.check_out_time.asc())
    )
    rows = result.all()
    return [
        {
            "matching_id": m.matching_id,
            "volunteer_name": u.name,
            "senior_name": s.name,
            "check_in_time": _fmt(m.check_in_time),
            "check_out_time": _fmt(m.check_out_time),
            "expected_minutes": (
                int((h.hosting_end - h.hosting_at).total_seconds() // 60)
                if h.hosting_end else None
            ),
        }
        for m, u, h, s in rows
    ]


# ── 통계 페이지 API ───────────────────────────────────────────────────────────

@router.get("/stats/volunteers")
async def get_volunteer_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[dict]:
    """봉사자별 방문 횟수 및 봉사시간 합계를 반환합니다."""
    result = await db.execute(
        select(
            User.user_id,
            User.name,
            User.email,
            User.kakao_id,
            func.count(MatchingInfo.matching_id).label("visit_count"),
            func.coalesce(func.sum(MatchingInfo.actual_volunteer_time), 0).label("total_minutes"),
        )
        .join(MatchingInfo, MatchingInfo.vt_id == User.user_id)
        .where(
            User.user_role == UserRole.VOLUNTEER,
            MatchingInfo.match_status == MatchStatus.APPROVED,
            MatchingInfo.check_out_time.is_not(None),
        )
        .group_by(User.user_id, User.kakao_id)
        .order_by(func.count(MatchingInfo.matching_id).desc())
    )
    rows = result.all()
    return [
        {
            "user_id": r.user_id,
            "name": r.name,
            "email": r.email,
            "is_social_login": r.kakao_id is not None,
            "visit_count": r.visit_count,
            "total_minutes": r.total_minutes,
        }
        for r in rows
    ]


@router.get("/stats/not-visited")
async def get_not_visited_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    """not_visited 매칭 목록과 총 건수를 반환합니다.

    total_closed: 체크아웃 완료 + not_visited 합계 (미방문율 계산용)
    """
    from sqlalchemy import or_

    result = await db.execute(
        select(MatchingInfo, User, Senior)
        .join(User, MatchingInfo.vt_id == User.user_id)
        .join(Senior, MatchingInfo.senior_id == Senior.senior_id)
        .where(MatchingInfo.match_status == MatchStatus.NOT_VISITED)
        .order_by(MatchingInfo.created_at.desc())
    )
    rows = result.all()
    items = [
        {
            "matching_id": m.matching_id,
            "volunteer_name": u.name,
            "volunteer_email": u.email,
            "is_social_login": u.kakao_id is not None,
            "senior_name": s.name,
            "created_at": _fmt(m.created_at),
        }
        for m, u, s in rows
    ]
    # 체크아웃 완료(방문) + 미방문 = 실제 방문 예정이었던 매칭 전체
    total_closed = await db.scalar(
        select(func.count()).select_from(MatchingInfo)
        .where(
            or_(
                MatchingInfo.match_status == MatchStatus.NOT_VISITED,
                MatchingInfo.check_out_time.is_not(None),
            )
        )
    )
    return {"total": len(items), "total_closed": total_closed, "items": items}


@router.get("/stats/sms-failures")
async def get_sms_failure_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    """SMS 발송 실패 목록과 총 건수를 반환합니다."""
    result = await db.execute(
        select(SmsLog, User)
        .join(User, SmsLog.receiver_id == User.user_id)
        .where(SmsLog.is_send.is_(False))
        .order_by(SmsLog.created_at.desc())
    )
    rows = result.all()
    items = [
        {
            "sms_id": s.sms_id,
            "receiver_name": u.name,
            "receiver_email": u.email,
            "is_social_login": u.kakao_id is not None,
            "alarm_type": s.alarm_type.value,
            "contents": s.contents,
            "created_at": _fmt(s.created_at),
        }
        for s, u in rows
    ]
    return {"total": len(items), "items": items}


@router.patch("/matches/{matching_id}/volunteer-time", status_code=status.HTTP_200_OK)
async def grant_volunteer_time(
    matching_id: int,
    payload: VolunteerTimeRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    """봉사시간을 최종 부여합니다."""
    result = await db.execute(select(MatchingInfo).where(MatchingInfo.matching_id == matching_id))
    match = result.scalar_one_or_none()
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="매칭을 찾을 수 없습니다."
        )
    match.actual_volunteer_time = payload.actual_volunteer_time
    await db.commit()
    return {"matching_id": matching_id, "actual_volunteer_time": payload.actual_volunteer_time}
