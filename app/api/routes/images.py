import requests
import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.image import Image
from app.schemas.image import ImageCreate
from app.services.vision_service import analyze_image

VISION_REVIEW_THRESHOLD = float(
    os.getenv("VISION_REVIEW_THRESHOLD", "0.80")
)
router = APIRouter(prefix="/images", tags=["images"])

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_image(
    image_data: ImageCreate,
    db: Session = Depends(get_db),
):
    # 1. Download the image
    response = requests.get(
        str(image_data.url),
        timeout=30,
    )
    response.raise_for_status()

    image_bytes = response.content
    mime_type = response.headers.get(
        "Content-Type",
        "image/jpeg",
    )

    # 2. Analyze the image with Ollama/LLaVA
    vision_result = analyze_image(
        image_bytes,
        mime_type,
    )

    # 3. Save the image and AI metadata
    image = Image(
        url=str(image_data.url),
        subject=vision_result.subject,
        category=vision_result.category,
        attributes=", ".join(vision_result.attributes),
        caption=vision_result.caption,
        confidence=vision_result.confidence,
        needs_review=vision_result.confidence < VISION_REVIEW_THRESHOLD,
    )

    db.add(image)
    db.commit()
    db.refresh(image)

    return image


@router.get("/{image_id}")
def get_image(
    image_id: int,
    db: Session = Depends(get_db),
):
    image = db.get(Image, image_id)

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    return image