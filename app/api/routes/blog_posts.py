from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.models.blog_post import BlogPost
from app.schemas.blog_post import BlogPostCreate
from app.services.embedding_service import generate_embedding
from app.services.matching_service import find_similar_images


router = APIRouter(
    prefix="/blog-posts",
    tags=["blog-posts"],
)


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_blog_post(
    post_data: BlogPostCreate,
    db: Session = Depends(get_db),
):
    embedding_text = (
        f"Title: {post_data.title}. "
        f"Content: {post_data.content}"
    )

    embedding = generate_embedding(embedding_text)

    blog_post = BlogPost(
        title=post_data.title,
        content=post_data.content,
        embedding=embedding,
    )

    db.add(blog_post)
    db.commit()
    db.refresh(blog_post)

    return {
        "id": blog_post.id,
        "title": blog_post.title,
        "content": blog_post.content,
        "has_embedding": blog_post.embedding is not None,
    }

@router.get("/{post_id}/matches")
def get_matches(
    post_id: int,
    db: Session = Depends(get_db),
):
    blog_post = db.get(BlogPost, post_id)

    if blog_post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found",
        )

    matches = find_similar_images(
        blog_post=blog_post,
        db=db,
        limit=5,
    )

    return {
        "blog_post_id": blog_post.id,
        "title": blog_post.title,
        "matches": matches,
    }