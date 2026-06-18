from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """환경변수 설정을 관리합니다."""

    # DB: 로컬은 SQLite, Docker 배포 시 PostgreSQL URL로 교체
    DATABASE_URL: str = "sqlite+aiosqlite:///./babdongmu.db"

    # JWT
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Solapi(=CoolSMS) (SMS 발송)
    SOLAPI_API_KEY: str = ""
    SOLAPI_API_SECRET: str = ""
    SOLAPI_SENDER: str = ""

    # Gemini (AI 요약 기능)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite-preview"
    GEMINI_MODEL_FALLBACK: str = "gemini-2.5-flash"

    # Cloudflare R2 (이미지 저장)
    R2_ENDPOINT: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_PUBLIC_BUCKET: str = ""   # 공개 버킷 (후기 이미지)
    R2_PRIVATE_BUCKET: str = ""  # 비공개 버킷 (신원 서류)
    R2_PUBLIC_URL: str = ""      # 공개 버킷 CDN URL

    # 카카오 OAuth
    KAKAO_CLIENT_ID: str = ""  # REST API KEY
    KAKAO_CLIENT_SECRET: str = ""
    KAKAO_REDIRECT_URI: str = "http://localhost:8000/api/v1/users/kakao/callback"

    # 프론트엔드 base URL (QR 코드에 담을 체크인 페이지 URL 생성에 사용)
    FRONTEND_BASE_URL: str = "http://localhost:8000"

    # 개발 모드 (True일 때만 테스트 라우터 등록)
    DEBUG: bool = False

    # 스케줄러 실행 주기(초)
    SCHEDULER_INTERVAL_SECONDS: int = 300
    CLEANUP_SCHEDULER_INTERVAL_SECONDS: int = 86400  # 하루 1번(24시간 주기)

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
