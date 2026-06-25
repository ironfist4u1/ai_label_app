from PIL import Image, ImageEnhance, ImageFile
import io
import base64
from pathlib import Path
from logging import getLogger


logger = getLogger(__name__)


def preprocess_image_for_ai(uploaded_file, target_width=1500, contrast=1.5):
    """Resizes and enhances image contrast to help the Vision Model read text."""
    img = get_image(uploaded_file)
    img = resize_image(img, target_width)
    img = boost_contrast(img, contrast)
    return encode_for_transfer(img)


def get_image(uploaded_file: Path) -> ImageFile.ImageFile:
    try:
        return Image.open(uploaded_file)
    except Exception as e:
        logger.error("Failed to open an image file given. Error: %s", str(e))
        raise e


def resize_image(img: ImageFile.ImageFile, target_width=1500):
    if img.width < target_width:
        ratio = target_width / img.width
        new_height = int(img.height * ratio)
        # LANCZOS is a high-quality resampling filter great for text
        img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
    return img


def boost_contrast(img: ImageFile.ImageFile, contrast: float = 1.5):
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(contrast)
    return img


def encode_for_transfer(img: ImageFile.ImageFile):
    buffered = io.BytesIO()
    # Save as JPEG to keep the payload size small for fast API transmission
    img.save(buffered, format="JPEG", quality=95) 
    return base64.b64encode(buffered.getvalue()).decode("utf-8")
