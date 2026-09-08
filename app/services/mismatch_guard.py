import os

from app.models.blog_post import BlogPost
from app.models.image import Image


SIMILARITY_THRESHOLD = float(
    os.getenv("MATCH_SIMILARITY_THRESHOLD", "0.70")
)

MIN_IMAGE_CONFIDENCE = float(
    os.getenv("MIN_IMAGE_CONFIDENCE", "0.70")
)


def evaluate_match(
    blog_post: BlogPost,
    image: Image,
    similarity: float,
) -> dict:

    expected_subject = blog_post.subject.strip().lower()
    actual_subject = (image.subject or "").strip().lower()

    if similarity < SIMILARITY_THRESHOLD:
        return {
            "accepted": False,
            "reason": (
                f"Similarity score {similarity:.3f} is below "
                f"the required threshold of "
                f"{SIMILARITY_THRESHOLD:.3f}."
            ),
        }

    if image.confidence is None:
        return {
            "accepted": False,
            "reason": "Image has no confidence score.",
        }

    if image.confidence < MIN_IMAGE_CONFIDENCE:
        return {
            "accepted": False,
            "reason": (
                f"Image confidence {image.confidence:.3f} is below "
                f"the required threshold of "
                f"{MIN_IMAGE_CONFIDENCE:.3f}."
            ),
        }

    if actual_subject != expected_subject:
        return {
            "accepted": False,
            "reason": (
                f'Image subject "{image.subject}" does not match '
                f'expected subject "{blog_post.subject}".'
            ),
        }

    return {
        "accepted": True,
        "reason": (
            f'Image subject "{image.subject}" matches the expected '
            f'subject "{blog_post.subject}", with similarity '
            f"{similarity:.3f} and confidence "
            f"{image.confidence:.3f}."
        ),
    }