"""애플리케이션 스케줄러 (APScheduler 3.x 기반)."""

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
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


async def _delete_orphan_review_images(session: AsyncSession) -> int:
    """R2 공개버킷 안의 리뷰이미지 파일 중 db에 없는 파일 삭제."""
    if settings.DEBUG:
        return 0

    result = await session.execute(select(ReviewImg.image_url))
    db_urls = set(result.scalars().all())

    bucket = settings.R2_PUBLIC_BUCKET
    public_url = settings.R2_PUBLIC_URL

    orphan_count = 0
    for key in await asyncio.to_thread(list_r2_keys, bucket, "reviews/"):
        r2_url = f"{public_url}/{key}"
        if r2_url not in db_urls:
            if await asyncio.to_thread(delete_r2_key, bucket, key):
                orphan_count += 1

    return orphan_count


async def _run_hosting_job() -> None:
    """호스팅 상태 스케줄 잡."""
    try:
        async with AsyncSessionLocal() as session:
            changed_count = await run_hosting_status_scheduler(session=session)
            if changed_count > 0:
                logger.info("호스팅 상태 스케줄러 처리 완료: changed_count=%s", changed_count)
    except Exception:
        logger.exception("호스팅 상태 스케줄러 실행 중 오류가 발생했습니다.")


async def _run_cleanup_job() -> None:
    """고아 데이터 정리 스케줄 잡."""
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


def create_scheduler() -> AsyncIOScheduler:
    """APScheduler 인스턴스를 생성하고 잡을 등록합니다."""
    scheduler = AsyncIOScheduler(timezone="UTC")

    scheduler.add_job(
        _run_hosting_job,
        "interval",
        seconds=settings.SCHEDULER_INTERVAL_SECONDS,
        id="hosting_status",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),
    )

    scheduler.add_job(
        _run_cleanup_job,
        "interval",
        seconds=settings.CLEANUP_SCHEDULER_INTERVAL_SECONDS,
        id="cleanup",
        replace_existing=True,
    )

    logger.info(
        "스케줄러 등록 완료: hosting=%ss, cleanup=%ss",
        settings.SCHEDULER_INTERVAL_SECONDS,
        settings.CLEANUP_SCHEDULER_INTERVAL_SECONDS,
    )

    return scheduler
