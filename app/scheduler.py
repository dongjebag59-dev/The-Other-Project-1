"""애플리케이션 스케줄러."""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.domain.hosting.service import run_hosting_status_scheduler
from app.domain.review.models import ReviewImg
from app.domain.user.service import (
    delete_duplicate_documents,
    delete_expired_phone_verifications,
    delete_orphan_r2_documents,
)
from app.services.r2 import delete_r2_key, list_r2_keys

logger = logging.getLogger(__name__)


async def hosting_scheduler_loop() -> None:
    """호스팅 상태 스케줄러를 주기적으로 실행합니다."""

    logger.info(
        "호스팅 상태 스케줄러를 시작합니다. interval_seconds=%s",
        settings.SCHEDULER_INTERVAL_SECONDS,
    )

    try:
        while True:
            try:
                async with AsyncSessionLocal() as session:
                    changed_count = await run_hosting_status_scheduler(session=session)

                    if changed_count > 0:
                        logger.info(
                            "호스팅 상태 스케줄러 처리 완료: changed_count=%s",
                            changed_count,
                        )

            except Exception:
                logger.exception("호스팅 상태 스케줄러 실행 중 오류가 발생했습니다.")

            await asyncio.sleep(settings.SCHEDULER_INTERVAL_SECONDS)

    except asyncio.CancelledError:
        logger.info("호스팅 상태 스케줄러를 종료합니다.")
        raise


# cleanup_scheduler_loop(정리 스케줄러)에서만 호출하는 내부 헬퍼 함수
async def _delete_orphan_review_images(session: AsyncSession) -> int:
    """R2 공개버킷 안의 리뷰이미지 파일 중 db에 없는 파일 삭제(삭제된 수 반환)"""
    # 로컬 개발환경에서는 팀원마다 DB가 달라 다른 팀원 파일을 고아로 오인할 수 있음
    if settings.DEBUG:
        return 0

    result = await session.execute(select(ReviewImg.image_url))
    db_urls = set(result.scalars().all())

    bucket = settings.R2_PUBLIC_BUCKET
    public_url = settings.R2_PUBLIC_URL

    # delete_orphan_r2_documents 함수와 구조 같음
    orphan_count = 0
    for key in await asyncio.to_thread(list_r2_keys, bucket, "reviews/"):
        r2_url = f"{public_url}/{key}"
        if r2_url not in db_urls:
            if await asyncio.to_thread(delete_r2_key, bucket, key):
                orphan_count += 1

    return orphan_count


# 기존 호스팅 스케줄러와 동일한 구조
async def cleanup_scheduler_loop() -> None:
    """고아 데이터 정리 스케줄러를 하루에 한 번 실행합니다."""

    logger.info("정리 스케줄러를 등록했습니다. 24시간 후 첫 실행됩니다.")

    try:
        while True:
            await asyncio.sleep(settings.CLEANUP_SCHEDULER_INTERVAL_SECONDS)

            try:
                async with AsyncSessionLocal() as session:
                    pv_count = await delete_expired_phone_verifications(session)
                    dup_count = await delete_duplicate_documents(session)
                    doc_count = await delete_orphan_r2_documents(session)
                    img_count = await _delete_orphan_review_images(session)

                    logger.info(
                        "정리 스케줄러 완료: 만료인증=%s 중복서류=%s 고아서류=%s 고아리뷰사진=%s",
                        pv_count,
                        dup_count,
                        doc_count,
                        img_count,
                    )

            except Exception:
                logger.exception("정리 스케줄러 실행 중 오류가 발생했습니다.")

    # 서버 꺼질때
    except asyncio.CancelledError:
        logger.info("정리 스케줄러를 종료합니다.")
        raise
