# Citi MRM Tools - Project Documentation

**Generated:** 2026-05-11

## Overview
This project contains Python scripts for analyzing datasets and models as part of the Model Risk Management (MRM) process. The scripts process audio transcript data in "phrase reco" format (tab-separated CSV files) to generate statistical analyses and model evaluation metrics.

---

## Scripts

### 1. **word_statistics.py**
**Purpose:** Generate descriptive statistics about the number of unigrams (words) per transcript.

**Key Functions:**
- `get_word_count(file)` - Counts words in a single transcript file
- `word_stats_by_label(datasets, file_col, label_col, save_path)` - Calculates word count statistics grouped by dataset AND label
- `word_stats(datasets, file_col, save_path)` - Calculates word count statistics grouped by dataset only

**Input Format:**
- Datasets: List of tuples `('dataset_name', dataframe)`
- Dataframe must contain:
  - File path column (phrase reco .csv.zip files)
  - Optional: Label column for grouping

**Output:**
- CSV file with descriptive statistics (count, mean, std, min, 25%, 50%, 75%, max)
- Statistics per dataset or per dataset+label combination

**Phrase Reco Format Expected:**
```
Nxpr | Channel | Type | Phrase | StartCS | EndCS | Score
```
- Filters for `Type=='T'` rows (transcribed text)

---

### 2. **word_frequency_analysis.py**
**Purpose:** Generate comprehensive unigram frequency analysis across multiple datasets using parallel processing.

**Key Functions:**
- `get_transcript_unigrams(file_path)` - Extracts all unigrams from a single transcript
- `get_dataset_unigrams(file_paths, max_workers, dataset_name)` - Extracts unigrams from entire dataset (parallel processing)
- `cnt_unigrams(ref_word, word_counter)` - Counts occurrences of a reference word
- `word_freq(ref_words, words, max_workers, dataset_name, save_dir)` - Calculates word frequencies against reference set

**Workflow:**
1. Build reference unigram set from development dataset
2. Count occurrences of reference unigrams across all datasets
3. Calculate both absolute counts and percentages

**Input Format:**
- File paths to phrase reco files (.csv.zip format)
- Same tab-separated format as word_statistics.py

**Output:**
- CSV file per dataset with columns:
  - `Word` - The unigram
  - `{dataset_name} Count` - Absolute frequency
  - `{dataset_name} %` - Relative frequency (percentage)
- Timestamped filenames: `{dataset_name}_word_frequency_analysis_{timestamp}.csv`

**Performance:**
- Uses `ProcessPoolExecutor` for parallel processing
- Progress bars via `tqdm`
- Configurable worker count

---

### 3. **tpr_fpr_curve.py**
**Purpose:** Generate ROC (Receiver Operating Characteristic) curves for model evaluation.

**Key Function:**
- `recall_vs_fpr_curve(df, pred_col, truth_col, score_col, dataset_name, save_dir)` - Computes and plots TPR vs FPR

**Metrics Calculated:**
- **TPR (True Positive Rate / Recall)** - Sensitivity of the model
- **FPR (False Positive Rate)** - 1 - Specificity
- **ROC AUC** - Area Under the ROC Curve

**Input Format:**
- DataFrame with columns:
  - `pred_col` - Model predictions
  - `truth_col` - Ground truth labels
  - `score_col` - Model confidence scores

**Output:**
- PNG image: `tpr_v_fpr_{dataset_name}.png` (150 DPI)
- Plots ROC curve with AUC value
- Includes diagonal reference line (random classifier baseline)

**Robustness:**
- Handles degenerate cases (all same labels)
- Coerces non-numeric scores to 0.0
- Creates output directory if needed

---

## Common Infrastructure

### Logging System
All scripts use a **shared logging system**:
- Logger name: `"citi_mrm_tools"`
- Log file: `citi_mrm_tools.log` (in project root)
- Format: `timestamp | logger_name | message`
- Timestamps: `YYYY-MM-DD HH:MM:SS`

### Data Format: Phrase Reco Files
All scripts expect **phrase reco format** (.csv or .csv.zip):
```
Column 1: Nxpr (expression number)
Column 2: Channel (audio channel)
Column 3: Type (T=transcript, other types filtered out)
Column 4: Phrase (the actual text/word)
Column 5: StartCS (start centiseconds)
Column 6: EndCS (end centiseconds)
Column 7: Score (confidence score)
```
- Tab-separated (TSV)
- No header row
- Scripts filter for `Type == 'T'` to get only transcribed text

---

## Dependencies Identified

### Core Libraries:
- **pandas** - DataFrame operations, CSV I/O
- **numpy** - Numerical operations
- **matplotlib** - Plotting (pyplot)

### Standard Library:
- **logging** - Logging infrastructure
- **pathlib** - Path operations
- **glob** - File pattern matching
- **re** - Regular expressions
- **os** - File system operations
- **datetime** - Timestamps
- **collections.Counter** - Word counting
- **typing** - Type hints

### Parallel Processing:
- **concurrent.futures.ProcessPoolExecutor** - Parallel processing
- **tqdm** - Progress bars

### Machine Learning:
- **sklearn.metrics** - ROC AUC, ROC curve calculations
  - `roc_auc_score`
  - `roc_curve`

---

## Example Usage Patterns

### word_statistics.py
```python
datasets = [
    ('DEV', pd.DataFrame({'File': dev_file_paths})),
    ('ITV', pd.DataFrame({'File': itv_file_paths}))
]
word_stats(datasets, 'File', './outputs/word_stats.csv')
```

### word_frequency_analysis.py
```python
# Build reference set from dev dataset
words_dev = get_dataset_unigrams(dev_files, max_workers=4, dataset_name='DEV')
ref_words = list(set(words_dev))

# Analyze other datasets against reference
words_itv = get_dataset_unigrams(itv_files, max_workers=4, dataset_name='ITV')
word_freq(ref_words, words_itv, 4, 'ITV', './outputs')
```

### tpr_fpr_curve.py
```python
recall_vs_fpr_curve(
    df,
    pred_col='ModelPrediction',
    truth_col='TrueValue',
    score_col='PredictionScore',
    dataset_name='Validation',
    save_dir='./outputs'
)
```

---

## Output Structure
Scripts expect/create these directories:
- `./data/` - Default output for word frequency analysis
- `./outputs/` - User-specified output directory
- `./Media/Telco/PhraseReco/` - Example input directory structure

---

## Notes
- All scripts include `if __name__ == "__main__"` blocks with example usage
- Error handling is minimal (bare `except` in `get_word_count`)
- Scripts are designed for Windows paths but use `os.path.join()` for some cross-platform compatibility
- Parallel processing uses configurable worker counts for different server capabilities
