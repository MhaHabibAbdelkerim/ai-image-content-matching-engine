from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.image import Image
from app.schemas.image import ImageCreate


router = APIRouter(prefix="/images", tags=["images"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_image(
    image_data: ImageCreate,
    db: Session = Depends(get_db),
):
    image = Image(
        url=str(image_data.url)
    )

    db.add(image)
    db.commit()
    db.refresh(image)

    return image

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.image import Image
from app.schemas.image import ImageCreate


router = APIRouter(prefix="/images", tags=["images"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_image(
    image_data: ImageCreate,
    db: Session = Depends(get_db),
):
    image = Image(
        url=str(image_data.url)
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