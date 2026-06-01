import os
from pathlib import Path
import glob
import pandas as pd
import numpy as np
import logging
import numpy as np
import re
from datetime import datetime
from matplotlib import pyplot as plt
import yaml
from typing import List


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


def get_word_count(file):
    try:
        tscript = pd.read_csv(file, sep='\t', header=None, names=['Nxpr', 'Channel', 'Type', 'Phrase', 'StartCS', 'EndCS', 'Score'])
    except:
        return 0
    return len(tscript[tscript['Type']=='T']['Phrase'])
    

def word_stats_by_label(datasets: list, file_col: str, label_col: str, save_path: str):
    """
    This function generates the statistics of the number of unigrams per transcript. The statistics are calculated per label per dataset.
    This was previously called word_stats.

    The datasets input should be a list of tuples, one tuple per dataset to be evaluated. 
    The tuple should be formatted as ('dataset_name', dataset_df)
    Each dataset should have a column with the paths to the phrase reco files, and the name of this column should be passed in as file_col
    Each dataset should have a column with the model label, and the name of this column should be passed in as label_col
    """
    logger.info('Calculating word stats by label.')
    word_cnt_analysis_list = []
    for dset_tup in datasets:
        dataset_name = dset_tup[0]
        dataset = dset_tup[1]
        dataset['word_cnt'] = dataset[file_col].apply(lambda x: get_word_count(x))
        labels = dataset[label_col].unique()      
        word_cnt_analysis_list.append(pd.concat([pd.DataFrame(dataset[dataset[label_col]==label]['word_cnt'].describe()).rename(columns={'word_cnt': f'{dataset_name} {label}'}).transpose() for label in labels]))
        logger.info(f'{dataset_name} stats complete. Saving')

    word_cnt_analysis = pd.concat(word_cnt_analysis_list)
    # word_cnt_analysis.to_csv(".\\word_count_descriptive_stats.csv", sep='\t', header=True, index=True)
    return word_cnt_analysis


def word_stats(datasets: list, file_col: str, save_path: str):
    """
    This function generates the statistics of the number of unigrams per transcript. The statistics are calculated per dataset.
    This was previously callsed word_stats2.

    The datasets input should be a list of tuples, one tuple per dataset to be evaluated. 
    The tuple should be formatted as ('dataset_name', dataset_df)
    Each dataset should have a column with the paths to the phrase reco files, and the name of this column should be passed in as file_col
    """
    logger.info('Starting word stats analysis.')
    word_cnt_analysis_list = []
    for dset_tup in datasets:
        dataset_name = dset_tup[0]
        dataset = dset_tup[1]
        dataset['word_cnt'] = dataset[file_col].apply(lambda x: get_word_count(x))
        word_cnt_analysis_list.append(pd.DataFrame(dataset['word_cnt'].describe()).rename(columns={'word_cnt': f'{dataset_name}'}).transpose())
        logger.info(f'{dataset_name} stats complete. Saving')

    word_cnt_analysis = pd.concat(word_cnt_analysis_list)
    if save_path:
        word_cnt_analysis.to_csv(save_path, sep='\t', header=True, index=True)
    return word_cnt_analysis


