# ml_utils.py - FINAL WORKING VERSION (Minimal Fixes)
"""
Machine Learning utilities: License Plate Detection (YOLOv8) + OCR (EasyOCR)
Optimized for Raspberry Pi 5
"""
import cv2
import easyocr
import torch
import logging
import numpy as np # Added for consistency in typing, even though not used for preprocessing
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
            
            # === FIX 1: YOLO/PyTorch Load Error ===
            # This is mandatory for newer PyTorch versions to load the model securely.
            from ultralytics.nn.tasks import DetectionModel
            torch.serialization.add_safe_globals([DetectionModel])
            # ======================================

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
            # === FIX 2: EasyOCR 'get_textbox' Error ===
            # Even though the original used detector=False, the current environment 
            # requires detector=True to avoid the 'get_textbox' AttributeError.
            ocr_reader = easyocr.Reader(['en'], gpu=False, detector=True, recognizer=True)
            logger.info("EasyOCR reader initialized (Detector Enabled)")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            raise


def detect_and_crop_license_plate(image_path: str) -> Tuple[Optional[np.array], float]:
    """
    Detect license plate using YOLOv8 and return cropped image + confidence.
    NOTE: Using np.array type hint for cv2.imread compatibility.
    """
    global yolo_model

    try:
        # NOTE: Using cv2.imread/numpy array for the image data
        results = yolo_model(image_path, conf=CONF_THRESHOLD, verbose=False)[0]
        if len(results.boxes) == 0:
            logger.info("No license plate detected")
            return None, 0.0

        # Get best detection
        best_box = results.boxes[0]
        conf = float(best_box.conf.cpu().numpy())
        x1, y1, x2, y2 = map(int, best_box.xyxy[0].cpu().numpy())

        img = cv2.imread(image_path)
        if img is None:
             logger.error(f"Could not read image file: {image_path}")
             return None, 0.0
             
        cropped = img[y1:y2, x1:x2]

        logger.info(f"License plate detected with confidence: {conf:.3f}")
        return cropped, conf

    except Exception as e:
        logger.error(f"Error in YOLO detection: {e}")
        return None, 0.0


def ocr_license_plate(cropped_img: np.array) -> Tuple[str, float]:
    """
    Perform OCR on cropped license plate using the raw image.
    (REVERTED: Removed all preprocessing steps)
    """
    global ocr_reader

    try:
        # Use the raw cropped image directly (as in the original working version)
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