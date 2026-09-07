import os
import logging
import requests
from sqlalchemy.orm import Session

from app.models.image import Image
from app.models.job import ImageProcessingJob
from app.services.vision_service import analyze_image


logger = logging.getLogger(__name__)

VISION_REVIEW_THRESHOLD = float(
    os.getenv("VISION_REVIEW_THRESHOLD", "0.80")
)


def process_image_job(
    job_id: int,
    db: Session,
) -> None:
    job = db.get(ImageProcessingJob, job_id)

    if job is None:
        return

    image = db.get(Image, job.image_id)

    if image is None:
        job.status = "failed"
        job.error_message = "Image not found"
        db.commit()
        return

    job.status = "processing"
    job.attempts += 1
    db.commit()

    try:
        response = requests.get(
            image.url,
            timeout=30,
        )
        response.raise_for_status()

        image_bytes = response.content
        mime_type = response.headers.get(
            "Content-Type",
            "image/jpeg",
        )

        vision_result = analyze_image(
            image_bytes,
            mime_type,
        )

        image.subject = vision_result.subject
        image.category = vision_result.category
        image.attributes = ", ".join(
            vision_result.attributes
        )
        image.caption = vision_result.caption
        image.confidence = vision_result.confidence

        image.needs_review = (
            vision_result.confidence < VISION_REVIEW_THRESHOLD
        )

        job.status = "completed"
        job.error_message = None

        db.commit()

    except Exception as exc:
        error_message = str(exc) or type(exc).__name__

        logger.exception(
            "Image processing failed for job %s (attempt %s): %s",
            job_id,
            job.attempts,
            error_message,
        )

        job.error_message = error_message

        if job.attempts < 3:
            job.status = "pending"
        else:
            job.status = "failed"

            logger.error(
                "ALERT: Image processing job %s permanently failed "
                "after %s attempts. Image ID: %s. Error: %s",
                job.id,
                job.attempts,
                job.image_id,
                error_message,
            )

        db.commit()