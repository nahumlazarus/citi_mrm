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
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML config: {e}")


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


