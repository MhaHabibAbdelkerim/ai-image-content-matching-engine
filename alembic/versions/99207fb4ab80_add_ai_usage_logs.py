"""add AI usage logs

Revision ID: 99207fb4ab80
Revises: bcbbd536087e
Create Date: 2026-09-10 05:12:38.695244
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "99207fb4ab80"
down_revision: Union[str, Sequence[str], None] = "bcbbd536087e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_logs",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "operation",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "model",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "success",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "duration_ms",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "estimated_cost",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("ai_usage_logs")