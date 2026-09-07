import time

from app.db.database import SessionLocal
from app.models.job import ImageProcessingJob
from app.services.image_processing_service import process_image_job


MAX_ATTEMPTS = 3
RETRY_DELAY = 5


def run_image_job(job_id: int) -> None:
    db = SessionLocal()

    try:
        process_image_job(job_id, db)

        job = db.get(ImageProcessingJob, job_id)

        if job is not None and job.status == "pending":
            time.sleep(RETRY_DELAY)
            run_image_job(job_id)

    finally:
        db.close()