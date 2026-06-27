"""
ocr_engine.py — Image preprocessing and Tesseract OCR pipeline.

Improvements over the original ocr_test.py:
  • Deskewing (corrects tilted scans)
  • CLAHE contrast enhancement (better for faded documents)
  • Sharpening kernel
  • Confidence score reporting
  • Camera / file dual input support
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image

import config

# ─────────────────────────────────────────────────────────
# Configure Tesseract
# ─────────────────────────────────────────────────────────
pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_PATH


# ─────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────

def _deskew(image: np.ndarray) -> np.ndarray:
    """Correct skew using image moments."""
    coords = np.column_stack(np.where(image > 0))
    if len(coords) < 5:
        return image
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h),
                             flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
    return rotated


def _sharpen(image: np.ndarray) -> np.ndarray:
    """Apply a mild unsharp-mask style sharpening."""
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    return cv2.filter2D(image, -1, kernel)


# ─────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────

def preprocess_image(path: str) -> np.ndarray:
    """
    Load an image from *path* and apply the full preprocessing
    pipeline suitable for Indian identity documents.

    Returns a binary (thresholded) NumPy array ready for OCR.
    Raises FileNotFoundError if the image cannot be loaded.
    """
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"Cannot load image: {path}")

    # 1 — Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2 — Upscale (critical for small text)
    gray = cv2.resize(gray, None, fx=2.5, fy=2.5,
                      interpolation=cv2.INTER_CUBIC)

    # 3 — Deskew (do this early before distortion)
    gray = _deskew(gray)

    # 4 — Bilateral Filter (Removes holograms/noise while keeping edges sharp)
    gray = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

    # 5 — CLAHE (adaptive histogram equalisation for faded docs)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # 6 — Adaptive threshold
    gray = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 2
    )

    # 7 — Morphological Closing (Stitches broken letters together)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)

    # 8 — Sharpening
    gray = _sharpen(gray)

    return gray


def preprocess_from_array(img: np.ndarray) -> np.ndarray:
    """Same pipeline but accepts an existing OpenCV image array (e.g. from camera)."""
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    cv2.imwrite(tmp.name, img)
    result = preprocess_image(tmp.name)
    os.unlink(tmp.name)
    return result


def run_ocr(processed: np.ndarray) -> dict:
    """
    Run Tesseract on a preprocessed image array.

    Returns:
        {
          'text': str,           # full raw OCR text
          'confidence': float,   # mean word confidence (0-100)
          'words': list[dict]    # per-word detail from pytesseract
        }
    """
    # Changed PSM from 4 to 6 (Assume a single uniform block of text)
    config_str = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(processed, config=config_str)

    # Per-word confidence
    try:
        data = pytesseract.image_to_data(processed,
                                         config=config_str,
                                         output_type=pytesseract.Output.DICT)
        confs = [int(c) for c in data['conf'] if str(c) != '-1']
        confidence = round(sum(confs) / len(confs), 1) if confs else 0.0
        words = [
            {'word': data['text'][i], 'conf': int(data['conf'][i])}
            for i in range(len(data['text']))
            if data['text'][i].strip() and str(data['conf'][i]) != '-1'
        ]
    except Exception:
        confidence = 0.0
        words = []

    return {
        'text': text,
        'confidence': confidence,
        'words': words
    }


def capture_from_camera(device_index: int = 0) -> np.ndarray:
    """
    Capture a single frame from a webcam or scanner.
    Returns the raw BGR image array.
    Raises RuntimeError if the camera cannot be opened.
    """
    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera device {device_index}")
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError("Failed to capture frame from camera")
    return frame


def numpy_to_pil(image: np.ndarray) -> Image.Image:
    """Convert a preprocessed numpy array to a PIL Image (for Tkinter display)."""
    return Image.fromarray(image)
