import os

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
from app.workers.image_worker import run_image_job

router = APIRouter(prefix="/images", tags=["images"])


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