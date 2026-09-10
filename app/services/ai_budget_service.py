import os

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.ai_usage import AIUsageLog


AI_BUDGET_LIMIT = float(
    os.getenv("AI_BUDGET_LIMIT", "1.00")
)


def get_total_ai_cost(db: Session) -> float:
    """
    Return the total estimated AI cost recorded so far.
    """

    total = (
        db.query(
            func.coalesce(
                func.sum(AIUsageLog.estimated_cost),
                0.0,
            )
        )
        .scalar()
    )

    return float(total)


def check_ai_budget(
    db: Session,
    estimated_cost: float,
) -> None:
    """
    Raise an error if the next AI operation would
    exceed the configured budget.
    """

    current_cost = get_total_ai_cost(db)

    projected_cost = current_cost + estimated_cost

    if projected_cost > AI_BUDGET_LIMIT:
        raise RuntimeError(
            f"AI budget exceeded. "
            f"Current estimated cost: ${current_cost:.4f}. "
            f"Next operation: ${estimated_cost:.4f}. "
            f"Budget limit: ${AI_BUDGET_LIMIT:.4f}."
        )