def load_config(config_path: str) -> dict:
    """Load YAML configuration file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Dictionary with config data

    Raises:
        FileNotFoundError: Config file not found
        yaml.YAMLError: Invalid YAML syntax
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if config is None:
            config = {}
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML config: {e}")


def validate_config(config: dict) -> List[str]:
    """Validate configuration structure and file availability.

    Args:
        config: Dictionary from load_config()

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Check top-level structure
    if not config:
        errors.append("Config is empty")
        return errors

    if 'output_file' not in config or not config['output_file']:
        errors.append("Missing required field: output_file")

    if 'datasets' not in config:
        errors.append("Missing required field: datasets")
        return errors

    if not isinstance(config['datasets'], list) or len(config['datasets']) == 0:
        errors.append("datasets must be a non-empty list")
        return errors

    # Check output file parent directory exists
    if 'output_file' in config and config['output_file']:
        output_path = Path(config['output_file'])
        if not output_path.parent.exists():
            errors.append(f"Output file parent directory does not exist: {output_path.parent}")

    # Track dataset names for duplicate check
    dataset_names = []

    # Validate each dataset
    for idx, dataset in enumerate(config['datasets']):
        ds_name = dataset.get('name', f'dataset[{idx}]')

        # Check required fields
        if 'name' not in dataset or not dataset['name']:
            errors.append(f"Dataset {idx}: missing required field 'name'")
            ds_name = f'dataset[{idx}]'

        if 'manifest_csv' not in dataset or not dataset['manifest_csv']:
            errors.append(f"Dataset '{ds_name}': missing required field 'manifest_csv'")
            continue

        if 'file_col' not in dataset or not dataset['file_col']:
            errors.append(f"Dataset '{ds_name}': missing required field 'file_col'")

        # Check manifest file exists
        manifest_path = Path(dataset['manifest_csv'])
        if not manifest_path.exists():
            errors.append(f"Dataset '{ds_name}': manifest CSV not found: {dataset['manifest_csv']}")
            continue

        # Try to load manifest and check columns
        try:
            manifest_df = pd.read_csv(manifest_path)

            # Check file_col exists
            file_col = dataset.get('file_col')
            if file_col and file_col not in manifest_df.columns:
                errors.append(f"Dataset '{ds_name}': column '{file_col}' not found in manifest CSV")

            # Check group_by_lob column if specified
            if 'group_by_lob' in dataset and dataset['group_by_lob']:
                if dataset['group_by_lob'] not in manifest_df.columns:
                    errors.append(f"Dataset '{ds_name}': group_by_lob column '{dataset['group_by_lob']}' not found in manifest CSV")

            # Check group_by_dataset column if specified
            if 'group_by_dataset' in dataset and dataset['group_by_dataset']:
                if dataset['group_by_dataset'] not in manifest_df.columns:
                    errors.append(f"Dataset '{ds_name}': group_by_dataset column '{dataset['group_by_dataset']}' not found in manifest CSV")

            # Check manifest has data rows
            if len(manifest_df) == 0:
                errors.append(f"Dataset '{ds_name}': manifest CSV has no data rows")

        except Exception as e:
            errors.append(f"Dataset '{ds_name}': failed to load manifest CSV: {e}")

        # Track name for duplicate check
        if 'name' in dataset:
            dataset_names.append(dataset['name'])

    # Check for duplicate names
    seen_names = set()
    for name in dataset_names:
        if name in seen_names:
            errors.append(f"Duplicate dataset name: '{name}'")
        seen_names.add(name)

    return errors


