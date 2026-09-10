import os
import time

import requests
from sqlalchemy.orm import Session

from app.services.ai_budget_service import check_ai_budget
from app.services.ai_usage_service import log_ai_usage


OLLAMA_EMBED_URL = "http://host.docker.internal:11434/api/embed"
MODEL_NAME = "nomic-embed-text"

EMBEDDING_COST_PER_CALL = float(
    os.getenv("EMBEDDING_COST_PER_CALL", "0.00")
)


def generate_embedding(
    text: str,
    db: Session,
) -> list[float]:

    # Check whether this AI call is allowed by the budget.
    check_ai_budget(
        db=db,
        estimated_cost=EMBEDDING_COST_PER_CALL,
    )

    # Start timing the AI operation.
    start_time = time.perf_counter()

    try:
        response = requests.post(
            OLLAMA_EMBED_URL,
            json={
                "model": MODEL_NAME,
                "input": text,
            },
            timeout=120,
        )

        response.raise_for_status()

        result = response.json()

        embedding = result["embeddings"][0]

        # Record successful AI operation.
        log_ai_usage(
            db=db,
            operation="embedding_generation",
            provider="ollama",
            model=MODEL_NAME,
            success=True,
            start_time=start_time,
            estimated_cost=EMBEDDING_COST_PER_CALL,
        )

        return embedding

    except Exception:
        # Record failed AI operation.
        log_ai_usage(
            db=db,
            operation="embedding_generation",
            provider="ollama",
            model=MODEL_NAME,
            success=False,
            start_time=start_time,
            estimated_cost=EMBEDDING_COST_PER_CALL,
        )

        raise