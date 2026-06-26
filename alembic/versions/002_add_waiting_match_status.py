"""add waiting match status

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-26
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # PostgreSQL: enum 타입에 값 추가 (트랜잭션 밖에서 실행해야 함)
        op.execute("ALTER TYPE matchstatus ADD VALUE IF NOT EXISTS 'WAITING'")
    # SQLite: match_status 컬럼은 VARCHAR로 저장되므로 마이그레이션 불필요


def downgrade() -> None:
    # PostgreSQL: enum 값 제거는 테이블 재생성 없이 불가 — 지원하지 않음
    pass
