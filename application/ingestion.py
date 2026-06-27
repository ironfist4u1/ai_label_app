import json
import logging
from io import BytesIO
import pdfplumber
import base64
import xml.etree.ElementTree as ET
from engine import extract_pdf_vision_api
from config import env

logger = logging.getLogger("IngestionPipeline")


def parse_application_data(uploaded_file, format_type: str) -> list[dict]:
    """
    Acts as a router. Takes an uploaded file and its format,
    and routes it to the correct parser.
    Always returns a list of standardized dictionaries.
    """
    try:
        if format_type == "JSON Manifest":
            data = json.load(uploaded_file)
            return data if isinstance(data, list) else [data]

        elif format_type == "PDF Forms":
            logger.info("Rerouting to PDF extraction pipeline...")
            return extract_from_pdf(uploaded_file)

        elif format_type == "XML Export":
            logger.info("Rerouting to XML parsing pipeline...")
            return extract_from_xml(uploaded_file)

        elif format_type == "JPEG Scans":
            logger.info("Rerouting to XML parsing pipeline...")
            buffer = BytesIO()
            uploaded_file.save(buffer, format="JPEG")
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return extract_pdf_vision_api([encoded])

        else:
            raise ValueError(f"Unsupported format: {format_type}")

    except Exception as e:
        logger.error(f"Failed to ingest {format_type}: {e}", exc_info=True)
        raise


def extract_from_pdf(uploaded_file) -> list[dict]:
    """
    Hybrid PDF extraction.
    Attempts standard text scraping first. Falls back to AI Vision if the PDF is a scanned image.
    """
    raw_text = ""

    # 1. Attempt Standard Text Extraction
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    raw_text += extracted + "\n"
    except Exception as e:
        logger.warning(f"Standard PDF extraction failed: {e}")

    # 2. Evaluate Success
    # If we got decent text length, it's a digital PDF. We can parse it.
    if len(raw_text.strip()) > 500:
        logger.info("PDF recognized as Digital. Parsing via Rules...")
        return _parse_raw_text_to_dict(raw_text)

    # 3. AI Fallback Triggered (It's a scanned image)
    else:
        logger.info(
            "PDF recognized as Scanned Image. Rerouting to AI Vision Extractor..."
        )
        return _ai_pdf_extraction(uploaded_file)


def _parse_raw_text_to_dict(raw_text: str) -> list[dict]:
    raw_app_data_sections = []
    lines = raw_text.split("\n")
    for _, line in enumerate(lines):
        if line.count(":") > 0:
            key, value = line.split(":", maxsplit=1)
            parsed_key = key.lower().replace("-", "_").replace(" ", "_")
            parsed_value = value.replace('"', '\\"').rstrip().strip()
            raw_app_data_sections.append(f'"{parsed_key}": "{parsed_value}"')
    raw_app_data = "{\n" + ",\n".join(raw_app_data_sections) + "\n}"
    app_data = json.loads(raw_app_data)
    if app_data.get(env.get("LABEL_FILE_KEY"), ""):
        # now we can assume if the label files key exists.
        app_data[env.get("LABEL_FILE_KEY")] = json.loads(
            app_data[env.get("LABEL_FILE_KEY")].replace("'", '"')
        )
    return [app_data]


def _ai_pdf_extraction(uploaded_file) -> list[dict]:
    """Converts the PDF to images and uses the AI Vision pipeline to extract the data."""
    images_b64 = []

    # 1. Rasterize PDF pages to images
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                # Convert the page to an image object
                im = page.to_image(resolution=150).original

                # Save the image to a bytes buffer
                buffer = BytesIO()
                im.save(buffer, format="JPEG")

                # Encode to base64
                encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
                images_b64.append(encoded)

    except Exception as e:
        logger.error(f"Failed to rasterize PDF for AI extraction: {e}")
        raise ValueError("Could not convert PDF to images for analysis.")

    # 2. Pass the base64 images to the specialized Vision endpoint
    if images_b64:
        return extract_pdf_vision_api(images_b64)
    else:
        raise ValueError("No readable pages found in PDF.")


def extract_from_xml(uploaded_file) -> list[dict]:
    """Parses an XML file and extracts expected COLA fields."""
    try:
        # Streamlit uploaded files are byte streams, so we parse directly
        tree = ET.parse(uploaded_file)
        root = tree.getroot()

        applications = []

        for app_node in root.findall(".//Application"):
            app_data = {}
            for child in app_node:
                # Normalize tags to match your schema keys (e.g., 'BrandName' -> 'brand_name')
                key = child.tag.lower().replace("-", "_")
                app_data[key] = child.text.strip() if child.text else ""

            applications.append(app_data)

        # Fallback if no <Application> nodes were found (single app XML)
        if not applications:
            single_app = {child.tag.lower(): child.text for child in root}
            applications.append(single_app)

        return applications

    except ET.ParseError as e:
        logger.error(f"XML Parsing failed: {e}")
        raise ValueError("Invalid XML format.")
