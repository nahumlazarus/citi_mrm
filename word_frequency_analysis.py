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

    Inputs:
    1. Single transcript in phrase reco format.

    Outputs:
    1. List of unigrams from the transcript.
    """

    tscript = pd.read_csv(file_path, sep='\t', header=None, names=['Nxpr', 'Channel', 'Type', 'Phrase', 'StartCS', 'EndCS', 'Score'])
    words = list(tscript[tscript['Type']=='T']['Phrase'])
    return words


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
