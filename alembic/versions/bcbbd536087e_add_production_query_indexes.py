"""add production query indexes

Revision ID: bcbbd536087e
Revises: b6c93b9bd8fd
Create Date: 2026-09-10
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "bcbbd536087e"
down_revision: Union[str, Sequence[str], None] = "b6c93b9bd8fd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Speeds up looking up processing jobs for a specific image.
    op.create_index(
        "ix_image_processing_jobs_image_id",
        "image_processing_jobs",
        ["image_id"],
    )

    # Speeds up the pending-review query.
    op.create_index(
        "ix_images_review_status",
        "images",
        ["review_status"],
    )

    # Speeds up filtering images that require human review.
    op.create_index(
        "ix_images_needs_review",
        "images",
        ["needs_review"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_images_needs_review",
        table_name="images",
    )

    op.drop_index(
        "ix_images_review_status",
        table_name="images",
    )

    op.drop_index(
        "ix_image_processing_jobs_image_id",
        table_name="image_processing_jobs",
    )