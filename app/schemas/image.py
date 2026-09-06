from pydantic import BaseModel, HttpUrl

class ImageCreate(BaseModel):
    url: HttpUrl