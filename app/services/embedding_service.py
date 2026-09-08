import requests

OLLAMA_EMBED_URL = "http://host.docker.internal:11434/api/embed"
MODEL_NAME = "nomic-embed-text"


def generate_embedding(text: str) -> list[float]:
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

    return result["embeddings"][0]