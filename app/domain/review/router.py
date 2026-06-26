"""후기 API 엔드포인트."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.review import service
from app.domain.review.schemas import ReviewResponse, ReviewUpdateRequest
from app.domain.user.dependency import require_volunteer
from app.services.r2 import BucketType, delete_image, upload_image

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=ReviewResponse)
async def create_review(
    background_tasks: BackgroundTasks,
    match_id: int = Form(...),
    contents: str = Form(..., min_length=1, max_length=500),
    images: list[UploadFile] = File(default=[]),
    current_user=Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """후기를 작성합니다."""

    if len(images) > 5:
        raise HTTPException(status_code=400, detail="이미지는 최대 5개까지 첨부할 수 있습니다.")

    image_urls: list[str] = []
    for image in images:
        if image.filename:
            url = await upload_image(image, folder="reviews", bucket=BucketType.PUBLIC)
            image_urls.append(url)

    try:
        response = await service.create_review(
            db=db,
            match_id=match_id,
            vt_id=current_user.user_id,
            contents=contents,
            image_urls=image_urls,
        )
    except Exception:
        for url in image_urls:
            try:
                await delete_image(url)
            except Exception as e:
                logger.warning("R2 롤백 실패: %s", e)
        raise

    background_tasks.add_task(service.run_ai_summary_bg, match_id)
    return response


@router.get("/senior/{senior_id}", response_model=list[ReviewResponse])
async def list_reviews_by_senior(
    senior_id: int,
    current_user=Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
) -> list[ReviewResponse]:
    """어르신별 후기 목록을 조회합니다."""
    return await service.list_reviews_by_senior(db=db, senior_id=senior_id)


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: int,
    current_user=Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """후기 단건을 조회합니다."""
    return await service.get_review(db=db, review_id=review_id)


@router.patch("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    request: ReviewUpdateRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """후기를 수정합니다."""
    response = await service.update_review(
        db=db,
        review_id=review_id,
        vt_id=current_user.user_id,
        contents=request.contents,
    )
    background_tasks.add_task(service.run_ai_summary_bg, response.matching_id)
    return response


@router.post("/{review_id}/images", response_model=ReviewResponse)
async def add_review_image(
    review_id: int,
    image: UploadFile = File(...),
    current_user=Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """후기에 이미지를 추가합니다."""
    image_url = await upload_image(image, folder="reviews", bucket=BucketType.PUBLIC)
    try:
        return await service.add_review_image(
            db=db,
            review_id=review_id,
            vt_id=current_user.user_id,
            image_url=image_url,
        )
    except Exception:
        try:
            await delete_image(image_url)
        except Exception as e:
            logger.warning("R2 롤백 실패: %s", e)
        raise


@router.delete("/{review_id}/images/{image_id}", response_model=ReviewResponse)
async def delete_review_image(
    review_id: int,
    image_id: int,
    current_user=Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """후기 이미지를 삭제합니다."""
    return await service.delete_review_image(
        db=db,
        review_id=review_id,
        image_id=image_id,
        vt_id=current_user.user_id,
    )


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: int,
    current_user=Depends(require_volunteer),
    db: AsyncSession = Depends(get_db),
) -> None:
    """후기를 삭제합니다."""
    await service.delete_review(
        db=db,
        review_id=review_id,
        vt_id=current_user.user_id,
    )
