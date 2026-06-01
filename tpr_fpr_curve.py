"""TPR vs FPR plotting utilities.

This module provides a small helper to compute and plot a TPR vs FPR (ROC) curve
for model score columns against boolean match labels computed from predicted
and truth columns.

The function returns the computed false-positive rates, true-positive rates,
ROC AUC and the Matplotlib Figure for programmatic use.
"""

from pathlib import Path
import re
import logging
from typing import Optional, Tuple, Iterable

import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve
from matplotlib import pyplot as plt
import yaml


# Configure logger with shared log file
def _setup_logger(name: str = "citi_mrm_tools") -> logging.Logger:
    """Set up logger that writes to a shared log file in the root."""
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # Shared log file in workspace root
        log_file = Path(__file__).parent / "citi_mrm_tools.log"
        file_handler = logging.FileHandler(log_file, mode='a')
        formatter = logging.Formatter('%(asctime)s | %(name)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


logger = _setup_logger()


def _sanitize_filename(name: str) -> str:
    """Make a filesystem-safe filename fragment from `name`."""
    return re.sub(r"[^0-9A-Za-z._-]", "_", str(name))


def load_config(config_path: str) -> dict:
    """
    Load YAML configuration file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Dictionary with config contents

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML config: {e}")


def recall_vs_fpr_curve(
    df: pd.DataFrame,
    pred_col: str,
    truth_col: str,
    score_col: str,
    dataset_name: str = None,
    save_dir: str = None
):
    """
    Compute and plot the ROC curve (TPR vs FPR) using the model score column.

    Args:
      df: DataFrame containing prediction, truth and score columns.
      pred_col: Column name with the predicted class (or label).
      truth_col: Column name with the true class (or label).
      score_col: Column name with the model score for the positive class.
      dataset_name: Optional label used in the plot title and saved filename.
      save_dir: Optional directory path to save the plotted image.
      show: If True, call `plt.show()`; otherwise return the Figure object.

    Returns:
      fpr, tpr, auc, fig
    """
    if df is None or df.empty:
        raise ValueError("`df` is empty or None")

    if dataset_name is None:
        dataset_name = "dataset"

    # Compute boolean match (1 for correct prediction, 0 for incorrect)
    match = (df[pred_col] == df[truth_col]).astype(int)

    # Ensure the score column is numeric
    scores = pd.to_numeric(df[score_col], errors="coerce").fillna(0.0)

    # Handle degenerate cases for ROC/AUC
    if match.nunique() == 1:
        logger.warning("All labels identical in `match`. ROC AUC is undefined.")
        auc_val = float('nan')
        fpr = np.array([0.0, 1.0])
        tpr = np.array([0.0, 1.0])
    else:
        auc_val = float(roc_auc_score(match, scores))
        fpr, tpr, _ = roc_curve(match, scores)

    logger.info('Plotting TPR v FPR')
    fig, ax = plt.subplots()
    ax.plot(fpr, tpr, label=f'{dataset_name} AUC = {auc_val:.4f}')
    ax.plot([0, 1], [0, 1], color='k', linestyle='--', linewidth=0.6)
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title(f'{dataset_name} - TPR vs FPR')
    ax.legend(loc='best')
    fig.tight_layout()

    if save_dir:
        logger.info('Saving ROC plot')
        p = Path(save_dir)
        p.mkdir(parents=True, exist_ok=True)
        safe_name = _sanitize_filename(dataset_name)
        out = p / f'tpr_v_fpr_{safe_name}.png'
        fig.savefig(out, dpi=150)
        logger.info('Saved ROC plot to %s', out)
    else:
        out = None

    # Log the run
    auc_str = f"{auc_val:.6f}" if not np.isnan(auc_val) else "NaN"
    logger.info('dataset=%s | rows=%d | auc=%s', dataset_name, len(df), auc_str)


if __name__ == "__main__":
    # Example use
    try:
        example_path = r'.\dummy_multiclass_predictions.csv'
        df = pd.read_csv(example_path)
        logger.info('Loaded example data from %s', example_path)
        # Ensure Interaction ID is string if present
        if 'InteractionID' in df.columns:
            df['InteractionID'] = df['InteractionID'].astype(str)

        save_p = r'.\test_tpr_fpr'
        recall_vs_fpr_curve(
            df,
            pred_col='ModelPrediction',
            truth_col='TrueValue',
            score_col='PredictionScore',
            dataset_name='Test',
            save_dir=save_p
        )
    except FileNotFoundError:
        logger.error('Example CSV not found; update the example path or use the function programmatically.')
