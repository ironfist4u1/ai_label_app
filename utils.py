from PIL import Image, ImageEnhance
import io
import base64


def preprocess_image_for_ai(uploaded_file, target_width=1500):
    """Resizes and enhances image contrast to help the Vision Model read text."""
    # Open the image using Pillow
    img = Image.open(uploaded_file)

    # 1. Upscale/Resize (if the image is too small)
    # Vision models love high resolution, but usually cap out around 1500-2000px
    if img.width < target_width:
        ratio = target_width / img.width
        new_height = int(img.height * ratio)
        # LANCZOS is a high-quality resampling filter great for text
        img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)

    # 2. Enhance Contrast (makes faded text pop against the background)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)  # Boost contrast by 50%

    # 3. Convert back to Base64 for the API
    buffered = io.BytesIO()
    # Save as JPEG to keep the payload size small for fast API transmission
    img.save(buffered, format="JPEG", quality=95) 
    return base64.b64encode(buffered.getvalue()).decode("utf-8")
