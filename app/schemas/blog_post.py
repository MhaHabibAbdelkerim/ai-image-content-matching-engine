from pydantic import BaseModel

class BlogPostCreate(BaseModel):
    title: str
    content: str
    