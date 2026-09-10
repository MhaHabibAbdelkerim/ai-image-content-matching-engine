import os
import logging

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

    # Network connection failures can be temporary.
    if isinstance(exc, ConnectionError):
        return True

    # Request timeouts can be temporary.
    if isinstance(exc, Timeout):
        return True

    # HTTP errors need to be inspected by status code.
    if isinstance(exc, requests.HTTPError):
        response = exc.response

        if response is None:
            return False

        # Rate limiting can be temporary.
        if response.status_code == 429:
            return True

        # Server-side errors can be temporary.
        if 500 <= response.status_code <= 599:
            return True

        # Client-side errors such as 400, 403, and 404
        # are treated as permanent failures.
        return False

    # Unknown errors are treated as permanent rather than
    # blindly retrying something we do not understand.
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
        # Download the image.
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

        # Run vision analysis.
        vision_result = analyze_image(
            image_bytes,
            mime_type,
        )

        # Store structured vision metadata.
        image.subject = vision_result.subject

        image.category = vision_result.category

        image.attributes = ", ".join(
            vision_result.attributes
        )

        image.caption = vision_result.caption

        image.confidence = vision_result.confidence

        # Build text representation for embedding.
        metadata_text = (
            f"Subject: {image.subject}. "
            f"Category: {image.category}. "
            f"Attributes: {image.attributes}. "
            f"Caption: {image.caption}"
        )

        # Generate semantic embedding.
        image.embedding = generate_embedding(
            metadata_text
        )

        # Flag low-confidence vision results.
        image.needs_review = (
            vision_result.confidence
            < VISION_REVIEW_THRESHOLD
        )

        # Mark job as successfully completed.
        job.status = "completed"
        job.error_message = None

        db.commit()

    except Exception as exc:
        error_message = (
            str(exc)
            or type(exc).__name__
        )

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
            # The worker will decide whether another attempt
            # is still available.
            job.status = "pending"

        else:
            # Permanent failure — do not retry.
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