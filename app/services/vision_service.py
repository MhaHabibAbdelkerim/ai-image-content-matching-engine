import base64
import json

import requests

from app.schemas.vision import VisionResult


OLLAMA_URL = "http://host.docker.internal:11434/api/generate"
MODEL_NAME = "llava:latest"


def analyze_image(image_bytes: bytes, mime_type: str) -> VisionResult:
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = """
Analyze this image for an image-content matching system.

Return ONLY valid JSON with exactly these fields:

{
  "subject": "specific main subject",
  "category": "broad category",
  "attributes": ["attribute 1", "attribute 2"],
  "caption": "short description of the image",
  "confidence": 0.0
}

Rules:

- subject MUST identify the specific main subject visible in the image.
- Never use generic values such as "main subject", "object", "thing", "item", or "unknown".
- For animals, identify the animal as specifically as possible, such as "fox", "wolf", "lion", "dog", or "cat".
- For vehicles, identify the type such as "car", "bus", "truck", or "motorcycle".
- For food, identify the specific food when possible.
- category MUST be a broad category that matches the subject, such as "animal", "person", "vehicle", "food", "landscape", "building", or "object".
- attributes MUST contain important visible characteristics.
- caption MUST be one concise sentence describing the image.
- confidence MUST be a number between 0.0 and 1.0.
- Be conservative with confidence.
- Do not include markdown.
- Do not include ``` around the JSON.
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
        },
        timeout=120,
    )

    response.raise_for_status()

    ollama_result = response.json()
    raw_text = ollama_result["response"].strip()

    print("RAW OLLAMA RESPONSE:")
    print(raw_text)

    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")

        if raw_text.startswith("json"):
            raw_text = raw_text[4:].strip()

    result_data = json.loads(raw_text)

    return VisionResult.model_validate(result_data)