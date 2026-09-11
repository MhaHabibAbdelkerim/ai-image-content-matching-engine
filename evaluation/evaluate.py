import json
import sys
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import SessionLocal
from app.models.blog_post import BlogPost
from app.models.image import Image
from app.services.mismatch_guard import evaluate_match


DATASET_PATH = Path(__file__).parent / "dataset.json"

MATCH_LIMIT = 5


def load_dataset() -> list[dict]:
    with open(DATASET_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def get_ranked_matches(
    blog_post: BlogPost,
    db,
    limit: int = MATCH_LIMIT,
) -> list[dict]:

    if blog_post.embedding is None:
        return []

    distance = Image.embedding.cosine_distance(
        blog_post.embedding
    )

    statement = (
        select(
            Image,
            distance.label("distance"),
        )
        .where(Image.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    )

    results = db.execute(statement).all()

    matches = []

    for image, image_distance in results:

        similarity = 1 - float(image_distance)

        guard_result = evaluate_match(
            blog_post=blog_post,
            image=image,
            similarity=similarity,
        )

        matches.append(
            {
                "image_id": image.id,
                "subject": image.subject,
                "confidence": image.confidence,
                "similarity": similarity,
                "accepted": guard_result["accepted"],
                "reason": guard_result["reason"],
            }
        )

    return matches


def find_blog_post(
    blog_subject: str,
    db,
) -> BlogPost | None:

    return (
        db.query(BlogPost)
        .filter(
            BlogPost.subject == blog_subject
        )
        .first()
    )


def find_image_by_subject(
    subject: str,
    db,
) -> Image | None:

    return (
        db.query(Image)
        .filter(
            Image.subject.ilike(subject)
        )
        .filter(
            Image.embedding.is_not(None)
        )
        .first()
    )


def find_image_by_id(
    image_id: int,
    db,
) -> Image | None:

    return (
        db.query(Image)
        .filter(
            Image.id == image_id
        )
        .first()
    )


def calculate_similarity(
    blog_post: BlogPost,
    image: Image,
    db,
) -> float:

    distance = Image.embedding.cosine_distance(
        blog_post.embedding
    )

    statement = (
        select(distance.label("distance"))
        .where(Image.id == image.id)
    )

    image_distance = db.execute(
        statement
    ).scalar_one()

    return 1 - float(image_distance)


def evaluate_match_case(
    case: dict,
    db,
) -> dict:

    blog_post = find_blog_post(
        case["blog_subject"],
        db,
    )

    if blog_post is None:
        return {
            "name": case["name"],
            "type": "match",
            "passed": False,
            "error": (
                f'No blog post found for '
                f'"{case["blog_subject"]}".'
            ),
        }

    matches = get_ranked_matches(
        blog_post,
        db,
    )

    accepted_matches = [
        match
        for match in matches
        if match["accepted"]
    ]

    if not accepted_matches:
        return {
            "name": case["name"],
            "type": "match",
            "passed": False,
            "error": "No accepted match was found.",
        }

    top_match = accepted_matches[0]

    expected_subject = (
        case["expected_subject"]
        .strip()
        .lower()
    )

    actual_subject = (
        (top_match["subject"] or "")
        .strip()
        .lower()
    )

    passed = (
        actual_subject == expected_subject
    )

    return {
        "name": case["name"],
        "type": "match",
        "passed": passed,
        "expected_subject": case["expected_subject"],
        "actual_subject": top_match["subject"],
        "similarity": top_match["similarity"],
        "confidence": top_match["confidence"],
        "accepted": top_match["accepted"],
        "reason": top_match["reason"],
    }


def evaluate_mismatch_case(
    case: dict,
    db,
) -> dict:

    blog_post = find_blog_post(
        case["blog_subject"],
        db,
    )

    if blog_post is None:
        return {
            "name": case["name"],
            "type": "mismatch",
            "passed": False,
            "error": (
                f'No blog post found for '
                f'"{case["blog_subject"]}".'
            ),
        }

    image = find_image_by_subject(
        case["expected_subject"],
        db,
    )

    if image is None:
        return {
            "name": case["name"],
            "type": "mismatch",
            "passed": False,
            "error": (
                f'No image found with subject '
                f'"{case["expected_subject"]}".'
            ),
        }

    if image.embedding is None:
        return {
            "name": case["name"],
            "type": "mismatch",
            "passed": False,
            "error": (
                f"Image {image.id} has no embedding."
            ),
        }

    similarity = calculate_similarity(
        blog_post=blog_post,
        image=image,
        db=db,
    )

    guard_result = evaluate_match(
        blog_post=blog_post,
        image=image,
        similarity=similarity,
    )

    passed = (
        guard_result["accepted"] is False
    )

    return {
        "name": case["name"],
        "type": "mismatch",
        "passed": passed,
        "expected_subject": case["expected_subject"],
        "actual_subject": image.subject,
        "similarity": similarity,
        "confidence": image.confidence,
        "accepted": guard_result["accepted"],
        "reason": guard_result["reason"],
    }


def evaluate_low_confidence_case(
    case: dict,
    db,
) -> dict:

    blog_post = find_blog_post(
        case["blog_subject"],
        db,
    )

    if blog_post is None:
        return {
            "name": case["name"],
            "type": "low_confidence",
            "passed": False,
            "error": (
                f'No blog post found for '
                f'"{case["blog_subject"]}".'
            ),
        }

    image_id = case.get("image_id")

    if image_id is not None:
        image = find_image_by_id(
            image_id,
            db,
        )
    else:
        image = find_image_by_subject(
            case["expected_subject"],
            db,
        )

    if image is None:
        return {
            "name": case["name"],
            "type": "low_confidence",
            "passed": False,
            "error": (
                "The expected low-confidence "
                "image was not found."
            ),
        }

    if image.embedding is None:
        return {
            "name": case["name"],
            "type": "low_confidence",
            "passed": False,
            "error": (
                f"Image {image.id} has no embedding."
            ),
        }

    similarity = calculate_similarity(
        blog_post=blog_post,
        image=image,
        db=db,
    )

    guard_result = evaluate_match(
        blog_post=blog_post,
        image=image,
        similarity=similarity,
    )

    reason = guard_result["reason"].lower()

    passed = (
        guard_result["accepted"] is False
        and "confidence" in reason
    )

    return {
        "name": case["name"],
        "type": "low_confidence",
        "passed": passed,
        "expected_subject": case["expected_subject"],
        "actual_subject": image.subject,
        "image_id": image.id,
        "similarity": similarity,
        "confidence": image.confidence,
        "accepted": guard_result["accepted"],
        "reason": guard_result["reason"],
    }


def evaluate_no_match_case(
    case: dict,
    db,
) -> dict:

    blog_post = find_blog_post(
        case["blog_subject"],
        db,
    )

    if blog_post is None:
        return {
            "name": case["name"],
            "type": "no_match",
            "passed": False,
            "error": (
                f'No blog post found for '
                f'"{case["blog_subject"]}".'
            ),
        }

    matches = get_ranked_matches(
        blog_post,
        db,
    )

    accepted_matches = [
        match
        for match in matches
        if match["accepted"]
    ]

    passed = len(accepted_matches) == 0

    return {
        "name": case["name"],
        "type": "no_match",
        "passed": passed,
        "expected_subject": case["expected_subject"],
        "accepted_count": len(accepted_matches),
    }


def evaluate_case(
    case: dict,
    db,
) -> dict:

    case_type = case["type"]

    if case_type == "match":
        return evaluate_match_case(
            case,
            db,
        )

    if case_type == "mismatch":
        return evaluate_mismatch_case(
            case,
            db,
        )

    if case_type == "low_confidence":
        return evaluate_low_confidence_case(
            case,
            db,
        )

    if case_type == "no_match":
        return evaluate_no_match_case(
            case,
            db,
        )

    return {
        "name": case["name"],
        "type": case_type,
        "passed": False,
        "error": (
            f"Unknown evaluation type: "
            f"{case_type}"
        ),
    }


def print_result(result: dict) -> None:

    status = (
        "PASS"
        if result["passed"]
        else "FAIL"
    )

    print(
        f"[{status}] {result['name']}"
    )

    if "error" in result:
        print(
            f"       Error: {result['error']}"
        )
        print()
        return

    if result["type"] == "match":

        print(
            f"       Expected subject: "
            f"{result['expected_subject']}"
        )

        print(
            f"       Actual subject:   "
            f"{result['actual_subject']}"
        )

        print(
            f"       Similarity: "
            f"{result['similarity']:.4f}"
        )

        print(
            f"       Confidence: "
            f"{result['confidence']}"
        )

        print(
            f"       Accepted: "
            f"{result['accepted']}"
        )

    elif result["type"] == "mismatch":

        print(
            f"       Wrong subject tested: "
            f"{result['expected_subject']}"
        )

        print(
            f"       Similarity: "
            f"{result['similarity']:.4f}"
        )

        print(
            f"       Confidence: "
            f"{result['confidence']}"
        )

        print(
            f"       Accepted: "
            f"{result['accepted']}"
        )

        print(
            f"       Guard reason: "
            f"{result['reason']}"
        )

    elif result["type"] == "low_confidence":

        print(
            f"       Image ID: "
            f"{result['image_id']}"
        )

        print(
            f"       Subject: "
            f"{result['actual_subject']}"
        )

        print(
            f"       Similarity: "
            f"{result['similarity']:.4f}"
        )

        print(
            f"       Confidence: "
            f"{result['confidence']}"
        )

        print(
            f"       Accepted: "
            f"{result['accepted']}"
        )

        print(
            f"       Guard reason: "
            f"{result['reason']}"
        )

    elif result["type"] == "no_match":

        print(
            f"       Accepted matches: "
            f"{result['accepted_count']}"
        )

        print(
            "       Expected: no confident match"
        )

    print()


def main() -> None:

    dataset = load_dataset()

    db = SessionLocal()

    try:

        results = []

        for case in dataset:

            result = evaluate_case(
                case,
                db,
            )

            results.append(result)

        print()
        print("=" * 70)
        print("AI IMAGE MATCHING EVALUATION")
        print("=" * 70)
        print()

        for result in results:
            print_result(result)

        match_results = [
            result
            for result in results
            if result["type"] == "match"
        ]

        match_passed = sum(
            1
            for result in match_results
            if result["passed"]
        )

        top1_precision = (
            match_passed / len(match_results)
            if match_results
            else 0.0
        )

        mismatch_results = [
            result
            for result in results
            if result["type"] == "mismatch"
        ]

        mismatch_passed = sum(
            1
            for result in mismatch_results
            if result["passed"]
        )

        low_confidence_results = [
            result
            for result in results
            if result["type"] == "low_confidence"
        ]

        low_confidence_passed = sum(
            1
            for result in low_confidence_results
            if result["passed"]
        )

        no_match_results = [
            result
            for result in results
            if result["type"] == "no_match"
        ]

        no_match_passed = sum(
            1
            for result in no_match_results
            if result["passed"]
        )

        total_passed = sum(
            1
            for result in results
            if result["passed"]
        )

        print("=" * 70)
        print("EVALUATION SUMMARY")
        print("=" * 70)

        print(
            f"Top-1 Precision: "
            f"{match_passed}/{len(match_results)} "
            f"= {top1_precision:.2%}"
        )

        print(
            f"Mismatch Guard: "
            f"{mismatch_passed}/{len(mismatch_results)} "
            f"passed"
        )

        print(
            f"Low-Confidence Guard: "
            f"{low_confidence_passed}/"
            f"{len(low_confidence_results)} "
            f"passed"
        )

        print(
            f"No-Confident-Match: "
            f"{no_match_passed}/"
            f"{len(no_match_results)} "
            f"passed"
        )

        print(
            f"Overall: "
            f"{total_passed}/{len(results)} "
            f"tests passed"
        )

        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    main()