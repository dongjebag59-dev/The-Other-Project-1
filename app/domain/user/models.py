"""유저 SQLAlchemy ORM 모델."""

import enum
from datetime import datetime, timezone

from sqlalchemy import TIMESTAMP, Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.domain.common.models import Address


class UserRole(enum.Enum):
    VOLUNTEER = "volunteer"
    GUARDIAN = "guardian"
    ADMIN = "admin"


class CertFlag(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    kakao_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    password: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # 카카오 로그인 시 None
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address_id: Mapped[int] = mapped_column(
        ForeignKey("addresses.address_id"), unique=True, nullable=False
    )
    address: Mapped[Address] = relationship("Address")
    user_role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    cert_flag: Mapped[CertFlag] = mapped_column(Enum(CertFlag), default=CertFlag.PENDING)
    cert_reject_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )

    # 카카오 로그인 유저 구분하기 위해 추가(비밀번호 관련)
    @property  # 메서드인데 속성처럼 쓸수있게(db 컬럼 X)
    def is_social_login(self) -> bool:
        return self.password is None


class PhoneVerification(Base):
    """SMS 인증 코드 저장."""

    __tablename__ = "phone_verifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    phone_number: Mapped[str] = mapped_column(String(20), index=True)
    code: Mapped[str] = mapped_column(String(6))
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class DocumentType(enum.Enum):
    CRIMINAL_RECORD = "criminal_record"  # 봉사자: 범죄경력조회서
    WELFARE_CERT = "welfare_cert"  # 보호자: 복지관 인증서류
    FAMILY_CERT = "family_cert"  # 보호자: 가족관계증명서
    IDENTITY_COPY = "identity_copy"  # 공통: 신분증 사본


class Document(Base):
    """신원 서류. 봉사자/보호자 가입 시 업로드."""

    __tablename__ = "documents"

    document_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType))
    document_url: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
