import time

from sqlalchemy.orm import Session

from app.models.ai_usage import AIUsageLog


def log_ai_usage(
    db: Session,
    operation: str,
    provider: str,
    model: str,
    success: bool,
    start_time: float,
    estimated_cost: float = 0.0,
) -> None:
    """
    Record one AI operation in the database.
    """

    duration_ms = int(
        (time.perf_counter() - start_time) * 1000
    )

    usage_log = AIUsageLog(
        operation=operation,
        provider=provider,
        model=model,
        success=success,
        duration_ms=duration_ms,
        estimated_cost=estimated_cost,
    )

    db.add(usage_log)
    db.commit()