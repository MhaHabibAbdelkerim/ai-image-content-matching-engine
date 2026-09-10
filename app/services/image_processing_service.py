import logging
import os

import requests
from requests.exceptions import ConnectionError, Timeout

from sqlalchemy.orm import Session

from app.models.image import Image
from app.models.job import ImageProcessingJob
from app.services.vision_service import analyze_image
from app.services.embedding_service import generate_embedding


logger = logging.getLogger(__name__)


VISION_REVIEW_THRESHOLD = float(
    os.getenv("VISION_REVIEW_THRESHOLD", "0.80")
)


def is_retryable_error(exc: Exception) -> bool:
    """
    Determine whether an error is likely temporary
    and therefore worth retrying.
    """

    if isinstance(exc, ConnectionError):
        return True

    if isinstance(exc, Timeout):
        return True

    if isinstance(exc, requests.HTTPError):
        response = exc.response

        if response is None:
            return False

        if response.status_code == 429:
            return True

        if 500 <= response.status_code <= 599:
            return True

        return False

    return False


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
            db,
        )

        image.subject = vision_result.subject
        image.category = vision_result.category
        image.attributes = ", ".join(
            vision_result.attributes
        )
        image.caption = vision_result.caption
        image.confidence = vision_result.confidence

        metadata_text = (
            f"Subject: {image.subject}. "
            f"Category: {image.category}. "
            f"Attributes: {image.attributes}. "
            f"Caption: {image.caption}"
        )

        image.embedding = generate_embedding(
            metadata_text,
            db,
        )

        image.needs_review = (
            vision_result.confidence
            < VISION_REVIEW_THRESHOLD
        )

        job.status = "completed"
        job.error_message = None

        db.commit()

    except Exception as exc:

        error_message = (
            str(exc)
            or type(exc).__name__
        )

        # Budget errors are permanent for the current
        # configuration. Retrying immediately cannot
        # make the budget available.
        if "AI budget exceeded" in error_message:
            retryable = False
        else:
            retryable = is_retryable_error(exc)

        logger.exception(
            "Image processing failed for job %s "
            "(attempt %s, retryable=%s): %s",
            job_id,
            job.attempts,
            retryable,
            error_message,
        )

        job.error_message = error_message

        if retryable:
            job.status = "pending"

        else:
            job.status = "failed"

            logger.error(
                "ALERT: Image processing job %s "
                "failed permanently. "
                "Image ID: %s. Error: %s",
                job.id,
                job.image_id,
                error_message,
            )

        db.commit()