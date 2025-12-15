# main.py - FINAL PRODUCTION VERSION FOR RASPBERRY PI 5

import serial
import time
import logging
import os
import json
import cv2 
from datetime import datetime
from pathlib import Path
from picamera2 import Picamera2
from typing import Tuple, Optional, Union
import re # Ensure regex is imported for the updated parser

# Local imports
from ml_utils import load_models, detect_and_crop_license_plate, ocr_license_plate
from student_db import verify_scanned_plate, init_student_db

# ================== LOGGING (auto-saves next to this file) ==================
SCRIPT_DIR = Path(__file__).parent.resolve()
LOG_FILE = SCRIPT_DIR / "security_system.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info("=== VEHICLE VERIFICATION SYSTEM STARTED ===")
logger.info(f"Log file: {LOG_FILE}")

# ================== PATHS (all relative to script) ==================
PHOTO_DIR = SCRIPT_DIR / "photos"
FLAGGED_DIR = SCRIPT_DIR / "FLAGGED"
SENSOR_JSON = SCRIPT_DIR / "latest_sensor.json"

PHOTO_DIR.mkdir(exist_ok=True)
FLAGGED_DIR.mkdir(exist_ok=True)

# ================== CONFIG ==================
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 9600
DISTANCE_THRESHOLD = 10.0  # Threshold is against the raw incoming number (unit-agnostic)

previous_distance = None
picam = Picamera2()

