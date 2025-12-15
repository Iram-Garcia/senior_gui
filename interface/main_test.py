# main_test.py - ML PIPELINE TESTING VERSION (FINAL)
# Combines: Image Queue, Simple Distance Trigger, and Robust Serial Parsing.

import serial
import time
import logging
import os
import random
import json
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional, Union

# Local imports (assuming these remain correct)
# NOTE: You must ensure ml_utils and student_db are available in your environment.
# from ml_utils import load_models, detect_and_crop_license_plate, ocr_license_plate
# from student_db import verify_scanned_plate, init_student_db

# Mock functions for local imports (replace with your actual imports if running)
def load_models(): logger.info("YOLOv8 model loaded successfully")
def init_student_db(): logger.info("Student database initialized at /home/magnus/Documents/senior_gui/interface/students.db")
def verify_scanned_plate(text, conf): return {'match_found': True, 'student_info': {'name': 'AUTHORIZED_TEST'}}
def detect_and_crop_license_plate(path): return "cropped_image", 0.95
def ocr_license_plate(img): return "MAGNUS123", 0.90
# End Mock functions

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

# ================== PATHS ==================
TEST_PHOTO_DIR = SCRIPT_DIR / "test_images" 
FLAGGED_DIR = SCRIPT_DIR / "FLAGGED"      
SENSOR_JSON = SCRIPT_DIR / "latest_sensor.json" 

TEST_PHOTO_DIR.mkdir(exist_ok=True)
FLAGGED_DIR.mkdir(exist_ok=True)

# ================== CONFIG ==================
# Use the correct port identified via USB connection: /dev/ttyUSB0
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 9600
DISTANCE_THRESHOLD = 50.0  
previous_distance = None

# ================== IMAGE QUEUE SETUP ==================
image_files = [f for f in TEST_PHOTO_DIR.glob('*') if f.suffix.lower() in ['.jpg', '.jpeg', '.png']]
IMAGE_QUEUE = image_files * 3
random.shuffle(IMAGE_QUEUE)
logger.info(f"Loaded {len(IMAGE_QUEUE)} test images into queue.")

# ================== SHARED SENSOR DATA FOR STREAMLIT ==================
def save_latest_sensor_data(temp: float, battery: float, distance: float):
    """Saves sensor data, handling sentinel values by making them 0 or None for JSON."""
    data = {
        # Use simple 'N/A' or 0 for JSON if the sentinel value is present
        "temperature": round(temp, 1) if temp != -999.0 else None,
        "battery": round(battery, 1) if battery != -1.0 else None,
        "distance": round(distance, 1),
        "last_update": datetime.now().isoformat()
    }
    try:
        with open(SENSOR_JSON, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Failed to write {SENSOR_JSON}: {e}")

# ================== SERIAL PARSING (CORRECTED & ROBUST) ==================

def _extract_and_convert(part_str: str, sentinel_value: float) -> float:
    """Helper to extract a value string and convert to float or return sentinel."""
    try:
        # Extract the string value after the colon (e.g., ' 55.23' or ' N/A')
        str_value = part_str.split(':')[-1].strip()
        
        if str_value == "N/A":
            return sentinel_value
        
        return float(str_value)
    except ValueError:
        # Catch non-numeric garbage or unexpected format
        logger.warning(f"Conversion error for: {part_str}")
        return sentinel_value

def parse_serial_line(line: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Parses the concise ESP32 format: "distance: X, temperature: Y, battery: Z"
    Returns a tuple of (distance, temp, battery). 
    
    If distance is N/A or line structure is invalid, returns (None, None, None).
    If temp or battery is N/A, returns the sentinel float value (-999.0 or -1.0).
    """
    try:
        line = line.strip()
        parts = line.split(',')
        if len(parts) != 3:
            logger.warning(f"Malformed serial line (part count): {line}")
            return None, None, None

        # Parse all three values, using their respective sentinel values
        distance = _extract_and_convert(parts[0], -1.0)
        temp = _extract_and_convert(parts[1], -999.0)
        battery = _extract_and_convert(parts[2], -1.0)

        # Apply Core Requirement: Skip if Distance is N/A (where -1.0 is the distance sentinel)
        if distance == -1.0:
            logger.warning(f"Skipping line due to distance N/A: {line}")
            return None, None, None # Triggers 'continue' in the main loop
        
        # Success: Return all values as floats (sentinels included for temp/battery)
        return distance, temp, battery

    except Exception as e:
        logger.error(f"Fatal error during line processing: '{line}' Error: {e}")
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
    # Ensure all variables used in global scope are declared here
    global previous_distance, IMAGE_QUEUE

    # Initialization
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
                
                if line.startswith("distance:"): 
                    
                    distance, temp, battery = parse_serial_line(line)
                    
                    # Skip if distance was N/A or line was malformed (distance is None)
                    if distance is None:
                        continue 

                    # --- Prepare for Console Print (Using N/A strings for clarity) ---
                    # Note: distance is guaranteed to be a valid float here
                    print_temp = "N/A" if temp == -999.0 else f"{temp:5.1f}"
                    print_batt = "N/A" if battery == -1.0 else f"{battery:5.1f}"
                    
                    print(f"Dist: {distance:6.1f} | Temp: {print_temp} | Batt: {print_batt}")
                    
                    # Save data to JSON (uses sentinel floats for storage)
                    save_latest_sensor_data(temp, battery, distance)

                    # Trigger Logic (Only runs if distance is a valid number, which is true here)
                    if distance < DISTANCE_THRESHOLD:
                        logger.info(f"VEHICLE DETECTED (< {DISTANCE_THRESHOLD}) — Processing...")
                        photo_path = capture_photo_mock()
                        
                        if not photo_path:
                            previous_distance = distance
                            time.sleep(1)
                            continue

                        # --- ML Pipeline (Unchanged) ---
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