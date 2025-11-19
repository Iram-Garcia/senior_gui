import os
import re
import time
import csv
import threading
import logging
from datetime import datetime

try:
    import serial
except Exception:
    serial = None

try:
    import picamera
except Exception:
    picamera = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SerialReader:
    """Read serial lines formatted like:
    "distance: <value>, temperature: <value>, battery: <value>"

    Saves readings to a JSON file and takes a photo when the distance
    drops to half (or less) of the previous measured distance.
    """

    LINE_RE = re.compile(r"distance:\s*([0-9.+-eE]+)\s*,\s*temperature:\s*([0-9.+-eE]+)\s*,\s*battery:\s*([0-9.+-eE]+)", re.IGNORECASE)

    def __init__(self, port='/dev/ttyUSB0', baudrate=115200, readings_file=None, photo_folder=None):
        self.port = port
        self.baudrate = baudrate
        self._stop_event = threading.Event()
        self.thread = None
        self.previous_distance = None

        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Use CSV for easier management and external analysis
        self.readings_file = readings_file or os.path.join(base_dir, 'readings.csv')
        self.photo_folder = photo_folder or os.path.join(base_dir, 'captures')
        os.makedirs(self.photo_folder, exist_ok=True)

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"Started serial reader on {self.port} @ {self.baudrate}")

    def stop(self):
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Serial reader stopped")

    def _open_serial(self):
        if serial is None:
            raise RuntimeError('pyserial is not available; install pyserial')
        try:
            ser = serial.Serial(self.port, self.baudrate, timeout=1)
            return ser
        except Exception as e:
            logger.error(f"Failed to open serial port {self.port}: {e}")
            raise

    def _parse_line(self, line: str):
        m = self.LINE_RE.search(line)
        if not m:
            return None
        try:
            distance = float(m.group(1))
            temperature = float(m.group(2))
            battery = float(m.group(3))
            return {
                'distance': distance,
                'temperature': temperature,
                'battery': battery
            }
        except ValueError:
            return None

    def _save_reading(self, reading: dict):
        """Append a reading to a CSV file with header if needed."""
        fieldnames = ['timestamp', 'distance', 'temperature', 'battery']
        row = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'distance': reading['distance'],
            'temperature': reading['temperature'],
            'battery': reading['battery']
        }
        write_header = not os.path.exists(self.readings_file)
        try:
            with open(self.readings_file, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if write_header:
                    writer.writeheader()
                writer.writerow(row)
        except Exception as e:
            logger.error(f"Failed to save reading to CSV: {e}")

    def _take_photo(self):
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"capture_{timestamp}.jpg"
        path = os.path.join(self.photo_folder, filename)
        if picamera:
            try:
                with picamera.PiCamera() as camera:
                    camera.resolution = (1640, 1232)
                    time.sleep(0.2)
                    camera.capture(path)
                logger.info(f"Captured photo to {path}")
                # After successful capture, forward to ML pipeline if available
                try:
                    # Import lazily to avoid loading heavy ML models at startup
                    from ml_processor import processor as ml_processor_instance
                    try:
                        ml_processor_instance.process_image_file(path, image_file_name=filename)
                        logger.info("Forwarded captured image to ML pipeline")
                    except Exception as e:
                        logger.error(f"ML processing failed for {path}: {e}")
                except Exception as e:
                    logger.debug(f"ML pipeline not available or failed to import: {e}")
                return path
            except Exception as e:
                logger.error(f"PiCamera capture failed: {e}")
        # Fallback: create an empty file to mark capture (or use OpenCV if available)
        try:
            with open(path, 'wb') as f:
                f.write(b'')
            logger.warning(f"PiCamera not available; created empty placeholder {path}")
            # Even for placeholder files, try forwarding to ML pipeline (it will likely skip)
            try:
                from ml_processor import processor as ml_processor_instance
                try:
                    ml_processor_instance.process_image_file(path, image_file_name=filename)
                    logger.info("Forwarded placeholder image to ML pipeline")
                except Exception as e:
                    logger.error(f"ML processing failed for placeholder {path}: {e}")
            except Exception:
                pass
            return path
        except Exception as e:
            logger.error(f"Failed to write fallback capture file: {e}")
            return None

    def _run(self):
        try:
            ser = self._open_serial()
        except Exception:
            return

        with ser:
            while not self._stop_event.is_set():
                try:
                    raw = ser.readline().decode('utf-8', errors='ignore').strip()
                    if not raw:
                        time.sleep(0.05)
                        continue
                    logger.debug(f"Serial line: {raw}")
                    reading = self._parse_line(raw)
                    if reading is None:
                        logger.debug("Unrecognized serial format, skipping")
                        continue

                    # Save reading
                    self._save_reading(reading)

                    # Check distance trigger
                    d = reading['distance']
                    if self.previous_distance is not None:
                        try:
                            if d <= (self.previous_distance / 2.0):
                                logger.info(f"Distance dropped from {self.previous_distance} to {d}; taking photo")
                                self._take_photo()
                        except Exception as e:
                            logger.error(f"Error evaluating trigger: {e}")

                    self.previous_distance = d
                except Exception as e:
                    logger.error(f"Error in serial loop: {e}")
                    time.sleep(0.5)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Serial reader for distance/temperature/battery')
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port (e.g. /dev/ttyUSB0 or COM3)')
    parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
    args = parser.parse_args()

    reader = SerialReader(port=args.port, baudrate=args.baud)
    try:
        reader.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        reader.stop()
