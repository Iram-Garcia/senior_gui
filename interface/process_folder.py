"""Process images placed into a folder through the ML pipeline for testing.

Usage examples:
  # Process all existing images once
  python process_folder.py --folder test_images --mode once

  # Watch folder and process new images as they appear
  python process_folder.py --folder test_images --mode watch --interval 2

Processed images with low confidence are kept in `interface/need_verification` by the ML pipeline.
This script will optionally move originals to a `processed/` or `failed/` subfolder after processing.
"""

import os
import time
import shutil
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPPORTED_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff'}


def process_folder(folder: str, mode: str = 'once', interval: float = 1.0, move_processed: bool = True):
    folder_path = Path(folder)
    if not folder_path.exists():
        logger.info(f"Creating folder {folder}")
        folder_path.mkdir(parents=True, exist_ok=True)

    # Ensure ML processor is instantiated
    try:
        from ml_processor import processor
    except Exception as e:
        logger.error(f"Failed to import ML processor: {e}")
        return

    processed_dir = folder_path / 'processed'
    failed_dir = folder_path / 'failed'
    processed_dir.mkdir(exist_ok=True)
    failed_dir.mkdir(exist_ok=True)

    def scan_and_process():
        for p in folder_path.iterdir():
            if p.is_dir():
                continue
            if p.suffix.lower() not in SUPPORTED_EXTS:
                continue
            try:
                logger.info(f"Processing {p}")
                result = processor.process_image_file(str(p), image_file_name=p.name)
                logger.info(f"Result: text={result.get('text')}, confidence={result.get('confidence')}")
                # If original still exists and user wants files moved, move them
                try:
                    if move_processed and p.exists():
                        dest = processed_dir / p.name
                        shutil.move(str(p), str(dest))
                except Exception as e:
                    logger.warning(f"Could not move processed file {p}: {e}")
            except Exception as e:
                logger.error(f"Failed processing {p}: {e}")
                try:
                    dest = failed_dir / p.name
                    shutil.move(str(p), str(dest))
                except Exception:
                    pass

    if mode == 'once':
        scan_and_process()
        logger.info("Completed one-shot processing")
    else:
        logger.info(f"Watching {folder} for new images (interval={interval}s)")
        try:
            while True:
                scan_and_process()
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Watcher stopped by user")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Process images in a folder through the ML pipeline')
    parser.add_argument('--folder', default='test_images', help='Folder to watch / process')
    parser.add_argument('--mode', choices=['once', 'watch'], default='once', help='Process once or watch continuously')
    parser.add_argument('--interval', type=float, default=1.0, help='Polling interval for watch mode (seconds)')
    parser.add_argument('--no-move', dest='move', action='store_false', help='Do not move processed originals to processed/ folder')
    args = parser.parse_args()

    process_folder(args.folder, mode=args.mode, interval=args.interval, move_processed=args.move)
