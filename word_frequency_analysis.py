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

    # 4. Validate reference_dataset if specified
    reference_dataset = config.get('reference_dataset')
    if reference_dataset is not None:
        dataset_names = [ds.get('name') for ds in config['datasets']]
        if reference_dataset not in dataset_names:
            errors.append(f"reference_dataset '{reference_dataset}' not found in datasets list. Available: {dataset_names}")

    # 5. Track dataset names for duplicate check
    dataset_names = []

    # 6. Validate each dataset
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

    # 7. Check for duplicate dataset names
    seen_names = set()
    for name in dataset_names:
        if name in seen_names:
            errors.append(f"Duplicate dataset name: '{name}'")
        seen_names.add(name)

    return errors


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
