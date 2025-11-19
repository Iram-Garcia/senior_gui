import os
import time
import threading
#import serial
# Defer/import heavy ML dependencies with clear error messages if missing
try:
    import cv2
    from ultralytics import YOLO
    import easyocr
    _ML_DEPS_MISSING = False
except Exception as _e:
    cv2 = None
    YOLO = None
    easyocr = None
    _ML_DEPS_MISSING = True
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

# Keep captured images only when confidence < this threshold
CONFIDENCE_SAVE_THRESHOLD = 0.5

# Singleton class for ML processing and serial communication
class MLProcessor:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MLProcessor, cls).__new__(cls)
            # Ensure ML deps are available
            if _ML_DEPS_MISSING:
                raise RuntimeError(
                    "Missing ML dependencies (cv2/ultralytics/easyocr). "
                    "Install required packages in your environment, for example:\n"
                    "pip install opencv-python-headless ultralytics easyocr\n"
                    "Also ensure the model file 'LP-detection.pt' exists in the interface/ folder."
                )

            # Load YOLO model from the interface folder explicitly
            model_path = os.path.join(INTERFACE_DIR, 'LP-detection.pt')
            if not os.path.exists(model_path):
                raise RuntimeError(f"YOLO model not found at {model_path}")

            cls._instance.yolo_model = YOLO(model_path)
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
        # Delegate processing of the captured file to the new helper
        self.process_image_file(temp_img_path, image_file_name=image_file)

    def stop_serial(self):
        """Close serial connection."""
        if self.serial:
            self.serial.close()
            self.serial = None
            logger.info("Serial connection closed")

    def process_image_file(self, image_path: str, image_file_name: str = None):
        """Process an existing image file with YOLO + OCR.

        Parameters:
        - image_path: path to the image file to process
        - image_file_name: optional label/name used in logs
        """
        if image_file_name is None:
            image_file_name = os.path.basename(image_path)

        start_time = time.time()
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Could not load image at {image_path}")
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
                try:
                    result = self.ocr_reader.readtext(license_plate_img, detail=1)
                    if result:
                        text = result[0][1]  # Extract text
                        confidence = result[0][2]  # Extract confidence
                except Exception as e:
                    logger.error(f"OCR error: {e}")

        end_time = time.time()
        execution_time = end_time - start_time

        # Save log
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(LOG_FILE, "a") as file:
                file.write(f"Image: {image_file_name}, Timestamp: {timestamp}, Execution Time: {execution_time:.2f}s, Text: {text}, Confidence: {confidence:.2f}\n")
        except Exception as e:
            logger.error(f"Failed to write log: {e}")
        logger.info(f"Processed {image_file_name}: Confidence = {confidence:.2f}, Text = {text}")

        # Save image for verification and keep files only when confidence < threshold
        timestamp_filename = timestamp.replace(":", "_") + "_" + image_file_name
        output_filename = f"processed_{timestamp.replace(':', '_')}_{image_file_name}"
        output_path = os.path.join(VERIFICATION_FOLDER, output_filename)

        saved_capture = None
        saved_processed = None
        deleted_original = False

        if confidence < CONFIDENCE_SAVE_THRESHOLD:
            # copy original capture for manual audit
            try:
                saved_capture = os.path.join(VERIFICATION_FOLDER, timestamp_filename)
                shutil.copy(image_path, saved_capture)
            except Exception as e:
                logger.error(f"Failed to copy for verification: {e}")
                saved_capture = None
            # save processed/annotated image as well
            try:
                cv2.imwrite(output_path, img)
                saved_processed = output_path
                self.latest_processed = output_path
            except Exception as e:
                logger.error(f"Failed to save processed image: {e}")
                saved_processed = None
        else:
            # high-confidence result: remove the captured file to conserve storage
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)
                    deleted_original = True
            except Exception as e:
                logger.debug(f"Could not remove capture {image_path}: {e}")

        # Return a summary dict so callers can make decisions (e.g., move/delete files)
        return {
            'image_file_name': image_file_name,
            'text': text,
            'confidence': float(confidence),
            'execution_time_s': execution_time,
            'saved_capture': saved_capture,
            'saved_processed': saved_processed,
            'deleted_original': deleted_original,
        }

# Global processor instance
processor = MLProcessor()

# Start serial watcher (called by Streamlit app)
def start_background_processor():
    thread = processor.start_serial_watcher()
    return thread