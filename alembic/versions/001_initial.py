"""initial

Revision ID: 0001
Revises:
Create Date: 2026-04-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. addresses — seniors / hostings / users 가 FK로 참조
    op.create_table(
        "addresses",
        sa.Column("address_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("road_address", sa.String(length=255), nullable=False),
        sa.Column("jibun_address", sa.String(length=255), nullable=True),
        sa.Column("zonecode", sa.String(length=10), nullable=True),
        sa.Column("sigungu", sa.String(length=100), nullable=False),
        sa.Column("bname", sa.String(length=100), nullable=True),
        sa.Column("detail_address", sa.String(length=255), nullable=False),
        sa.Column("sido", sa.String(length=50), nullable=True),
        sa.Column("building_name", sa.String(length=100), nullable=True),
        sa.Column("is_apartment", sa.Boolean(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("sigungu_code", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("address_id"),
    )

    # 2. users
    op.create_table(
        "users",
        sa.Column("user_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("kakao_id", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("password", sa.String(length=255), nullable=True),
        sa.Column("phone_number", sa.String(length=20), nullable=True),
        sa.Column("address_id", sa.Integer(), nullable=False),
        sa.Column(
            "user_role",
            # plain enum.Enum → DB에는 name('VOLUNTEER'…) 저장
            sa.Enum("VOLUNTEER", "GUARDIAN", "ADMIN", name="userrole"),
            nullable=False,
        ),
        sa.Column(
            "cert_flag",
            sa.Enum("PENDING", "APPROVED", "REJECTED", name="certflag"),
            nullable=False,
        ),
        sa.Column("cert_reject_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["address_id"], ["addresses.address_id"]),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("address_id"),
        sa.UniqueConstraint("kakao_id"),
    )
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_users_kakao_id"), ["kakao_id"], unique=True)
        batch_op.create_index(batch_op.f("ix_users_email"), ["email"], unique=True)

    # 3. phone_verifications
    op.create_table(
        "phone_verifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("code", sa.String(length=6), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("phone_verifications", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_phone_verifications_phone_number"),
            ["phone_number"],
            unique=False,
        )

    # 4. documents
    op.create_table(
        "documents",
        sa.Column("document_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum(
                "CRIMINAL_RECORD",
                "WELFARE_CERT",
                "FAMILY_CERT",
                "IDENTITY_COPY",
                name="documenttype",
            ),
            nullable=False,
        ),
        sa.Column("document_url", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id"),
    )

    # 5. seniors
    op.create_table(
        "seniors",
        sa.Column("senior_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("guardian_id", sa.Integer(), nullable=False),
        sa.Column("address_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "gender",
            # str enum.Enum → DB에는 value('male'…) 저장
            sa.Enum("male", "female", "other", name="genderenum"),
            nullable=False,
        ),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("special_note", sa.Text(), nullable=True),
        sa.Column("active_flag", sa.Boolean(), nullable=False),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("max_people", sa.Integer(), nullable=False),
        sa.Column("qr_code", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint("max_people >= 2", name="ck_senior_max_people"),
        sa.ForeignKeyConstraint(["guardian_id"], ["users.user_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["address_id"], ["addresses.address_id"]),
        sa.PrimaryKeyConstraint("senior_id"),
        sa.UniqueConstraint("address_id"),
    )
    with op.batch_alter_table("seniors", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_seniors_guardian_id"), ["guardian_id"], unique=False
        )

    # 6. hostings
    op.create_table(
        "hostings",
        sa.Column("hosting_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("senior_id", sa.Integer(), nullable=True),
        sa.Column("address_id", sa.Integer(), nullable=False),
        sa.Column("menu", sa.String(length=255), nullable=False),
        sa.Column("hosting_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("hosting_end", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("max_people", sa.Integer(), nullable=False),
        sa.Column(
            "hosting_status",
            # str enum.Enum → DB에는 value 저장 (FIXED 최초부터 포함)
            sa.Enum(
                "OPEN", "FULL", "FIXED", "FAILED", "IN_PROGRESS", "CLOSED",
                name="hostingstatus",
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint("max_people >= 2", name="ck_hosting_max_people"),
        sa.ForeignKeyConstraint(["senior_id"], ["seniors.senior_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["address_id"], ["addresses.address_id"]),
        sa.PrimaryKeyConstraint("hosting_id"),
        sa.UniqueConstraint("address_id"),
    )
    with op.batch_alter_table("hostings", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_hostings_senior_id"), ["senior_id"], unique=False
        )

    # 7. matching_info
    op.create_table(
        "matching_info",
        sa.Column("matching_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("hosting_id", sa.Integer(), nullable=False),
        sa.Column("vt_id", sa.Integer(), nullable=False),
        sa.Column("senior_id", sa.Integer(), nullable=False),
        sa.Column(
            "match_status",
            # plain enum.Enum → DB에는 name 저장
            sa.Enum("APPROVED", "CANCELLED", "NOT_VISITED", name="matchstatus"),
            nullable=False,
        ),
        sa.Column("check_in_time", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("check_out_time", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("actual_volunteer_time", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["hosting_id"], ["hostings.hosting_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["vt_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["senior_id"], ["seniors.senior_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("matching_id"),
    )

    # 8. sms_logs
    op.create_table(
        "sms_logs",
        sa.Column("sms_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("hosting_id", sa.Integer(), nullable=False),
        sa.Column("receiver_id", sa.Integer(), nullable=False),
        sa.Column("is_send", sa.Boolean(), nullable=False),
        sa.Column(
            "alarm_type",
            # str enum.Enum → DB에는 value('match'…) 저장
            sa.Enum("match", "checkin", "checkout", "update", "delete", name="alarmtype"),
            nullable=False,
        ),
        sa.Column("contents", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["hosting_id"], ["hostings.hosting_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["receiver_id"], ["users.user_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("sms_id"),
    )
    with op.batch_alter_table("sms_logs", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_sms_logs_hosting_id"), ["hosting_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_sms_logs_receiver_id"), ["receiver_id"], unique=False
        )

    # 9. reviews
    op.create_table(
        "reviews",
        sa.Column("review_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("matching_id", sa.Integer(), nullable=False),
        sa.Column("vt_id", sa.Integer(), nullable=False),
        sa.Column("contents", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["matching_id"], ["matching_info.matching_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["vt_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("review_id"),
    )
    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_reviews_matching_id"), ["matching_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_reviews_vt_id"), ["vt_id"], unique=False
        )

    # 10. review_img
    op.create_table(
        "review_img",
        sa.Column("image_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["review_id"], ["reviews.review_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("image_id"),
    )
    with op.batch_alter_table("review_img", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_review_img_review_id"), ["review_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("review_img", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_review_img_review_id"))
    op.drop_table("review_img")

    with op.batch_alter_table("reviews", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_reviews_vt_id"))
        batch_op.drop_index(batch_op.f("ix_reviews_matching_id"))
    op.drop_table("reviews")

    with op.batch_alter_table("sms_logs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_sms_logs_receiver_id"))
        batch_op.drop_index(batch_op.f("ix_sms_logs_hosting_id"))
    op.drop_table("sms_logs")

    op.drop_table("matching_info")

    with op.batch_alter_table("hostings", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_hostings_senior_id"))
    op.drop_table("hostings")

    with op.batch_alter_table("seniors", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_seniors_guardian_id"))
    op.drop_table("seniors")

    op.drop_table("documents")

    with op.batch_alter_table("phone_verifications", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_phone_verifications_phone_number"))
    op.drop_table("phone_verifications")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_email"))
        batch_op.drop_index(batch_op.f("ix_users_kakao_id"))
    op.drop_table("users")

    op.drop_table("addresses")

    # PostgreSQL: 테이블 DROP 후 명명된 Enum 타입 명시 삭제
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS matchstatus")
        op.execute("DROP TYPE IF EXISTS alarmtype")
        op.execute("DROP TYPE IF EXISTS hostingstatus")
        op.execute("DROP TYPE IF EXISTS genderenum")
        op.execute("DROP TYPE IF EXISTS documenttype")
        op.execute("DROP TYPE IF EXISTS certflag")
        op.execute("DROP TYPE IF EXISTS userrole")
