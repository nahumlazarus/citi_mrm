# import asyncio
# import multiprocessing
# from multiprocessing import Manager
import argparse
import glob
import logging
import logging.config
import os
import sys
from collections import Counter
from concurrent.futures import as_completed, ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from tqdm import tqdm
import pandas as pd
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

"""
This script generates the counts of words in a dataset. This is a requirement for the model review process.
The deliverable requires the counts of all unigrams in the development (or training) dataset. These unigrams will be the reference unigram set. 
All other datasets (e.g. in-time validation and out-of-time validation) will have the counts generated against the reference unigram set.

Functionality:
1. Build reference unigram set from dev dataset - i.e extract unique unigrams.
2. Get word counts for each dataset.

Inputs:
1. Dev dataset with interactions in phrase reco (.csv.zip) format.
2. (Optional) Additional datasets with interactions in phrase reco format.

Outputs:
1. CSV file with the reference unigrams in the first column and one column per dataset for the unigram frequencies.


Enhancements:
1. Track transcript length. Maybe useful to get a distribution of transcript lengths so that we can investigate a dataset if they all have a low number of unigrams.
"""



def get_transcript_unigrams(file_path: str) -> Iterable[str]:
    """
    Takes in a transcript in phrase reco format and extracts the unigrams.
    Returns empty list on error (logged, not raised).

    Inputs:
    1. Single transcript in phrase reco format.

    Outputs:
    1. List of unigrams from the transcript.
    """
    try:
        tscript = pd.read_csv(file_path, sep='\t', header=None, names=['Nxpr', 'Channel', 'Type', 'Phrase', 'StartCS', 'EndCS', 'Score'])
        words = list(tscript[tscript['Type']=='T']['Phrase'])
        return words
    except Exception as e:
        logger.warning(f"Failed to read {file_path}: {e}")
        return []


def get_dataset_unigrams(file_paths: Iterable[str], max_workers: int, dataset_name: str ='') -> Iterable[str]:
    """
    Takes in a list of transcripts in phrase reco format and extracts the unigrams across the corpus.
    The function processes the transcripts in parallel. 

    Inputs:
    1. Corpus - List of transcript file paths in phrase reco format.
    2. Number of workers allowed by the server.
    3. (Optional) name of the dataset for logging purposes.

    Outputs:
    1. List of unigrams in dataset.
    """

    logger.info(f'Extracting words from {dataset_name}')
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(get_transcript_unigrams, file) for file in file_paths]
        words = []
        for future in tqdm(as_completed(futures), total=len(futures), desc='Processing files...'):
            words.extend(future.result())
    
    executor.shutdown(wait=True)

    logger.info(f'{dataset_name} total words: {len(words)}')
    return words


def cnt_unigrams(ref_word: str, word_counter: Counter) -> dict:
    """
    Takes in a single reference word and returns the number of occurences of the unigram in the Counter container. 

    Inputs:
    1. Reference unigram.
    2. Counter container with the set of unigrams.

    Outputs:
    1. Dict with the frequency of the word in the Counter container.
    """
    cnt = word_counter[ref_word]
    return {ref_word: cnt}


def word_freq(ref_words: Iterable[str], words: Iterable[str], max_workers: int, dataset_name: str='', save_dir: str=None) -> pd.DataFrame:
    """
    Counts the occurances of a set of reference unigrams within a datasets. Saves the output to csv

    Inputs
    1. Reference unigrams to count within the dataset
    2. Unigrams extraced from the dataset
    3. Number of workers allowed by the server.
    4. (Optional) name of the dataset for logging and output naming purposes.
    5. (Optional) directory to save the output. If not specified, it will save to the data folder.
    """

    counter = Counter(words)
    logger.info('Calculating word frequencies')
    with ProcessPoolExecutor(max_workers=max_workers) as executor2:
        futures2 = [executor2.submit(cnt_unigrams, ref_word, counter) for ref_word in ref_words]
        word_cnts = {}
        for future2 in tqdm(as_completed(futures2), total=len(futures2), desc=f'Counting {dataset_name} words...'):
            word_cnts.update(future2.result())

    executor2.shutdown(wait=True)
    logger.info(f'{dataset_name} - Counting complete. Getting frequencies.')

    word_cnts = pd.DataFrame(list(word_cnts.items()), columns=['Word', f'{dataset_name} Count'.strip()])
    word_cnts[f'{dataset_name} %'.strip()] = word_cnts[f'{dataset_name} Count'.strip()]/word_cnts[f'{dataset_name} Count'.strip()].sum()
    logger.info(f'{dataset_name} - Calculated counts. Saving files')
    cur_time = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    file_name = f'{dataset_name}_word_frequency_analysis_{cur_time}.csv' if dataset_name != '' else f'word_frequency_analysis_{cur_time}.csv'
    logger.info(f'Output file: {file_name}')
    if save_dir:
        # save_path = f'{save_dir}{file_name}' if save_dir[-1] == "\\" else f'{save_dir}\\{file_name}'
        save_path = os.path.join(save_dir, file_name)
    else:
        # cur_time = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        save_path = f'.\\data\\{file_name}\\'
        # os.makedirs(save_dir, exist_ok=True)
        # save_path = f'{save_dir}{file_name}'
    word_cnts.to_csv(save_path, sep='\t', header=True, index=False)
    return word_cnts


