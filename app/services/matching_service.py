from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.image import Image
from app.models.blog_post import BlogPost


def find_similar_images(
    blog_post: BlogPost,
    db: Session,
    limit: int = 5,
):
    if blog_post.embedding is None:
        return []

    query_embedding = blog_post.embedding

    distance = Image.embedding.cosine_distance(
        query_embedding
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

        matches.append(
            {
                "image_id": image.id,
                "subject": image.subject,
                "category": image.category,
                "caption": image.caption,
                "similarity": similarity,
            }
        )

    return matches