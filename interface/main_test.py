# main_test.py - ML PIPELINE TESTING VERSION (FINAL)
# Combines: Image Queue, Simple Distance Trigger, and Robust Serial Parsing.

import serial
import time
import logging
import os
import random
import json # Explicitly import json
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional # For type hinting

# Local imports
from ml_utils import load_models, detect_and_crop_license_plate, ocr_license_plate
from student_db import verify_scanned_plate, init_student_db

# ================== LOGGING SETUP ==================
SCRIPT_DIR = Path(__file__).parent.resolve()
LOG_FILE = SCRIPT_DIR / "security_system_test.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info("=== VEHICLE VERIFICATION SYSTEM (TESTING MODE) STARTED ===")
logger.info(f"Log file: {LOG_FILE}")

# ================== PATHS (Using original production folder names) ==================
TEST_PHOTO_DIR = SCRIPT_DIR / "test_images" # Input source for test images
FLAGGED_DIR = SCRIPT_DIR / "FLAGGED"       # Output folder for unauthorized
SENSOR_JSON = SCRIPT_DIR / "latest_sensor.json" # Output file for Streamlit data

TEST_PHOTO_DIR.mkdir(exist_ok=True)
FLAGGED_DIR.mkdir(exist_ok=True)

# ================== CONFIG ==================
SERIAL_PORT = "/dev/ttyUSB0" # Use Pi default for the test environment
BAUD_RATE = 9600
DISTANCE_THRESHOLD = 50.0  # Simple trigger threshold

previous_distance = None

# ================== IMAGE QUEUE SETUP ==================
image_files = [f for f in TEST_PHOTO_DIR.glob('*') if f.suffix.lower() in ['.jpg', '.jpeg', '.png']]
IMAGE_QUEUE = image_files * 3
random.shuffle(IMAGE_QUEUE)
logger.info(f"Loaded {len(IMAGE_QUEUE)} test images into queue.")

# ================== SHARED SENSOR DATA FOR STREAMLIT ==================
def save_latest_sensor_data(temp: float, battery: float, distance: float):
    # Same logic as your working main.py
    data = {
        "temperature": round(temp, 1),
        "battery": round(battery, 1),
        "distance": round(distance, 1),
        "last_update": datetime.now().isoformat()
    }
    try:
        with open(SENSOR_JSON, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Failed to write {SENSOR_JSON}: {e}")

# ================== SERIAL PARSING (APPLIED FIX) ==================
def parse_serial_line(line: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Applies the robust parsing logic from your working main.py"""
    try:
        # NOTE: This logic assumes data is comma-separated but strips all headers/units 
        parts = line.strip().replace("Distance:", "").replace("Temperature:", "").replace("Battery:", "").split(",")
        if len(parts) != 3:
            return None, None, None
            
        distance = float(parts[0].strip().replace("cm", "")) 
        temp = float(parts[1].strip().replace("°F", ""))
        battery = float(parts[2].strip().replace("%", ""))
        
        return distance, temp, battery
    except Exception:
        return None, None, None

# ================== CAMERA MOCK FUNCTION ==================
def capture_photo_mock() -> str | None:
    """Mocks the camera capture by taking the next image from the queue."""
    global IMAGE_QUEUE

    if not IMAGE_QUEUE:
        logger.warning("Image queue is empty. Refill the 'test_images' folder.")
        return None
    
    photo_path = IMAGE_QUEUE.pop(0)
    logger.info(f"MOCK Photo captured: {photo_path.name}")
    return str(photo_path)

# ================== MAIN ==================
def main():
    global previous_distance, IMAGE_QUEUE

    init_student_db()
    load_models()

    if not IMAGE_QUEUE:
        logger.critical(f"FATAL: No images found in {TEST_PHOTO_DIR}. Please add test images.")
        return

    # Serial init
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        logger.info(f"Serial connected: {SERIAL_PORT} @ {BAUD_RATE}")
    except Exception as e:
        logger.critical(f"Serial port error: {e}")
        logger.critical("Check serial port or run `sudo usermod -aG dialout user && sudo reboot`")
        return

    print("\nSYSTEM READY (TESTING MODE) — Waiting for simulated trigger...\n")

    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                # Check for the key phrase to ensure it's sensor data
                if "Distance:" in line: 
                    distance, temp, battery = parse_serial_line(line)
                    if distance is None:
                        continue

                    print(f"Dist: {distance:6.1f}cm | Temp: {temp:5.1f}°F | Batt: {battery:5.1f}%")
                    save_latest_sensor_data(temp, battery, distance)

                    # Trigger when distance is less than the threshold (50 cm)
                    if distance < DISTANCE_THRESHOLD:

                        logger.info(f"VEHICLE DETECTED (< {DISTANCE_THRESHOLD}cm) — Processing...")
                        photo_path = capture_photo_mock()
                        if not photo_path:
                            previous_distance = distance
                            time.sleep(1) 
                            continue

                        # --- ML Pipeline ---
                        cropped, yolo_conf = detect_and_crop_license_plate(photo_path)
                        
                        if cropped is not None:
                            plate_text, ocr_conf = ocr_license_plate(cropped)
                            overall_conf = round((yolo_conf + ocr_conf) / 2, 3)
                            
                            if plate_text:
                                result = verify_scanned_plate(plate_text, overall_conf)
                                if result['match_found']:
                                    logger.info(f"AUTHORIZED: {result['student_info']['name']} — {plate_text}")
                                    print(f"  AUTHORIZED: {result['student_info']['name']}")
                                else:
                                    logger.warning(f"UNAUTHORIZED → IMAGE PATH: {Path(photo_path).name}")
                                    print(f"  UNAUTHORIZED → IMAGE PATH: {Path(photo_path).name}")
                            else:
                                logger.warning(f"No text recognized → IMAGE PATH: {Path(photo_path).name}")
                                print(f"  No plate text → IMAGE PATH: {Path(photo_path).name}")
                        else:
                            logger.warning(f"No plate detected → IMAGE PATH: {Path(photo_path).name}")
                            print(f"  No plate detected → IMAGE PATH: {Path(photo_path).name}")

                        time.sleep(4)  # Prevent rapid re-trigger

                    previous_distance = distance

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
    finally:
        ser.close()
        logger.info("System stopped")

if __name__ == "__main__":
    main()