def load_config(config_path: str) -> dict:
    """Load YAML configuration file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Dictionary with config data

    Raises:
        FileNotFoundError: Config file not found
        yaml.YAMLError: Invalid YAML syntax
        ValueError: Config file is empty
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if not config:
            raise ValueError("Config file is empty")
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML config: {e}")


def validate_config(config: dict) -> List[str]:
    """Validate configuration structure and file availability.

    Args:
        config: Configuration dictionary from load_config()

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Check config is not empty
    if not config:
        errors.append("Config is empty")
        return errors

    # 1. Check top-level structure
    if 'output_dir' not in config or not config['output_dir']:
        errors.append("Missing required field: output_dir")
    elif not isinstance(config['output_dir'], str) or not config['output_dir'].strip():
        errors.append("output_dir must be a non-empty string")

    if 'datasets' not in config:
        errors.append("Missing required field: datasets")
        return errors

    if not isinstance(config['datasets'], list) or len(config['datasets']) == 0:
        errors.append("datasets must be a non-empty list")
        return errors

    # 2. Validate max_workers if present
    max_workers = config.get('max_workers')
    if max_workers is not None:
        if not isinstance(max_workers, int) or max_workers < 1:
            errors.append(f"max_workers must be >= 1, got: {max_workers}")
        elif os.cpu_count() and max_workers > os.cpu_count():
            logger.warning(f"max_workers ({max_workers}) exceeds available CPU cores ({os.cpu_count()})")

    # 3. Validate output_dir exists or can be created
    if 'output_dir' in config and config['output_dir']:
        output_dir = Path(config['output_dir'])
        if not output_dir.exists() and not output_dir.parent.exists():
            errors.append(f"output_dir parent does not exist: {output_dir.parent}")

    # 4. Track dataset names for duplicate check and reference validation
    dataset_names = []

    # 5. Validate each dataset
    for idx, dataset in enumerate(config['datasets']):
        ds_name = dataset.get('name', f'dataset[{idx}]')

        # Check required fields
        if 'name' not in dataset or not dataset['name']:
            errors.append(f"Dataset {idx}: missing required field 'name'")
            ds_name = f'dataset[{idx}]'
        else:
            dataset_names.append(dataset['name'])

        if 'manifest_csv' not in dataset or not dataset['manifest_csv']:
            errors.append(f"Dataset '{ds_name}': missing required field 'manifest_csv'")

        if 'file_col' not in dataset or not dataset['file_col']:
            errors.append(f"Dataset '{ds_name}': missing required field 'file_col'")

        # Skip file validation if required fields are missing
        if 'manifest_csv' not in dataset or not dataset['manifest_csv']:
            continue

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
                if not isinstance(dataset['group_by_lob'], str) or not dataset['group_by_lob'].strip():
                    errors.append(f"Dataset '{ds_name}': group_by_lob must be a non-empty string")
                elif dataset['group_by_lob'] not in manifest_df.columns:
                    errors.append(f"Dataset '{ds_name}': group_by_lob column '{dataset['group_by_lob']}' not found in manifest CSV")

            # Check group_by_dataset column if specified
            if 'group_by_dataset' in dataset and dataset['group_by_dataset']:
                if not isinstance(dataset['group_by_dataset'], str) or not dataset['group_by_dataset'].strip():
                    errors.append(f"Dataset '{ds_name}': group_by_dataset must be a non-empty string")
                elif dataset['group_by_dataset'] not in manifest_df.columns:
                    errors.append(f"Dataset '{ds_name}': group_by_dataset column '{dataset['group_by_dataset']}' not found in manifest CSV")

            # Check manifest has data rows
            if len(manifest_df) == 0:
                errors.append(f"Dataset '{ds_name}': manifest CSV has no data rows")

        except Exception as e:
            errors.append(f"Dataset '{ds_name}': failed to load manifest CSV: {e}")

    # 6. Validate reference_dataset if specified
    reference_dataset = config.get('reference_dataset')
    if reference_dataset is not None:
        if reference_dataset not in dataset_names:
            errors.append(f"reference_dataset '{reference_dataset}' not found in datasets list. Available: {dataset_names}")

    # 7. Check for duplicate dataset names
    seen_names = set()
    for name in dataset_names:
        if name in seen_names:
            errors.append(f"Duplicate dataset name: '{name}'")
        seen_names.add(name)

    return errors


