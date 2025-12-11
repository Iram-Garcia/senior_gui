# main.py - FINAL PRODUCTION VERSION FOR RASPBERRY PI 5
# Works for any user (magnus, pi, etc.) — no hardcoded paths!

import serial
import time
import logging
import os
import json # Import json globally as it's used in the new function signature
import cv2  # added: needed to save cropped images
from datetime import datetime
from pathlib import Path
from picamera2 import Picamera2

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

previous_distance = None
picam = Picamera2()

# ================== SHARED SENSOR DATA FOR STREAMLIT ==================
def save_latest_sensor_data(temp: float, battery: float):
    data = {
        "temperature": round(temp, 1),
        "battery": round(battery, 1),
        "last_update": datetime.now().isoformat()
    }
    try:
        import json
        with open(SENSOR_JSON, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Failed to write {SENSOR_JSON}: {e}")

# ================== SERIAL PARSING ==================
def parse_serial_line(line: str):
    try:
        line = line.strip()
        if not line.startswith("Distance:"):
            return None, None, None
        parts = line.replace("Distance:", "").replace("Temperature:", "").replace("Battery:", "").split(",")
        if len(parts) != 3:
            return None, None, None
        distance = float(parts[0].strip())
        temp = float(parts[1].strip())
        battery = float(parts[2].strip().replace("%", ""))
        return distance, temp, battery
    except Exception:
        return None, None, None

# ================== CAMERA ==================
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

# ================== MAIN ==================
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
                line = ser.readline().decode('utf-8', errors='ignore')
                distance, temp, battery = parse_serial_line(line)
                if distance is None:
                    continue

                print(f"Dist: {distance:6.1f}cm | Temp: {temp:5.1f}°F | Batt: {battery:5.1f}%")
                save_latest_sensor_data(temp, battery)

                # Trigger when car gets close (distance drops to ~half)
                if (distance < 50):

                    logger.info("VEHICLE DETECTED — Processing...")
                    photo_path = capture_photo()
                    if not photo_path:
                        previous_distance = distance
                        continue

                    cropped, yolo_conf = detect_and_crop_license_plate(photo_path)
                    if cropped is not None:
                        plate_text, ocr_conf = ocr_license_plate(cropped)
                        confidence = round((yolo_conf + ocr_conf) / 2, 3)

                        if plate_text:
                            result = verify_scanned_plate(plate_text, confidence)
                            if result['match_found']:
                                os.remove(photo_path)
                                logger.info(f"AUTHORIZED: {result['student_info']['name']} — {plate_text}")
                                print(f"   AUTHORIZED: {result['student_info']['name']}")
                            else:
                                flagged = FLAGGED_DIR / Path(photo_path).name
                                os.rename(photo_path, flagged)
                                logger.warning(f"UNAUTHORIZED → FLAGGED: {plate_text}")
                                print(f"   UNAUTHORIZED → FLAGGED")
                        else:
                            # Save the cropped license-plate image into FLAGGED instead of moving the full photo
                            flagged_name = f"{Path(photo_path).stem}_cropped.jpg"
                            flagged = FLAGGED_DIR / flagged_name
                            try:
                                cv2.imwrite(str(flagged), cropped)
                                # remove the original full photo to avoid duplicates
                                os.remove(photo_path)
                                logger.warning(f"No text recognized → FLAGGED (cropped saved: {flagged.name})")
                                print("   No plate text → FLAGGED (cropped saved)")
                            except Exception as e:
                                # Fallback: move full photo if saving crop fails
                                flagged_full = FLAGGED_DIR / Path(photo_path).name
                                os.rename(photo_pasth, flagged_full)
                                logger.error(f"Failed to save cropped image: {e} — moved full photo to FLAGGED")
                                print("   No plate text → FLAGGED (full photo moved)")
                    else:
                        flagged = FLAGGED_DIR / Path(photo_path).name
                        os.rename(photo_path, flagged)
                        logger.warning("No plate detected → FLAGGED")
                        print("   No plate detected → FLAGGED")

                    time.sleep(4)  # Prevent rapid re-trigger

                previous_distance = distance

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
    finally:
        picam.stop()
        ser.close()
        logger.info("System stopped")

if __name__ == "__main__":
    main()