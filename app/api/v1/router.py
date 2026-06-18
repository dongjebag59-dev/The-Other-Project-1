from fastapi import APIRouter

from app.config import settings
from app.domain.admin.router import router as admin_router
from app.domain.ai.router import router as ai_router
from app.domain.hosting.router import router as hosting_router
from app.domain.match.router import router as match_router
from app.domain.review.router import router as review_router
from app.domain.senior.router import router as senior_router
from app.domain.user.router import router as user_router

api_router = APIRouter()

api_router.include_router(user_router, prefix="/users", tags=["users"])
api_router.include_router(senior_router, prefix="/seniors", tags=["seniors"])
api_router.include_router(hosting_router, prefix="/hostings", tags=["hostings"])
api_router.include_router(match_router, prefix="/matches", tags=["matches"])
api_router.include_router(review_router, prefix="/reviews", tags=["reviews"])
api_router.include_router(ai_router, prefix="/ai", tags=["ai"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])

if settings.DEBUG:
    from app.domain.test.router import router as test_router
    api_router.include_router(test_router, prefix="/test", tags=["test"])