# ================== SHARED SENSOR DATA FOR STREAMLIT ==================
def save_latest_sensor_data(temp: float, battery: float, distance_value: float):
    """
    Saves sensor data to JSON, using the raw incoming distance value.
    """
    data = {
        # Use None for JSON if the sentinel value is present
        "temperature": round(temp, 1) if temp != -999.0 else None,
        "battery": round(battery, 1) if battery != -1.0 else None,
        "distance": round(distance_value, 1), # Use the raw value
        "last_update": datetime.now().isoformat()
    }
    try:
        with open(SENSOR_JSON, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Failed to write {SENSOR_JSON}: {e}")

# ================== SERIAL PARSING (UPDATED for % sign) ==================

def _extract_and_convert(part_str: str, sentinel_value: float) -> float:
    """
    Helper to extract a value string, strip non-numeric units (like '%'), 
    convert to float, or return sentinel.
    """
    try:
        # Extract the string value after the colon
        str_value = part_str.split(':')[-1].strip()
        
        if str_value == "N/A":
            return sentinel_value
        
        # --- FIX: Use regex to find and extract the numerical part ---
        # This handles the '%' sign and ensures only the number is converted.
        match = re.search(r'[-+]?\d*\.?\d+', str_value)
        if match:
            str_value = match.group(0)
        else:
            # If no number is found, treat as an error/sentinel
            logger.warning(f"No numeric value found in string: {str_value}")
            return sentinel_value
        # --- END FIX ---

        return float(str_value)
    except ValueError:
        logger.warning(f"Conversion error for: {part_str}")
        return sentinel_value

def parse_serial_line(line: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    # Define sentinels used by the ESP32 code
    DISTANCE_SENTINEL = -1.0
    TEMP_SENTINEL = -999.0
    
    try:
        line = line.strip()
        parts = line.split(',')
        if len(parts) != 3:
            logger.warning(f"Malformed serial line (part count): {line}")
            return None, None, None

        # Parse all three values
        distance_value = _extract_and_convert(parts[0], DISTANCE_SENTINEL)
        temp = _extract_and_convert(parts[1], TEMP_SENTINEL)
        battery = _extract_and_convert(parts[2], DISTANCE_SENTINEL) # Use -1.0 for battery sentinel

        # Apply Core Requirement: Skip if Distance is N/A
        if distance_value == DISTANCE_SENTINEL:
            logger.warning(f"Skipping line due to distance N/A: {line}")
            return None, None, None
        
        # Success: Return distance, temp, and battery
        return distance_value, temp, battery

    except Exception as e:
        logger.error(f"Fatal error during line processing: '{line}' Error: {e}")
        return None, None, None

# ================== CAMERA (UNCHANGED) ==================
def capture_photo() -> str | None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    photo_path = PHOTO_DIR / f"{timestamp}.jpg"
    try:
        picam.capture_file(str(photo_path))
        logger.info(f"Photo captured: {photo_path.name}")
        return str(photo_path)
    except Exception as e:
        logger.error(f"Camera capture failed: {e}")
        return None

# ================== MAIN (FINAL PRODUCTION LOOP) ==================
def main():
    global previous_distance

    init_student_db()
    load_models()

    # Camera init
    try:
        picam.configure(picam.create_still_configuration()) 
        picam.start()
        time.sleep(2) 
        logger.info("PiCamera2 started successfully")
    except Exception as e:
        logger.critical(f"Camera failed: {e}")
        return

    # Serial init
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        logger.info(f"Serial connected: {SERIAL_PORT} @ {BAUD_RATE}")
    except Exception as e:
        logger.critical(f"Serial port error: {e}")
        logger.critical("Run `sudo usermod -aG dialout magnus && sudo reboot` if needed")
        return

    print("\nSYSTEM READY — Waiting for vehicle...\n")

    try:
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                if line.startswith("distance:"): # <--- Correctly filters for your desired line format
                    
                    distance_value, temp, battery = parse_serial_line(line)
                    
                    if distance_value is None:
                        continue 
                    
                    # --- Prepare for Console Print ---
                    print_dist = f"{distance_value:6.1f}"
                    # The following lines correctly handle the sentinel values (-999.0 and -1.0)
                    # which are returned by parse_serial_line when it encounters "N/A".
                    print_temp = "N/A" if temp == -999.0 else f"{temp:5.1f}°F"
                    print_batt = "N/A" if battery == -1.0 else f"{battery:5.1f}%"
                    
                    # Print the data
                    print(f"Dist: {print_dist} | Temp: {print_temp} | Batt: {print_batt}")
                    
                    # Save data to JSON (uses the raw value)
                    save_latest_sensor_data(temp, battery, distance_value)

                    # Trigger Logic (Compares raw value directly to 50.0)
                    if (distance_value < DISTANCE_THRESHOLD):

                        logger.info(f"VEHICLE DETECTED (< {DISTANCE_THRESHOLD}) — Processing...")
                        
                        # === CAMERA CAPTURE (Live Picam) ===
                        photo_path = capture_photo()
                        
                        if not photo_path:
                            previous_distance = distance_value
                            continue

                        # --- ML Pipeline ---
                        cropped, yolo_conf = detect_and_crop_license_plate(photo_path)
                        
                        if cropped is not None:
                            plate_text, ocr_conf = ocr_license_plate(cropped)
                            confidence = round((yolo_conf + ocr_conf) / 2, 3)

                            if plate_text:
                                result = verify_scanned_plate(plate_text, confidence)
                                if result['match_found']:
                                    os.remove(photo_path)
                                    logger.info(f"AUTHORIZED: {result['student_info']['name']} — {plate_text}")
                                    print(f"  AUTHORIZED: {result['student_info']['name']}")
                                else:
                                    flagged = FLAGGED_DIR / Path(photo_path).name
                                    os.rename(photo_path, flagged)
                                    logger.warning(f"UNAUTHORIZED → FLAGGED: {plate_text}")
                                    print(f"  UNAUTHORIZED → FLAGGED")
                            else:
                                # No text recognized
                                flagged_name = f"{Path(photo_path).stem}_cropped.jpg"
                                flagged = FLAGGED_DIR / flagged_name
                                try:
                                    cv2.imwrite(str(flagged), cropped)
                                    os.remove(photo_path)
                                    logger.warning(f"No text recognized → FLAGGED (cropped saved: {flagged.name})")
                                    print("  No plate text → FLAGGED (cropped saved)")
                                except Exception as e:
                                    # Fallback: move full photo if saving crop fails
                                    flagged_full = FLAGGED_DIR / Path(photo_path).name
                                    os.rename(photo_path, flagged_full) 
                                    logger.error(f"Failed to save cropped image: {e} — moved full photo to FLAGGED")
                                    print("  No plate text → FLAGGED (full photo moved)")
                        else:
                            # No plate detected
                            flagged = FLAGGED_DIR / Path(photo_path).name
                            os.rename(photo_path, flagged)
                            logger.warning("No plate detected → FLAGGED")
                            print("  No plate detected → FLAGGED")

                        time.sleep(4)  # Prevent rapid re-trigger

                    previous_distance = distance_value 

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
    finally:
        # Ensure camera and serial are closed gracefully
        try:
            picam.stop()
        except Exception:
            pass 
        ser.close()
        logger.info("System stopped")

if __name__ == "__main__":
    main()