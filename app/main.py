from fastapi import FastAPI

from app.api.routes.images import router as images_router
from app.api.routes.blog_posts import router as blog_posts_router


app = FastAPI(
    title="AI Image Content Matching Engine"
)


app.include_router(images_router)
app.include_router(blog_posts_router)


@app.get("/")
def root():
    return {
        "message": "AI Image Content Matching Engine API"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }