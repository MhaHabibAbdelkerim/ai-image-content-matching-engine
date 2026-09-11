from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_get_nonexistent_image():
    response = client.get("/images/999999")

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Image not found"
    }


def test_get_nonexistent_job():
    response = client.get("/images/jobs/999999")

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Job not found"
    }


def test_create_image_missing_idempotency_key():
    response = client.post(
        "/images/",
        json={
            "url": "https://example.com/image.jpg"
        },
    )

    assert response.status_code == 422


def test_create_image_invalid_url():
    response = client.post(
        "/images/",
        headers={
            "Idempotency-Key": "test-validation-invalid-url"
        },
        json={
            "url": "not-a-valid-url"
        },
    )

    assert response.status_code == 422


def test_review_nonexistent_image():
    response = client.post(
        "/images/999999/review",
        json={
            "decision": "approved",
            "reason": "Test review",
        },
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Image not found"
    }


def test_review_invalid_decision():
    response = client.post(
        "/images/999999/review",
        json={
            "decision": "maybe",
            "reason": "Invalid decision test",
        },
    )

    assert response.status_code == 422


def test_get_matches_for_nonexistent_blog_post():
    response = client.get(
        "/blog-posts/999999/matches"
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Blog post not found"
    }