from types import SimpleNamespace

from app.services.mismatch_guard import evaluate_match


def make_blog_post(subject: str):
    return SimpleNamespace(
        subject=subject,
    )


def make_image(
    subject: str,
    confidence: float,
):
    return SimpleNamespace(
        subject=subject,
        confidence=confidence,
    )


def test_matching_subject_is_accepted():
    blog_post = make_blog_post("fox")

    image = make_image(
        subject="fox",
        confidence=0.90,
    )

    result = evaluate_match(
        blog_post=blog_post,
        image=image,
        similarity=0.80,
    )

    assert result["accepted"] is True

    assert "matches" in result["reason"]


def test_wrong_subject_is_rejected():
    blog_post = make_blog_post("fox")

    image = make_image(
        subject="wolf",
        confidence=0.90,
    )

    result = evaluate_match(
        blog_post=blog_post,
        image=image,
        similarity=0.80,
    )

    assert result["accepted"] is False

    assert "wolf" in result["reason"]

    assert "fox" in result["reason"]


def test_low_similarity_is_rejected():
    blog_post = make_blog_post("fox")

    image = make_image(
        subject="fox",
        confidence=0.90,
    )

    result = evaluate_match(
        blog_post=blog_post,
        image=image,
        similarity=0.60,
    )

    assert result["accepted"] is False

    assert "below" in result["reason"]


def test_low_confidence_is_rejected():
    blog_post = make_blog_post("fox")

    image = make_image(
        subject="fox",
        confidence=0.60,
    )

    result = evaluate_match(
        blog_post=blog_post,
        image=image,
        similarity=0.85,
    )

    assert result["accepted"] is False

    assert "confidence" in result["reason"]


def test_missing_confidence_is_rejected():
    blog_post = make_blog_post("fox")

    image = SimpleNamespace(
        subject="fox",
        confidence=None,
    )

    result = evaluate_match(
        blog_post=blog_post,
        image=image,
        similarity=0.85,
    )

    assert result["accepted"] is False

    assert "no confidence" in result["reason"]