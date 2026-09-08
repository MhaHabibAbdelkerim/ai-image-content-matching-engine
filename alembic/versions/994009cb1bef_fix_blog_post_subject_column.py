from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "994009cb1bef"
down_revision: Union[str, Sequence[str], None] = "995218bf390b"

branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "blog_posts",
        sa.Column(
            "subject",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.execute(
        "UPDATE blog_posts SET subject = 'fox' WHERE id = 1"
    )

    op.alter_column(
        "blog_posts",
        "subject",
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("blog_posts", "subject")