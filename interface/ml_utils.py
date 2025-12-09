# ml_utils.py
"""
Machine Learning utilities: License Plate Detection (YOLOv8) + OCR (EasyOCR)
Optimized for Raspberry Pi 5
"""
import cv2
import easyocr
import torch
import logging
from pathlib import Path
from typing import Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model instances (load once)
yolo_model = None
ocr_reader = None

# Paths
MODEL_PATH = Path(__file__).parent / "LP-detection.pt"
CONF_THRESHOLD = 0.4


def load_models():
    """Load YOLOv8 and EasyOCR models once at startup."""
    global yolo_model, ocr_reader

    if yolo_model is None:
        try:
            from ultralytics import YOLO
            if not MODEL_PATH.exists():
                raise FileNotFoundError(f"YOLO model not found at {MODEL_PATH}")
            yolo_model = YOLO(str(MODEL_PATH))
            yolo_model.to('cpu')  # Pi 5 has no strong GPU, use CPU
            logger.info("YOLOv8 model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise

    if ocr_reader is None:
        try:
            # language='en' for better plate reading, gpu=False for Pi
            ocr_reader = easyocr.Reader(['en'], gpu=False, detector=False, recognizer=True)
            logger.info("EasyOCR reader initialized")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            raise


def detect_and_crop_license_plate(image_path: str) -> Tuple[Optional[cv2.UMat], float]:
    """
    Detect license plate using YOLOv8 and return cropped image + confidence.
    Returns (cropped_img, best_confidence) or (None, 0.0)
    """
    global yolo_model

    try:
        results = yolo_model(image_path, conf=CONF_THRESHOLD, verbose=False)[0]
        if len(results.boxes) == 0:
            logger.info("No license plate detected")
            return None, 0.0

        # Get best detection
        best_box = results.boxes[0]
        conf = float(best_box.conf.cpu().numpy())
        x1, y1, x2, y2 = map(int, best_box.xyxy[0].cpu().numpy())

        img = cv2.imread(image_path)
        cropped = img[y1:y2, x1:x2]

        logger.info(f"License plate detected with confidence: {conf:.3f}")
        return cropped, conf

    except Exception as e:
        logger.error(f"Error in YOLO detection: {e}")
        return None, 0.0


def ocr_license_plate(cropped_img) -> Tuple[str, float]:
    """
    Perform OCR on cropped license plate.
    Returns (plate_text, avg_confidence)
    """
    global ocr_reader

    try:
        result = ocr_reader.readtext(cropped_img, detail=1, paragraph=False)

        if not result:
            return "", 0.0

        # Extract text and confidence
        texts = []
        confs = []
        for (_, text, conf) in result:
            cleaned = ''.join(c for c in text if c.isalnum()).upper()
            if cleaned:
                texts.append(cleaned)
                confs.append(conf)

        if not texts:
            return "", 0.0

        plate_text = ''.join(texts)
        avg_conf = sum(confs) / len(confs)

        logger.info(f"OCR Result: '{plate_text}' | Confidence: {avg_conf:.3f}")
        return plate_text, avg_conf

    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return "", 0.0