from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id: Mapped[int] = mapped_column(primary_key=True)

    key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    image_id: Mapped[int] = mapped_column(
        ForeignKey("images.id"),
        nullable=False,
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey("image_processing_jobs.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )