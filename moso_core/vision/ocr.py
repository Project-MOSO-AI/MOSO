from __future__ import annotations

import logging
from typing import Optional

from moso_core.vision.models import BoundingBox, OCRResult

logger = logging.getLogger(__name__)

_OCR_AVAILABLE = None


def _get_tesseract():
    global _OCR_AVAILABLE
    if _OCR_AVAILABLE is None:
        try:
            import pytesseract
            _OCR_AVAILABLE = pytesseract
        except ImportError:
            _OCR_AVAILABLE = False
    return _OCR_AVAILABLE


def extract_text(image) -> str:
    t = _get_tesseract()
    if not t:
        return ""
    try:
        text = t.image_to_string(image)
        return text.strip() if text else ""
    except Exception as e:
        logger.warning("OCR text extraction failed: %s", e)
        return ""


def extract_text_regions(image) -> list[OCRResult]:
    t = _get_tesseract()
    if not t:
        logger.warning("pytesseract not installed, OCR disabled")
        return []
    try:
        data = t.image_to_data(image, output_type=t.Output.DICT)
        results: list[OCRResult] = []
        for i in range(len(data.get("text", []))):
            text = (data["text"][i] or "").strip()
            if not text:
                continue
            conf_str = data.get("conf", [None])[i]
            conf = 0.0
            if conf_str is not None:
                try:
                    conf = float(conf_str) if conf_str != "-1" else 0.0
                except (ValueError, TypeError):
                    conf = 0.0
            left = data.get("left", [0])[i] or 0
            top = data.get("top", [0])[i] or 0
            width = data.get("width", [0])[i] or 0
            height = data.get("height", [0])[i] or 0
            if width < 2 or height < 2:
                continue
            results.append(OCRResult(
                text=text,
                confidence=conf,
                bounding_box=BoundingBox(left=left, top=top, width=width, height=height),
            ))
        return results
    except Exception as e:
        logger.warning("OCR region extraction failed: %s", e)
        return []
