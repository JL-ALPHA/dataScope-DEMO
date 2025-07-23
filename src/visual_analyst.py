# src/visual_analyst.py

import matplotlib.pyplot as plt
import seaborn as sns
import logging

logger = logging.getLogger(__name__)

def show_null_heatmap(df):
    if df is not None:
        plt.figure(figsize=(10, 6))
        sns.heatmap(df.isnull(), cbar=False)
        plt.title("Null Value Heatmap")
        plt.tight_layout()
        plt.show()
        logger.info("Displayed heatmap.")
    else:
        logger.warning("No data to visualize.")
