"""TPR vs FPR plotting utilities.

This module provides a small helper to compute and plot a TPR vs FPR (ROC) curve
for model score columns against boolean match labels computed from predicted
and truth columns.

The function returns the computed false-positive rates, true-positive rates,
ROC AUC and the Matplotlib Figure for programmatic use.
"""

from pathlib import Path
import os
import re
import logging
from typing import Optional, Tuple, Iterable, List

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


def validate_config(config: dict) -> List[str]:
    """
    Validate configuration structure and data availability.

    Args:
        config: Configuration dictionary from YAML

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # 1. Top-level structure
    if not config:
        errors.append("Config is empty")
        return errors

    if 'output_dir' not in config:
        errors.append("Missing required field: output_dir")
    elif not isinstance(config['output_dir'], str) or not config['output_dir'].strip():
        errors.append("output_dir must be a non-empty string")

    if 'datasets' not in config:
        errors.append("Missing required field: datasets")
        return errors  # Can't continue without datasets

    if not isinstance(config['datasets'], list) or len(config['datasets']) == 0:
        errors.append("datasets must be a non-empty list")
        return errors

    # 2. Per-dataset structure validation
    required_fields = ['csv_path', 'name', 'pred_col', 'truth_col', 'score_col']
    dataset_names = []
    potential_names = set()  # Track all possible output names for collision detection

    for i, dataset in enumerate(config['datasets']):
        if not isinstance(dataset, dict):
            errors.append(f"Dataset {i}: must be a dictionary")
            continue

        ds_name = dataset.get('name', f'dataset_{i}')

        # Check required fields
        for field in required_fields:
            if field not in dataset:
                errors.append(f"Dataset '{ds_name}': missing required field '{field}'")
            elif not isinstance(dataset[field], str) or not dataset[field].strip():
                errors.append(f"Dataset '{ds_name}': field '{field}' must be a non-empty string")

        # Check optional group_by field
        if 'group_by' in dataset:
            if not isinstance(dataset['group_by'], str) or not dataset['group_by'].strip():
                errors.append(f"Dataset '{ds_name}': field 'group_by' must be a non-empty string if present")

        # Track dataset names for duplicate check
        dataset_names.append(ds_name)

    # Check for duplicate names
    seen_names = set()
    for name in dataset_names:
        if name in seen_names:
            errors.append(f"Duplicate dataset name: '{name}'")
        seen_names.add(name)

    # If structural validation failed, don't proceed to file checks
    if errors:
        return errors

    # 3. File system checks
    output_dir = config['output_dir']
    output_parent = os.path.dirname(os.path.abspath(output_dir))
    if output_parent and not os.path.exists(output_parent):
        errors.append(f"Output directory parent does not exist: {output_parent}")

    # 4. CSV content checks
    for dataset in config['datasets']:
        ds_name = dataset['name']
        csv_path = dataset['csv_path']

        # Check file exists
        if not os.path.exists(csv_path):
            errors.append(f"Dataset '{ds_name}': CSV file not found: {csv_path}")
            continue

        # Try to load CSV and check columns
        try:
            df = pd.read_csv(csv_path)

            if len(df) == 0:
                errors.append(f"Dataset '{ds_name}': CSV file is empty (no data rows)")

            # Check required columns exist
            for col_key in ['pred_col', 'truth_col', 'score_col']:
                col_name = dataset[col_key]
                if col_name not in df.columns:
                    available = ', '.join(df.columns[:5])
                    errors.append(
                        f"Dataset '{ds_name}': column '{col_name}' not found in CSV. "
                        f"Available columns: {available}..."
                    )

            # Check group_by column if specified
            if 'group_by' in dataset:
                group_col = dataset['group_by']
                if group_col not in df.columns:
                    errors.append(f"Dataset '{ds_name}': group_by column '{group_col}' not found in CSV")
                else:
                    # Collect potential output names for collision detection
                    group_values = df[group_col].unique()
                    for val in group_values:
                        potential_name = f"{ds_name}_{val}"
                        if potential_name in potential_names or potential_name in dataset_names:
                            errors.append(
                                f"Name collision detected: '{potential_name}' "
                                f"(from stratification conflicts with existing name)"
                            )
                        potential_names.add(potential_name)
            else:
                potential_names.add(ds_name)

        except Exception as e:
            errors.append(f"Dataset '{ds_name}': failed to load CSV: {e}")

    return errors


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
