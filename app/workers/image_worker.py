import random
import time

from app.db.database import SessionLocal
from app.models.job import ImageProcessingJob
from app.services.image_processing_service import process_image_job


MAX_ATTEMPTS = 3
BASE_RETRY_DELAY = 5
MAX_RETRY_DELAY = 30


def calculate_retry_delay(attempt: int) -> float:
    """
    Calculate exponential backoff with jitter.

    Attempt 1 failure → roughly 5 seconds
    Attempt 2 failure → roughly 10 seconds
    Attempt 3 failure → no retry
    """

    exponential_delay = BASE_RETRY_DELAY * (2 ** (attempt - 1))

    capped_delay = min(
        exponential_delay,
        MAX_RETRY_DELAY,
    )

    jitter = random.uniform(0, 1)

    return capped_delay + jitter


def run_image_job(job_id: int) -> None:
    db = SessionLocal()

    try:
        while True:
            job = db.get(ImageProcessingJob, job_id)

            if job is None:
                return

            # Stop if the job has already completed or permanently failed.
            if job.status in {"completed", "failed"}:
                return

            process_image_job(
                job_id,
                db,
            )

            # Refresh the job state after processing.
            db.expire_all()

            job = db.get(
                ImageProcessingJob,
                job_id,
            )

            if job is None:
                return

            # Successful processing.
            if job.status == "completed":
                return

            # Permanently failed after maximum attempts.
            if job.status == "failed":
                return

            # Retry only while we have attempts remaining.
            if job.status == "pending" and job.attempts < MAX_ATTEMPTS:
                delay = calculate_retry_delay(
                    job.attempts
                )

                time.sleep(delay)

                continue

            return

    finally:
        db.close()