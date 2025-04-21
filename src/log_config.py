import logging
import os

def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s (%(name)s) [%(levelname)s]: %(message)s")
    if os.getenv("HEROKU"):
        logging.getLogger().addHandler(logging.StreamHandler())
