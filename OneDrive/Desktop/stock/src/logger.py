import logging

# Configure logger to save to a file and show in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("NiftyScanner")