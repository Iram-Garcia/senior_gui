# ml_utils.py - UPDATED FOR YOLOv11
"""
Machine Learning utilities: License Plate Detection (YOLOv11) + OCR (EasyOCR)
Optimized for Raspberry Pi 5
"""
import cv2
import easyocr
import torch
import logging
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
import re 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global model instances (load once)
yolo_model = None
ocr_reader = None

# === UPDATE: POINTING TO NEW YOLOv11 MODEL ===
# Assumes structure:
#   project_root/
#     ├── ml_utils.py
#     └── interface/
#           └── license-plate-finetune-v1l.pt
MODEL_PATH = Path(__file__).parent / "interface" / "license-plate-finetune-v1l.pt"
CONF_THRESHOLD = 0.4


def load_models():
    """Load YOLOv11 and EasyOCR models once at startup."""
    global yolo_model, ocr_reader

    if yolo_model is None:
        try:
            from ultralytics import YOLO
            
            # === SAFETY FIX: PyTorch Safe Globals ===
            # Required for loading custom trained models in newer PyTorch versions
            from ultralytics.nn.tasks import DetectionModel
            torch.serialization.add_safe_globals([DetectionModel])
            # ========================================

            if not MODEL_PATH.exists():
                raise FileNotFoundError(f"YOLO model not found at {MODEL_PATH}")
            
            logger.info(f"Loading YOLOv11 model from: {MODEL_PATH}")
            yolo_model = YOLO(str(MODEL_PATH))
            yolo_model.to('cpu')  # Pi 5 has no strong GPU, use CPU
            logger.info("YOLOv11 model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            raise

    if ocr_reader is None:
        try:
            # === FIX: EasyOCR 'get_textbox' Error ===
            # detector=True is required to avoid AttributeError in some environments
            ocr_reader = easyocr.Reader(['en'], gpu=False, detector=True, recognizer=True)
            logger.info("EasyOCR reader initialized (Detector Enabled)")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            raise


def detect_and_crop_license_plate(image_path: str) -> Tuple[Optional[np.array], float]:
    """
    Detect license plate using YOLOv11 and return cropped image + confidence.
    """
    global yolo_model

    try:
        # Run inference
        # NOTE: YOLOv11 'Large' is slower. If it hangs on Pi, add imgsz=320 here to speed up.
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
    Perform OCR on cropped license plate using the raw image, then clean the result.
    """
    global ocr_reader

    try:
        # Use the raw cropped image directly
        result = ocr_reader.readtext(cropped_img, detail=1, paragraph=False)

        if not result:
            return "", 0.0

        # Extract text and confidence
        texts = []
        confs = []
        for (_, text, conf) in result:
            # Clean text: remove non-alphanumeric characters and convert to uppercase
            cleaned = ''.join(c for c in text if c.isalnum()).upper()
            if cleaned:
                texts.append(cleaned)
                confs.append(conf)

        if not texts:
            return "", 0.0

        plate_text = ''.join(texts)
        avg_conf = sum(confs) / len(confs)
        
        # === TEXT CLEANUP LOGIC (Optimized for Texas Plates) ===
        
        # 1. Aggressive String Removal
        cleaned_text = plate_text
        cleaned_text = cleaned_text.replace("THELONESTARSTATEKUAD", "")
        cleaned_text = cleaned_text.replace("THELONESTARSTATE", "")
        cleaned_text = cleaned_text.replace("TEXAS", "")
        
        # 2. Final Extraction using Regex
        # Looks for the longest contiguous block of 6-8 alphanumeric chars
        matches = re.findall(r'[A-Z0-9]{6,8}', cleaned_text)
        
        final_plate = ""
        if matches:
            final_plate = max(matches, key=len)
        else:
            final_plate = cleaned_text
            
        plate_text = final_plate
        
        # === END CLEANUP LOGIC ===

        logger.info(f"OCR Result: '{plate_text}' | Confidence: {avg_conf:.3f}")
        return plate_text, avg_conf

    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return "", 0.0