def run_from_config(config: dict) -> None:
    """Execute word statistics analysis from validated config.

    Args:
        config: Validated configuration dictionary

    Note: Config must be validated before calling this function.
    """
    all_stats = []
    output_file = config['output_file']

    logger.info("Starting word statistics analysis from config")

    for dataset in config['datasets']:
        ds_name = dataset['name']
        manifest_csv = dataset['manifest_csv']
        file_col = dataset['file_col']
        group_by_lob = dataset.get('group_by_lob')
        group_by_dataset = dataset.get('group_by_dataset')

        try:
            # Load manifest
            manifest_df = pd.read_csv(manifest_csv)
            logger.info(f"Processing dataset: {ds_name} ({len(manifest_df)} files in manifest)")

            # Case 1: No grouping
            if not group_by_lob and not group_by_dataset:
                logger.info("No grouping specified - creating single combined output")
                result = word_stats([(ds_name, manifest_df)], file_col, None)
                all_stats.append(result)

            # Case 2: LOB grouping only
            elif group_by_lob and not group_by_dataset:
                lob_values = sorted(manifest_df[group_by_lob].unique())
                logger.info(f"Grouping by LOB: {len(lob_values)} groups: {lob_values}")
                for lob_value in lob_values:
                    df_lob = manifest_df[manifest_df[group_by_lob] == lob_value]
                    row_name = f"{ds_name}_{lob_value}"
                    logger.info(f"Processing {row_name} ({len(df_lob)} files)")
                    result = word_stats([(row_name, df_lob)], file_col, None)
                    all_stats.append(result)

            # Case 3: Dataset grouping only
            elif not group_by_lob and group_by_dataset:
                dataset_values = sorted(manifest_df[group_by_dataset].unique())
                logger.info(f"Grouping by dataset: {len(dataset_values)} groups: {dataset_values}")
                for dataset_value in dataset_values:
                    df_dataset = manifest_df[manifest_df[group_by_dataset] == dataset_value]
                    row_name = f"{ds_name}_{dataset_value}"
                    logger.info(f"Processing {row_name} ({len(df_dataset)} files)")
                    result = word_stats([(row_name, df_dataset)], file_col, None)
                    all_stats.append(result)

            # Case 4: Both LOB and Dataset grouping
            else:
                dataset_values = sorted(manifest_df[group_by_dataset].unique())
                logger.info("Grouping by both LOB and dataset")
                logger.info(f"Found {len(dataset_values)} dataset values: {dataset_values}")

                for dataset_value in dataset_values:
                    df_dataset = manifest_df[manifest_df[group_by_dataset] == dataset_value]
                    logger.info(f"Processing {ds_name}_{dataset_value} ({len(df_dataset)} files)")

                    # Create combined for this dataset
                    combined_name = f"{ds_name}_{dataset_value}_combined"
                    logger.info(f"Creating {combined_name}")
                    result = word_stats([(combined_name, df_dataset)], file_col, None)
                    all_stats.append(result)

                    # Create individual LOB splits within this dataset
                    lob_values = sorted(df_dataset[group_by_lob].unique())
                    logger.info(f"Found {len(lob_values)} LOB values: {lob_values}")
                    for lob_value in lob_values:
                        df_lob = df_dataset[df_dataset[group_by_lob] == lob_value]
                        row_name = f"{ds_name}_{dataset_value}_{lob_value}"
                        logger.info(f"Creating {row_name} ({len(df_lob)} files)")
                        result = word_stats([(row_name, df_lob)], file_col, None)
                        all_stats.append(result)

        except Exception as e:
            logger.error(f"Failed to process dataset '{ds_name}': {e}")
            continue

    # Concatenate all results and save
    if all_stats:
        final_stats = pd.concat(all_stats)
        final_stats.to_csv(output_file, sep='\t', header=True, index=True)
        logger.info(f"Analysis complete: processed {len(config['datasets'])} datasets, created {len(final_stats)} output rows")
        logger.info(f"Saved to {output_file}")
    else:
        logger.error("No statistics generated - all datasets failed")


if __name__ == "__main__":
    # Example use:
    prs = glob.glob(".\\Media\\Telco\\PhraseReco\\*.zip")
    prs_dev = prs[0:10]
    prs_itv = prs[10::]
    print(len(prs_dev), len(prs_itv ))

    datasets = [('DEV', pd.DataFrame({'File': prs_dev})), ('ITV', pd.DataFrame({'File': prs_itv}))]

    # caars_janjun25_pr = pd.DataFrame({'File': glob.glob(r'S:\Nicetech\ForResearch\005_CAARS_Validations\PhraseRecos\CAARS_JanJun25\*.zip')})
    # caars_janjun25_pr['InteractionID'] = caars_janjun25_pr.File.str.split('\\').str[-1].str.split('_').str[1].astype(str)
    # caars_janjun25_pr.head()

    # caars_janjun25_pr_lob = [('Combined', caars_janjun25_pr)]
    # for lob in caars_janjun25_labels.LOB.unique():
    #     lob_ints = caars_janjun25_labels[caars_janjun25_labels.LOB==lob]['Interaction ID (NICE)']
        # caars_janjun25_pr_lob.append((f'CAARS_JanJun25_{lob}', caars_janjun25_pr[caars_janjun25_pr.InteractionID.isin(lob_ints)]))
    word_stats_save_p = '.\\outputs\\word_stats_test.csv'
    caars_janjun25_word_stats = word_stats(datasets, 'File', word_stats_save_p)


