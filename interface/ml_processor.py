import os
import time
import threading
#import serial
import cv2
from ultralytics import YOLO
import easyocr
#import picamera
import shutil
import logging

# Setup logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Folder paths (relative to project root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERFACE_DIR = os.path.join(BASE_DIR, 'interface')
LOG_FILE = os.path.join(INTERFACE_DIR, 'license_plate_results.txt')
VERIFICATION_FOLDER = os.path.join(INTERFACE_DIR, 'need_verification')
os.makedirs(INTERFACE_DIR, exist_ok=True)
os.makedirs(VERIFICATION_FOLDER, exist_ok=True)

# Singleton class for ML processing and serial communication
class MLProcessor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MLProcessor, cls).__new__(cls)
            cls._instance.yolo_model = YOLO('LP-detection.pt')  # Adjust path if needed
            cls._instance.ocr_reader = easyocr.Reader(['en'])
            cls._instance.latest_processed = None  # Store latest processed image path
            cls._instance.serial = None
            cls._instance.serial_thread = None
        return cls._instance

    def start_serial_watcher(self, port='/dev/ttyUSB0', baudrate=115200):
        """Start serial port monitoring in a background thread."""
        if self.serial is None:
            try:
                self.serial = serial.Serial(port, baudrate, timeout=1)
                logger.info(f"Connected to serial port {port} at {baudrate} baud")
                self.serial_thread = threading.Thread(target=self._serial_loop, daemon=True)
                self.serial_thread.start()
            except serial.SerialException as e:
                logger.error(f"Failed to open serial port {port}: {e}")
                raise

    def _serial_loop(self):
        """Read serial data and trigger processing when distance < 5.0."""
        while True:
            try:
                if self.serial.in_waiting > 0:
                    data = self.serial.readline().decode('utf-8').strip()
                    try:
                        distance = float(data)
                        logger.info(f"Received distance: {distance} inches")
                        if distance < 5.0 and distance >= 0:
                            self.process_image()
                    except ValueError:
                        logger.warning(f"Ignoring non-numeric serial data: {data}")
            except serial.SerialException as e:
                logger.error(f"Serial error: {e}")
                time.sleep(1)  # Retry after delay
            except Exception as e:
                logger.error(f"Unexpected error in serial loop: {e}")
            time.sleep(0.1)  # Prevent CPU overload

    def process_image(self):
        """Capture and process an image with PiCamera, YOLO, and OCR."""
        temp_img_path = os.path.join(BASE_DIR, 'temp.jpg')
        image_file = "captured_image.jpg"  # Fixed name for logging

        # Capture image using PiCamera
        try:
            with picamera.PiCamera() as camera:
                camera.resolution = (640, 480)
                camera.capture(temp_img_path)
        except Exception as e:
            logger.error(f"PiCamera error: {e}")
            return

        # Process image
        start_time = time.time()
        img = cv2.imread(temp_img_path)
        if img is None:
            logger.error(f"Could not load captured image at {temp_img_path}")
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)
            return

        img = cv2.resize(img, (640, 480))
        results = self.yolo_model(img)

        text = "No plate detected"
        confidence = 0.0
        if len(results[0].boxes) > 0:
            # Crop first plate
            boxes = results[0].boxes.xyxy[0]
            x1, y1, x2, y2 = map(int, boxes)
            license_plate_img = img[y1:y2, x1:x2]

            if license_plate_img.size > 0:
                license_plate_img = cv2.convertScaleAbs(license_plate_img, alpha=1.3, beta=0)
                result = self.ocr_reader.readtext(license_plate_img, detail=1)
                if result:
                    text = result[0][1]  # Extract text
                    confidence = result[0][2]  # Extract confidence

        end_time = time.time()
        execution_time = end_time - start_time

        # Save log
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a") as file:
            file.write(f"Image: {image_file}, Timestamp: {timestamp}, Execution Time: {execution_time:.2f}s, Text: {text}, Confidence: {confidence:.2f}\n")
        logger.info(f"Processed {image_file}: Confidence = {confidence:.2f}, Text = {text}")

        # Save image for verification if confidence < 0.5
        if confidence < 0.5:
            timestamp_filename = timestamp.replace(":", "_") + "_" + image_file
            shutil.copy(temp_img_path, os.path.join(VERIFICATION_FOLDER, timestamp_filename))

        # Save processed image with annotations
        output_filename = f"processed_{timestamp.replace(':', '_')}_{image_file}"
        output_path = os.path.join(VERIFICATION_FOLDER, output_filename)
        cv2.imwrite(output_path, img)
        self.latest_processed = output_path

        # Clean up temporary file
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

    def stop_serial(self):
        """Close serial connection."""
        if self.serial:
            self.serial.close()
            self.serial = None
            logger.info("Serial connection closed")

# Global processor instance
processor = MLProcessor()

# Start serial watcher (called by Streamlit app)
def start_background_processor():
    thread = processor.start_serial_watcher()
    return thread