from fastapi import FastAPI

app = FastAPI(title = "AI Image Content Matching Engine")

@app.get("/")
def root():
    return {"message": "AI Image Content Matching Engine API"}