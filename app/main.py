from fastapi import FastAPI

from app.api.routes.images import router as images_router


app = FastAPI(title="AI Image Content Matching Engine")


app.include_router(images_router)


@app.get("/")
def root():
    return {"message": "AI Image Content Matching Engine API"}