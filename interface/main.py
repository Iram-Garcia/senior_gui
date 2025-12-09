# main.py → Laptop Testing Version (NO camera, NO picamera2, NO opencv)
import serial
import time
import logging
import os
import json # Import json globally as it's used in the new function signature
from datetime import datetime
from pathlib import Path

# Local imports (your existing files)
from ml_utils import load_models, detect_and_crop_license_plate, ocr_license_plate
from student_db import verify_scanned_plate, init_student_db

logging.basicConfig(
  level=logging.INFO,
  format='%(asctime)s | %(levelname)s | %(message)s',
  handlers=[
    logging.FileHandler("security_system.log"),
    logging.StreamHandler()
  ]
)
logger = logging.getLogger(__name__)

# ================= CONFIGURATION =================
SERIAL_PORT = "COM7"       # Change to your ESP32 COM port
BAUD_RATE = 9600

PHOTO_DIR = Path("photos")
FLAGGED_DIR = Path("FLAGGED")
PHOTO_DIR.mkdir(exist_ok=True)
FLAGGED_DIR.mkdir(exist_ok=True)

# Test image to use when trigger happens (drop any car photo here!)
TEST_IMAGE_PATH = PHOTO_DIR / "test_car.jpg"  # ← Put a sample photo with visible plate here

previous_distance = None

# Shared sensor data for Streamlit
def save_latest_sensor_data(temp: float, battery: float, distance: float): # <-- FIX 1: Added distance parameter
  data = {
    "temperature": temp,
    "battery": battery,
    "distance": distance, # <-- FIX 2: Added distance key
    "last_update": datetime.now().isoformat()
  }
  # import json # Removed global import, moved to top
  with open("latest_sensor.json", "w") as f:
    json.dump(data, f)

def parse_serial_line(line: str):
  try:
    # NOTE: The parsing assumes data is comma-separated floats, 
    # but your print statement shows it separated by pipe (|) and key names (Distance:, Temp:, Battery:).
    # The existing parsing logic is slightly flawed but works by stripping keys/units.
    parts = line.strip().replace("Distance:", "").replace("Temperature:", "").replace("Battery:", "").split(",")
    if len(parts) != 3:
      return None, None, None
    # The app.py side handles the 'cm' and '%' units, but stripping them here 
        # simplifies the app.py regex slightly (though the current app.py handles it fine).
    distance = float(parts[0].strip().replace("cm", "")) 
    temp = float(parts[1].strip().replace("°F", ""))
    battery = float(parts[2].strip().replace("%", ""))
    return distance, temp, battery
  except:
    return None, None, None

def fake_capture_photo() -> str:
  """Instead of taking a photo → just pretend and use test image"""
  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
  fake_path = PHOTO_DIR / f"FAKE_{timestamp}.jpg"

  # Copy the test image so the rest of the pipeline works normally
  if TEST_IMAGE_PATH.exists():
    import shutil
    shutil.copy(TEST_IMAGE_PATH, fake_path)
    print("Picture taken! (using test image)")
    logger.info(f"FAKE photo created: {fake_path.name}")
    return str(fake_path)
  else:
    # Fallback: create a blank image so ML doesn't crash
    import cv2
    import numpy as np
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(blank, "NO TEST IMAGE", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
    cv2.imwrite(str(fake_path), blank)
    print("Picture taken! (blank test image - drop a real photo as photos/test_car.jpg)")
    return str(fake_path)

def main():
  global previous_distance

  logger.info("=== LAPTOP TESTING MODE ===")
  logger.info("No camera → Using fake_capture_photo()")
  init_student_db()
  load_models()

  try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    logger.info(f"Connected to {SERIAL_PORT}")
  except Exception as e:
    logger.error(f"Cannot open serial port: {e}")
    logger.error("Make sure ESP32 is connected and COM port is correct!")
    return

  print("\nSystem ready! Waiting for ESP32 data...\n")
  print("Tip: Drop a clear photo of a car + license plate into photos/test_car.jpg for best testing!\n")

  while True:
    try:
      if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if "Distance:" in line:
          distance, temp, battery = parse_serial_line(line)
          if distance is None:
            continue

          print(f"Distance: {distance:.1f}cm | Temp: {temp}°F | Battery: {battery}%")
          save_latest_sensor_data(temp, battery, distance) # <-- FIX 3: Passed distance

          # Trigger when distance drops to ~half
          if previous_distance and distance <= previous_distance / 2 + 5:
            print("\nTRIGGERED! Vehicle detected close enough!\n")
            photo_path = fake_capture_photo()

            # Run ML pipeline
            cropped, yolo_conf = detect_and_crop_license_plate(photo_path)
            if cropped is not None:
              plate_text, ocr_conf = ocr_license_plate(cropped)
              overall_conf = (yolo_conf + ocr_conf) / 2

              if plate_text:
                result = verify_scanned_plate(plate_text, overall_conf)
                if result['match_found']:
                  os.remove(photo_path)
                  print(f"AUTHORIZED → {result['student_info']['name']} ({plate_text})\n")
                else:
                  flagged = FLAGGED_DIR / Path(photo_path).name
                  os.rename(photo_path, flagged)
                  print(f"UNAUTHORIZED → FLAGGED: {plate_text}\n")
              else:
                flagged = FLAGGED_DIR / Path(photo_path).name
                os.rename(photo_path, flagged)
                print("No plate text → FLAGGED\n")
            else:
              flagged = FLAGGED_DIR / Path(photo_path).name
              os.rename(photo_path, flagged)
              print("No plate detected → FLAGGED\n")

            time.sleep(4) # Avoid double-trigger

          previous_distance = distance

      time.sleep(0.05)

    except KeyboardInterrupt:
      print("\nShutting down...")
      break
    except Exception as e:
      logger.error(f"Error: {e}")
      time.sleep(1)

  ser.close()

if __name__ == "__main__":
  main()