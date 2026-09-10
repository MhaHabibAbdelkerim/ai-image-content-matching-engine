from datetime import datetime

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.image import Image
from app.models.job import ImageProcessingJob
from app.models.idempotency import IdempotencyKey
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
    idempotency_key: str = Header(
        ...,
        alias="Idempotency-Key",
    ),
    db: Session = Depends(get_db),
):
    # 0. Check whether this request was already processed
    existing_key = (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.key == idempotency_key)
        .first()
    )

    if existing_key is not None:
        return {
            "image_id": existing_key.image_id,
            "job_id": existing_key.job_id,
            "status": "already_processed",
        }

    # 1. Create image + job + idempotency record
    image = Image(
        url=str(image_data.url),
    )

    db.add(image)
    db.flush()

    job = ImageProcessingJob(
        image_id=image.id,
        status="pending",
    )

    db.add(job)
    db.flush()

    idempotency_record = IdempotencyKey(
        key=idempotency_key,
        image_id=image.id,
        job_id=job.id,
    )

    try:
        # The idempotency key is the part that can have
        # a concurrent unique-constraint conflict.
        #
        # begin_nested() creates a SAVEPOINT.
        # If another request inserted the same key first,
        # only this nested operation is rolled back.
        with db.begin_nested():
            db.add(idempotency_record)
            db.flush()

    except IntegrityError:
        # Another concurrent request won the race.
        #
        # The SAVEPOINT has already been rolled back,
        # so the outer transaction is still usable.

        existing_key = (
            db.query(IdempotencyKey)
            .filter(IdempotencyKey.key == idempotency_key)
            .first()
        )

        if existing_key is None:
            db.rollback()

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotency key conflict. Please retry.",
            )

        # Our image/job were only temporary objects.
        # We don't want this losing request to create them.
        db.rollback()

        return {
            "image_id": existing_key.image_id,
            "job_id": existing_key.job_id,
            "status": "already_processed",
        }

    # 2. Commit image + job + idempotency key together
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    # 3. Refresh objects after commit
    db.refresh(image)
    db.refresh(job)

    # 4. Schedule the background processing job
    background_tasks.add_task(
        run_image_job,
        job.id,
    )

    # 5. Return response
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