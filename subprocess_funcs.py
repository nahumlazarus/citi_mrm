from typing import Iterable
from tqdm import tqdm
import pandas as pd
import numpy as np
import os
import logging
import logging.config
from datetime import datetime
from collections import Counter
import subprocess
import glob
logging.config.fileConfig('logger.ini')
logger = logging.getLogger("research")


def run_bat_file(bat_file_path: str):
    proc1 = subprocess.run(bat_file_path, shell=True)
    bat_fn = os.path.basename(bat_file_path)

    if proc1.returncode == 0:
        logger.info(f'{bat_fn} complete.')
    else:
        logger.info('Error running {bat_fn}')
        return 