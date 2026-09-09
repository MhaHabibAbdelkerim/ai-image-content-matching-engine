from datetime import datetime

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.image import Image
from app.models.job import ImageProcessingJob
from app.schemas.image import ImageCreate
from app.schemas.review import ImageReviewCreate
from app.workers.image_worker import run_image_job


router = APIRouter(
    prefix="/images",
    tags=["images"],
)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_image(
    image_data: ImageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # 1. Save the image first
    image = Image(
        url=str(image_data.url),
    )

    db.add(image)
    db.commit()
    db.refresh(image)

    # 2. Create a processing job
    job = ImageProcessingJob(
        image_id=image.id,
        status="pending",
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # 3. Schedule the job in the background
    background_tasks.add_task(
        run_image_job,
        job.id,
    )

    # 4. Return immediately
    return {
        "image_id": image.id,
        "job_id": job.id,
        "status": job.status,
    }


@router.post("/{image_id}/review")
def review_image(
    image_id: int,
    review_data: ImageReviewCreate,
    db: Session = Depends(get_db),
):
    image = db.get(Image, image_id)

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    image.review_status = review_data.decision
    image.review_reason = review_data.reason
    image.reviewed_at = datetime.utcnow()

    db.commit()
    db.refresh(image)

    return {
        "image_id": image.id,
        "review_status": image.review_status,
        "review_reason": image.review_reason,
        "reviewed_at": image.reviewed_at,
    }


@router.get("/{image_id}/review")
def get_image_review(
    image_id: int,
    db: Session = Depends(get_db),
):
    image = db.get(Image, image_id)

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    return {
        "image_id": image.id,
        "subject": image.subject,
        "category": image.category,
        "confidence": image.confidence,
        "needs_review": image.needs_review,
        "review_status": image.review_status,
        "review_reason": image.review_reason,
        "reviewed_at": image.reviewed_at,
    }


@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: int,
    db: Session = Depends(get_db),
):
    job = db.get(ImageProcessingJob, job_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return {
        "job_id": job.id,
        "image_id": job.image_id,
        "status": job.status,
        "attempts": job.attempts,
        "error_message": job.error_message,
    }

@router.get("/review/pending")
def get_pending_reviews(
    db: Session = Depends(get_db),
):
    images = (
        db.query(Image)
        .filter(
            Image.review_status == "pending",
            Image.needs_review == True,
        )
        .all()
    )

    return {
        "count": len(images),
        "images": [
            {
                "image_id": image.id,
                "url": image.url,
                "subject": image.subject,
                "category": image.category,
                "confidence": image.confidence,
                "needs_review": image.needs_review,
                "review_status": image.review_status,
                "review_reason": image.review_reason,
                "reviewed_at": image.reviewed_at,
            }
            for image in images
        ],
    }

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