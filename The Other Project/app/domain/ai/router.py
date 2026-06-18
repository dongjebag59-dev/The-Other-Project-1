"""AI 관련 API 엔드포인트."""

from fastapi import APIRouter, Depends, HTTPException, status
from google.genai.errors import ServerError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.senior.models import Senior
from app.domain.user.dependency import get_current_user, require_admin
from app.domain.user.models import User
from app.services.ai import MIN_REVIEW_COUNT, update_senior_ai_summary

router = APIRouter()


@router.post("/seniors/{senior_id}/summary", status_code=status.HTTP_200_OK)
async def generate_summary(
    senior_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> dict:
    """어르신 AI 소개글을 생성/갱신합니다 (관리자 전용).

    TODO: 후기 작성 시 자동 생성되도록 review/service.py에 훅 추가 필요
          (후기 저장 후 해당 어르신 후기 수 >= MIN_REVIEW_COUNT이면 update_senior_ai_summary 호출)
    """
    try:
        summary = await update_senior_ai_summary(senior_id, db)
    except ServerError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini 서버 과부하로 AI 소개글 생성에 실패했습니다. 잠시 후 다시 시도해주세요.",
        )

    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"후기가 {MIN_REVIEW_COUNT}개 이상이어야 AI 소개글을 생성할 수 있습니다.",
        )

    return {"senior_id": senior_id, "ai_summary": summary}


@router.get("/seniors/{senior_id}/summary")
async def get_summary(
    senior_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """어르신 AI 소개글을 조회합니다."""
    result = await db.execute(select(Senior).where(Senior.senior_id == senior_id))
    senior = result.scalar_one_or_none()

    if senior is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="어르신을 찾을 수 없습니다."
        )

    return {"senior_id": senior_id, "ai_summary": senior.ai_summary}
