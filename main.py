#!/usr/bin/env python3
"""
Raspberry Pi Display System
Main entry point for the display application
"""
import sys
import time
import logging
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from image import image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/display/logs/display.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    """Main application loop"""
    try:
        # Create logs directory if it doesn't exist
        Path('/opt/display/logs').mkdir(exist_ok=True)
        
        logging.info("Starting display application")
        img_display = image()  # Use original class name
        
        while True:
            img_display.HMI1()
            time.sleep(1)  # Refresh every second
            
    except KeyboardInterrupt:
        logging.info("Application stopped by user")
    except Exception as e:
        logging.error(f"Application error: {e}")
    finally:
        logging.info("Cleaning up and exiting")
        if 'img_display' in locals():
            img_display.disp.module_exit()

if __name__ == "__main__":
    main()