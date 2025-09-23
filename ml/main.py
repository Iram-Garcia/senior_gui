import cv2
from ultralytics import YOLO
import easyocr
import time
import os
import shutil
import picamera
import serial

# Load YOLO model
model = YOLO('LP-detection.pt')
reader = easyocr.Reader(['en'])


def process_images_folder():
    # Create captured images folder if it doesn't exist
    captured_folder = "captured_images"
    os.makedirs(captured_folder, exist_ok=True)
    
    # Generate timestamped filename
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
    img_filename = f"{timestamp}_captured.jpg"
    img_path = os.path.join(captured_folder, img_filename)
    
    # Capture image using PiCamera
    with picamera.PiCamera() as camera:
        camera.resolution = (640, 480)
        camera.capture(img_path)
    
    image_file = img_filename
    
    img = cv2.imread(img_path)
    if img is None:
        print(f"Could not load captured image at {img_path}")
        return

    start_time = time.time()
    img = cv2.resize(img, (640, 480))
    results = model(img)

    text = "No plate detected"
    confidence = 0.0
    if len(results[0].boxes) > 0:
        # Crop first plate
        boxes = results[0].boxes.xyxy[0]
        x1, y1, x2, y2 = map(int, boxes)
        license_plate_img = img[y1:y2, x1:x2]

        if license_plate_img.size > 0:
            license_plate_img = cv2.convertScaleAbs(license_plate_img, alpha=1.3, beta=0)

            result = reader.readtext(license_plate_img, detail=1)
            if result:
                text = result[0][1]  # Extract text
                confidence = result[0][2]  # Extract confidence

    end_time = time.time()
    execution_time = end_time - start_time

    # Save log
    timestamp_log = time.strftime("%Y-%m-%d %H:%M:%S")
    with open("../interface/license_plate_results.txt", "a") as file:
        file.write(f"Image: {image_file}, Timestamp: {timestamp_log}, Execution Time: {execution_time:.2f}s, Text: {text}, Confidence: {confidence:.2f}\n")
    print(f"Confidence for {image_file}: {confidence:.2f}")

    # If confidence is below 50%, save the image for verification
    if confidence < 0.5:
        verification_folder = "../interface/need_verification"
        os.makedirs(verification_folder, exist_ok=True)
        timestamp_filename = timestamp_log.replace(":", "_") + "_" + image_file
        shutil.copy(img_path, os.path.join(verification_folder, timestamp_filename))

if __name__ == "__main__":
    # Set up serial connection (adjust port and baud as needed)
    ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
    while True:
        if ser.in_waiting > 0:
            data = ser.readline().decode('utf-8').strip()
            try:
                value = float(data)
                if value < 5.0:
                    process_images_folder()
            except ValueError:
                pass  # Ignore non-numeric inputs

