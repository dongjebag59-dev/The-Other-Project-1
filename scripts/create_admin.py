"""관리자 계정 생성 스크립트.

사용법:
    .env에 ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_NAME 설정 후 실행

    uv 환경:  uv run python scripts/create_admin.py
    pip 환경: python scripts/create_admin.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Babdongmu/ 루트를 경로에 추가 (app 패키지 인식용)
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import select

from app.core.security import hash_password
from app.database import AsyncSessionLocal, init_db
from app.domain.common.models import Address
from app.domain.user.models import CertFlag, User, UserRole

load_dotenv()


async def create_admin(email: str, password: str, name: str) -> None:
    """관리자 계정을 생성합니다. 이미 존재하면 건너뜁니다."""
    await init_db()

    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(User).where(User.email == email))
        if existing:
            print(f"이미 존재하는 계정입니다: {email}")
            return

        address = Address(road_address="관리자", sigungu="관리자", detail_address="")
        db.add(address)
        await db.flush()

        admin = User(
            email=email,
            password=hash_password(password),
            name=name,
            phone_number="010-0000-0000",
            address_id=address.address_id,
            user_role=UserRole.ADMIN,
            cert_flag=CertFlag.APPROVED,
        )
        db.add(admin)
        await db.commit()
        print(f"관리자 계정 생성 완료: {email}")


if __name__ == "__main__":
    email    = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    name     = os.getenv("ADMIN_NAME", "관리자")

    if not email or not password:
        print("오류: .env에 ADMIN_EMAIL과 ADMIN_PASSWORD를 설정해주세요.")
        sys.exit(1)

    asyncio.run(create_admin(email, password, name))