def process_single_group(output_name, manifest_df, file_col,
                        ref_words, is_independent_mode,
                        max_workers, output_dir):
    """Process a single dataset or group and generate frequency output.

    Args:
        output_name: Name for output file (e.g., "DEV_Commercial")
        manifest_df: DataFrame with file paths (for this group only)
        file_col: Column containing file paths
        ref_words: Reference unigram list (or None for independent mode)
        is_independent_mode: If True, build own reference from this data
        max_workers: Worker count for parallel processing
        output_dir: Output directory
    """
    file_paths = manifest_df[file_col].tolist()
    logger.info(f"Processing {output_name} ({len(file_paths)} files)")

    # Extract unigrams from this group's files
    words = get_dataset_unigrams(file_paths, max_workers, output_name)

    # Determine reference to use
    if is_independent_mode:
        # Independent mode: use this group's own unigrams as reference
        ref_words = list(set(words))
        logger.info(f"{output_name}: Built own reference ({len(ref_words)} unique unigrams)")
    # else: use pre-built ref_words from cross-dataset mode

    # Generate frequency analysis
    word_freq(ref_words, words, max_workers, output_name, output_dir)


def process_dataset_with_grouping(ds_name, manifest_df, file_col,
                                  group_by_lob, group_by_dataset,
                                  ref_words, is_independent_mode,
                                  max_workers, output_dir):
    """Apply grouping logic and generate frequency outputs.

    Args:
        ds_name: Dataset name
        manifest_df: DataFrame with file paths and grouping columns
        file_col: Column containing file paths
        group_by_lob: LOB grouping column name (or None)
        group_by_dataset: Dataset grouping column name (or None)
        ref_words: Reference unigram list (or None for independent mode)
        is_independent_mode: If True, each group builds own reference
        max_workers: Worker count
        output_dir: Output directory
    """

    # Case 1: No grouping
    if not group_by_lob and not group_by_dataset:
        logger.info("No grouping specified - single output")
        process_single_group(
            ds_name, manifest_df, file_col,
            ref_words, is_independent_mode,
            max_workers, output_dir
        )

    # Case 2: LOB grouping only
    elif group_by_lob and not group_by_dataset:
        lob_values = sorted(manifest_df[group_by_lob].unique())
        logger.info(f"Grouping by LOB: {len(lob_values)} groups: {lob_values}")

        # Create combined (all LOBs together)
        combined_name = f"{ds_name}_combined"
        logger.info(f"Creating {combined_name} ({len(manifest_df)} files)")
        process_single_group(
            combined_name, manifest_df, file_col,
            ref_words, is_independent_mode,
            max_workers, output_dir
        )

        # Create per-LOB outputs
        for lob_value in lob_values:
            df_lob = manifest_df[manifest_df[group_by_lob] == lob_value]
            output_name = f"{ds_name}_{lob_value}"
            logger.info(f"Creating {output_name} ({len(df_lob)} files)")
            process_single_group(
                output_name, df_lob, file_col,
                ref_words, is_independent_mode,
                max_workers, output_dir
            )

    # Case 3: Dataset grouping only
    elif not group_by_lob and group_by_dataset:
        dataset_values = sorted(manifest_df[group_by_dataset].unique())
        logger.info(f"Grouping by dataset: {len(dataset_values)} groups: {dataset_values}")

        # NO combined - just one output per dataset value
        for dataset_value in dataset_values:
            df_dataset = manifest_df[manifest_df[group_by_dataset] == dataset_value]
            output_name = f"{ds_name}_{dataset_value}"
            logger.info(f"Creating {output_name} ({len(df_dataset)} files)")
            process_single_group(
                output_name, df_dataset, file_col,
                ref_words, is_independent_mode,
                max_workers, output_dir
            )

    # Case 4: Both LOB and Dataset grouping (nested)
    else:
        dataset_values = sorted(manifest_df[group_by_dataset].unique())
        logger.info(f"Grouping by both LOB and dataset: {len(dataset_values)} dataset values")

        for dataset_value in dataset_values:
            df_dataset = manifest_df[manifest_df[group_by_dataset] == dataset_value]
            logger.info(f"Processing {ds_name}_{dataset_value} ({len(df_dataset)} files)")

            # Create combined for this dataset value (all LOBs in this dataset)
            combined_name = f"{ds_name}_{dataset_value}_combined"
            logger.info(f"Creating {combined_name}")
            process_single_group(
                combined_name, df_dataset, file_col,
                ref_words, is_independent_mode,
                max_workers, output_dir
            )

            # Create individual LOB splits within this dataset value
            lob_values = sorted(df_dataset[group_by_lob].unique())
            logger.info(f"Found {len(lob_values)} LOB values: {lob_values}")
            for lob_value in lob_values:
                df_lob = df_dataset[df_dataset[group_by_lob] == lob_value]
                output_name = f"{ds_name}_{dataset_value}_{lob_value}"
                logger.info(f"Creating {output_name} ({len(df_lob)} files)")
                process_single_group(
                    output_name, df_lob, file_col,
                    ref_words, is_independent_mode,
                    max_workers, output_dir
                )


