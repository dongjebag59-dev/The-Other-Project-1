"""AI 요약 생성 서비스 (Gemini 기반)."""


from google import genai
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.hosting.models import Hosting
from app.domain.match.models import MatchingInfo
from app.domain.review.models import Review
from app.domain.senior.models import Senior

MIN_REVIEW_COUNT = 3  # AI 소개글 생성에 필요한 최소 후기 수

SUMMARY_PROMPT = """당신은 독거 어르신을 위한 식사 동반 플랫폼 '밥동무'의 AI 어시스턴트입니다.
봉사자들이 남긴 후기를 바탕으로, 어르신의 매력을 자연스럽게 소개하는 짧은 문구를 생성하세요.

어르신 이름: {senior_name}

규칙:
- 2~3문장, 따뜻하고 친근한 톤
- 어르신의 음식 솜씨, 성격, 분위기 등 긍정적 특성 중심
- 봉사자가 다시 방문하고 싶게 만드는 문구
- 개인정보(주소, 연락처 등)는 절대 포함하지 않을 것

후기 목록:
{reviews}

소개 문구:"""


async def generate_senior_summary(senior_name: str, reviews: list[str]) -> str:
    """후기 목록을 받아 어르신 AI 소개글을 생성합니다."""
    if len(reviews) < MIN_REVIEW_COUNT:
        raise ValueError(f"후기가 {MIN_REVIEW_COUNT}개 이상이어야 합니다.")

    prompt = SUMMARY_PROMPT.format(
        senior_name=senior_name,
        reviews="\n".join(f"- {r}" for r in reviews),
    )

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    models = [settings.GEMINI_MODEL, settings.GEMINI_MODEL_FALLBACK]
    last_error: Exception | None = None
    for model in models:
        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            last_error = e

    if last_error is None:
        raise RuntimeError("AI 모델 설정이 비어있습니다.")
    raise last_error


async def update_senior_ai_summary(senior_id: int, db: AsyncSession) -> str | None:
    """어르신의 후기를 조회하고 AI 요약을 갱신합니다.

    후기가 MIN_REVIEW_COUNT개 미만이면 None 반환.
    """
    # 해당 어르신의 호스팅에 달린 후기 내용 조회
    stmt = (
        select(Review.contents)
        .join(MatchingInfo, Review.matching_id == MatchingInfo.matching_id)
        .join(Hosting, MatchingInfo.hosting_id == Hosting.hosting_id)
        .where(Hosting.senior_id == senior_id)
    )
    result = await db.execute(stmt)
    reviews = [row for (row,) in result.fetchall()]

    if len(reviews) < MIN_REVIEW_COUNT:
        return None

    # 어르신 이름 조회 (프롬프트에 포함)
    senior_result = await db.execute(select(Senior).where(Senior.senior_id == senior_id))
    senior = senior_result.scalar_one_or_none()
    if senior is None:
        return None

    summary = await generate_senior_summary(senior.name, reviews)

    senior.ai_summary = summary
    await db.commit()

    return summary

