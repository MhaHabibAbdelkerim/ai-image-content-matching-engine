from urllib.request import urlopen

from app.services.vision_service import analyze_image


IMAGE_URL = "https://goo.gle/instrument-img"


with urlopen(IMAGE_URL) as response:
    image_bytes = response.read()
    mime_type = response.headers.get_content_type()


result = analyze_image(image_bytes, mime_type)

print(result.model_dump_json(indent=2))