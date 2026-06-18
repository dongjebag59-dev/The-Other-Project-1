"""후기 비즈니스 로직."""

import logging

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.database import AsyncSessionLocal
from app.domain.match.models import MatchingInfo, MatchStatus
from app.domain.review.models import Review, ReviewImg
from app.domain.review.schemas import ReviewImageResponse, ReviewResponse
from app.services.ai import update_senior_ai_summary
from app.services.r2 import delete_image


async def _get_review_or_raise(db: AsyncSession, review_id: int, vt_id: int) -> Review:
    """후기를 조회하고 본인 여부를 확인합니다."""
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="존재하지 않는 후기입니다.")
    if review.vt_id != vt_id:
        raise HTTPException(status_code=403, detail="본인 후기만 이용할 수 있습니다.")
    return review


async def _get_images(db: AsyncSession, review_id: int) -> list[ReviewImg]:
    """후기 이미지 목록을 조회합니다."""
    result = await db.execute(select(ReviewImg).where(ReviewImg.review_id == review_id))
    return list(result.scalars().all())


async def run_ai_summary_bg(match_id: int) -> None:
    """AI 소개글 갱신 백그라운드 태스크 — 독립 세션으로 실행."""
    async with AsyncSessionLocal() as db:
        match = await db.get(MatchingInfo, match_id)
        if match is None:
            return
        senior_id = match.senior_id
        try:
            await update_senior_ai_summary(senior_id, db)
        except Exception as e:
            logger.warning("AI 소개글 생성 실패: senior_id=%s error=%s", senior_id, e)


async def create_review(
    db: AsyncSession,
    match_id: int,
    vt_id: int,
    contents: str,
    image_urls: list[str],
) -> ReviewResponse:
    """후기를 작성합니다."""
    # 매칭 존재 여부 및 본인 확인
    match = await db.get(MatchingInfo, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="존재하지 않는 매칭입니다.")
    if match.vt_id != vt_id:
        raise HTTPException(status_code=403, detail="본인 매칭에만 후기를 작성할 수 있습니다.")

    # 체크아웃 완료된 매칭만 후기 작성 가능
    if not match.check_out_time:
        raise HTTPException(status_code=400, detail="체크아웃 완료 후 후기를 작성할 수 있습니다.")

    # 취소 또는 미방문 매칭은 후기 불가
    if match.match_status in (MatchStatus.CANCELLED, MatchStatus.NOT_VISITED):
        raise HTTPException(status_code=400, detail="후기를 작성할 수 없는 매칭입니다.")

    # 중복 후기 방지
    result = await db.execute(
        select(Review).where(Review.matching_id == match_id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 후기를 작성한 매칭입니다.")

    # 후기 생성
    review = Review(matching_id=match_id, vt_id=vt_id, contents=contents)
    db.add(review)
    await db.flush()

    # 이미지 저장 (최대 5개)
    if len(image_urls) > 5:
        raise HTTPException(status_code=400, detail="이미지는 최대 5개까지 첨부할 수 있습니다.")

    images = []
    for url in image_urls:
        img = ReviewImg(review_id=review.review_id, image_url=url)
        db.add(img)
        images.append(img)

    await db.commit()
    await db.refresh(review)

    logger.info(
        "후기 작성 완료: review_id=%s match_id=%s vt_id=%s",
        review.review_id, match_id, vt_id,
    )

    return _to_response(review, images)


async def get_review(db: AsyncSession, review_id: int) -> ReviewResponse:
    """후기 단건을 조회합니다."""
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="존재하지 않는 후기입니다.")

    images = await _get_images(db, review_id)
    return _to_response(review, images)


async def list_reviews_by_senior(
    db: AsyncSession,
    senior_id: int,
) -> list[ReviewResponse]:
    """어르신별 후기 목록을 조회합니다."""
    result = await db.execute(
        select(Review)
        .join(MatchingInfo, Review.matching_id == MatchingInfo.matching_id)
        .where(MatchingInfo.senior_id == senior_id)
        .order_by(Review.created_at.desc(), Review.review_id.desc())
    )
    reviews = result.scalars().all()

    response = []
    for review in reviews:
        images = await _get_images(db, review.review_id)
        response.append(_to_response(review, images))

    return response


async def update_review(
    db: AsyncSession,
    review_id: int,
    vt_id: int,
    contents: str,
) -> ReviewResponse:
    """후기를 수정합니다."""
    review = await _get_review_or_raise(db, review_id, vt_id)
    review.contents = contents
    await db.commit()
    await db.refresh(review)

    images = await _get_images(db, review_id)
    return _to_response(review, images)


async def add_review_image(
    db: AsyncSession,
    review_id: int,
    vt_id: int,
    image_url: str,
) -> ReviewResponse:
    """후기에 이미지를 추가합니다."""
    review = await _get_review_or_raise(db, review_id, vt_id)

    images = await _get_images(db, review_id)
    if len(images) >= 5:
        raise HTTPException(status_code=400, detail="이미지는 최대 5개까지 첨부할 수 있습니다.")

    img = ReviewImg(review_id=review_id, image_url=image_url)
    db.add(img)
    await db.commit()

    # 이미 조회한 목록에 추가해 재쿼리 방지
    images.append(img)
    return _to_response(review, images)


async def delete_review_image(
    db: AsyncSession,
    review_id: int,
    image_id: int,
    vt_id: int,
) -> ReviewResponse:
    """후기 이미지를 삭제합니다."""
    review = await _get_review_or_raise(db, review_id, vt_id)

    img = await db.get(ReviewImg, image_id)
    if not img or img.review_id != review_id:
        raise HTTPException(status_code=404, detail="존재하지 않는 이미지입니다.")

    # R2에서 파일 삭제
    await delete_image(img.image_url)

    await db.delete(img)
    await db.commit()

    images = await _get_images(db, review_id)
    return _to_response(review, images)


async def delete_review(
    db: AsyncSession,
    review_id: int,
    vt_id: int,
) -> None:
    """후기를 삭제합니다."""
    review = await _get_review_or_raise(db, review_id, vt_id)

    # R2 파일 삭제 후 DB에서도 명시적으로 삭제 (SQLite는 CASCADE 미지원)
    images = await _get_images(db, review_id)
    for img in images:
        await delete_image(img.image_url)
        await db.delete(img)

    await db.delete(review)
    await db.commit()


def _to_response(review: Review, images: list[ReviewImg]) -> ReviewResponse:
    """Review 모델을 ReviewResponse로 변환합니다."""
    return ReviewResponse(
        review_id=review.review_id,
        matching_id=review.matching_id,
        vt_id=review.vt_id,
        contents=review.contents,
        images=[
            ReviewImageResponse(image_id=img.image_id, image_url=img.image_url)
            for img in images
        ],
        created_at=review.created_at,
        updated_at=review.updated_at,
    )
