from urllib.request import urlopen

from app.db.database import SessionLocal
from app.services.vision_service import analyze_image

IMAGE_URL = "https://goo.gle/instrument-img"

db = SessionLocal()

try:
    with urlopen(IMAGE_URL) as response:
        image_bytes = response.read()
        mime_type = response.headers.get_content_type()

    result = analyze_image(
        image_bytes,
        mime_type,
        db,
    )

    print(result.model_dump_json(indent=2))

finally:
    db.close()