from typing import Literal

from pydantic import BaseModel


class ImageReviewCreate(BaseModel):
    decision: Literal["approved", "rejected"]
    reason: str | None = None