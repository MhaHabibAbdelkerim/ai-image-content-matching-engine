from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "995218bf390b"
down_revision: Union[str, Sequence[str], None] = "1fed7b001431"

branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Add the column temporarily as nullable
    op.add_column(
        "blog_posts",
        sa.Column(
            "subject",
            sa.String(length=100),
            nullable=True,
        ),
    )

    # 2. Give the existing test blog post its subject
    op.execute(
        "UPDATE blog_posts SET subject = 'fox' WHERE id = 1"
    )

    # 3. Make subject required for all future blog posts
    op.alter_column(
        "blog_posts",
        "subject",
        nullable=False,
    )

def downgrade() -> None:
    op.drop_column("blog_posts", "subject")