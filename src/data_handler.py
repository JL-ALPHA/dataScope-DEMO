# src/data_handler.py

import pandas as pd
import logging

logger = logging.getLogger(__name__)

def load_data(file_path):
    logger.info(f"Loading data from: {file_path}")
    try:
        df = pd.read_csv(file_path)
        logger.info("Data loaded successfully.")
        return df
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return None
