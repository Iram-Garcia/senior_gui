import cv2
from ultralytics import YOLO
import easyocr
import time
import os

# Load YOLO model
model = YOLO('LP-detection.pt')
reader = easyocr.Reader(['en'])


def process_images_folder():
    images_folder = "images"
    if not os.path.exists(images_folder):
        print(f"Folder '{images_folder}' does not exist.")
        return

    image_files = [f for f in os.listdir(images_folder) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    if not image_files:
        print(f"No image files found in '{images_folder}'.")
        return

    with open("../interface/license_plate_results.txt", "a") as file:
        for image_file in image_files:
            img_path = os.path.join(images_folder, image_file)
            img = cv2.imread(img_path)
            if img is None:
                print(f"Could not load image at {img_path}")
                continue

            start_time = time.time()
            img = cv2.resize(img, (640, 480))
            results = model(img)

            text = "No plate detected"
            if len(results[0].boxes) > 0:
                # Crop first plate
                boxes = results[0].boxes.xyxy[0]
                x1, y1, x2, y2 = map(int, boxes)
                license_plate_img = img[y1:y2, x1:x2]

                if license_plate_img.size > 0:
                    license_plate_img = cv2.convertScaleAbs(license_plate_img, alpha=1.3, beta=0)

                    result = reader.readtext(license_plate_img, detail=0)
                    if result:
                        text = result[0]

            end_time = time.time()
            execution_time = end_time - start_time

            # Save log
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            file.write(f"Image: {image_file}, Timestamp: {timestamp}, Execution Time: {execution_time:.2f}s, Text: {text}\n")

if __name__ == "__main__":
    process_images_folder()

