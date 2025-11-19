"""Simple entry point to start the serial reader on the Raspberry Pi.

Run with: `python main.py --port /dev/ttyUSB0 --baud 115200` (or `COM3` on Windows)
"""

from serial_reader import SerialReader
import logging

# Eagerly load ML processor so models are ready when the first capture occurs.
try:
	# importing `processor` instantiates MLProcessor and loads YOLO/OCR.
	from ml_processor import processor as ml_processor_instance
	logging.getLogger(__name__).info("ML processor instantiated at startup")
except Exception as e:
	logging.getLogger(__name__).warning(f"ML processor could not be instantiated at startup: {e}")
import argparse
import time


def main():
	parser = argparse.ArgumentParser(description='Start serial reader')
	parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port')
	parser.add_argument('--baud', type=int, default=115200, help='Baud rate')
	args = parser.parse_args()

	reader = SerialReader(port=args.port, baudrate=args.baud)
	try:
		reader.start()
		while True:
			time.sleep(1)
	except KeyboardInterrupt:
		reader.stop()


if __name__ == '__main__':
	main()