def run_from_config(config: dict) -> None:
    """Execute word frequency analysis from validated config.

    Args:
        config: Validated configuration dictionary

    Note: Config must be validated before calling this function.
    """
    # 1. Extract config values
    output_dir = config['output_dir']
    reference_dataset = config.get('reference_dataset')
    max_workers_config = config.get('max_workers')
    datasets = config['datasets']

    # 2. Determine worker count
    if max_workers_config is None:
        max_workers = max(1, os.cpu_count() // 2)
        logger.info(f"Auto-detected max_workers: {max_workers} (half of {os.cpu_count()} cores)")
    else:
        max_workers = max_workers_config
        logger.info(f"Using configured max_workers: {max_workers}")

    # 3. Log analysis start
    logger.info("Starting word frequency analysis from config")

    # 4. PHASE 1: Build reference (if cross-dataset mode)
    ref_words = None
    is_independent_mode = True

    if reference_dataset is not None:
        # Cross-dataset mode
        logger.info(f"Cross-dataset mode: using '{reference_dataset}' as reference")

        # Find reference dataset in config
        ref_dataset_config = [ds for ds in datasets if ds['name'] == reference_dataset][0]

        # Load full manifest (ignore any grouping)
        ref_manifest_df = pd.read_csv(ref_dataset_config['manifest_csv'])
        ref_file_col = ref_dataset_config['file_col']
        ref_file_paths = ref_manifest_df[ref_file_col].tolist()

        # Extract all unigrams from reference dataset
        logger.info(f"Building reference from {reference_dataset} ({len(ref_file_paths)} files)")
        ref_words_all = get_dataset_unigrams(ref_file_paths, max_workers, reference_dataset)
        ref_words = list(set(ref_words_all))
        logger.info(f"Reference built: {len(ref_words)} unique unigrams from {len(ref_words_all)} total words")

        is_independent_mode = False
    else:
        # Independent mode
        logger.info("Independent mode: each dataset will use own unigrams as reference")

    # 5. PHASE 2: Process each dataset
    datasets_processed = 0
    datasets_total = len(datasets)

    for dataset in datasets:
        ds_name = dataset['name']
        manifest_csv = dataset['manifest_csv']
        file_col = dataset['file_col']
        group_by_lob = dataset.get('group_by_lob')
        group_by_dataset = dataset.get('group_by_dataset')

        try:
            manifest_df = pd.read_csv(manifest_csv)
            logger.info(f"Processing dataset: {ds_name} ({len(manifest_df)} files in manifest)")

            # Apply grouping logic
            process_dataset_with_grouping(
                ds_name, manifest_df, file_col,
                group_by_lob, group_by_dataset,
                ref_words, is_independent_mode,
                max_workers, output_dir
            )

            datasets_processed += 1

        except Exception as e:
            logger.error(f"Failed to process dataset '{ds_name}': {e}")
            continue

    # 6. PHASE 3: Summary
    logger.info("Analysis complete")
    logger.info(f"Datasets processed: {datasets_processed}/{datasets_total}")
    if datasets_processed < datasets_total:
        logger.warning(f"{datasets_total - datasets_processed} dataset(s) failed - check log for details")


if __name__ == "__main__":
    # Example use:
    prs = glob.glob(".\\Media\\Telco\\PhraseReco\\*.zip")
    prs_dev = prs[0:10]
    prs_itv = prs[10::]
    print(len(prs_dev), len(prs_itv ))

    words_dev = get_dataset_unigrams(prs_dev, max_workers=2, dataset_name='DEV')
    ref_words = list(set(words_dev))
    words_itv = get_dataset_unigrams(prs_itv, max_workers=2, dataset_name='ITV')
    word_cnt_dev = word_freq(ref_words, words_dev, 2, 'DEV', r'C:\Users\nlazarus\OneDrive - Nice Systems Ltd\Documents\CitiTools\outputs').sort_values(by=f'DEV %', ascending=False).reset_index(drop=True)
    word_cnt_itv = word_freq(ref_words, words_itv, 2, 'ITV', r'C:\Users\nlazarus\OneDrive - Nice Systems Ltd\Documents\CitiTools\outputs').sort_values(by=f'ITV %', ascending=False).reset_index(drop=True)
    print(len(word_cnt_dev))
    print(len(word_cnt_itv))
