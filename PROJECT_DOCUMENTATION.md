# Citi MRM Tools - Project Documentation

**Generated:** 2026-05-11  
**Updated:** 2026-05-12

## Project Mission

**Goal:** Automate the Model Risk Management (MRM) evaluation and approval process for machine learning models deployed to clients.

**Current State:** Python scripts and notebooks used by technical practitioners to generate MRM documentation and evidence.

**Next Step:** Build a simple UI tool where users can point to datasets and models, then automatically generate all required MRM outputs.

**Target Users:**
- Model validators (semi-technical) - understand models but not necessarily Python
- Risk managers (non-technical) - need to review evidence without running code
- Business stakeholders (non-technical) - need performance summaries and visualizations

**Long-term Vision:** Fully automated MRM workflow from model output to approval documentation through a user-friendly interface.

---

## UI Tool Vision

The end goal is a simple desktop application where non-technical users can:

**Input Section:**
1. Browse to select dataset directories containing phrase reco files
2. Browse to select model prediction CSV files
3. Choose dataset names/labels from dropdowns
4. Select output directory for results

**Analysis Selection:**
- ☑ Generate Word Statistics (dataset characterization)
- ☑ Generate Word Frequency Analysis (vocabulary distribution)
- ☑ Generate ROC Curves (model performance)
- ☑ Generate Full MRM Report (all analyses + summary PDF)

**Execution:**
- "Run Analysis" button
- Progress bar showing current step
- Log viewer showing real-time progress
- Cancel button for long-running jobs

**Output:**
- Summary dashboard showing:
  - Generated files (clickable links)
  - Key metrics (AUC scores, dataset sizes, word counts)
  - Thumbnail previews of plots
- "Open Output Folder" button
- "Export Report" button (PDF with all artifacts)

**Technology Considerations:**
- Must run on Windows (target environment)
- Must work offline (no internet dependency)
- Python 3.7.4 compatible
- Options: Tkinter (built-in), PyQt, or simple web interface (Flask + local browser)

---

## Business Context

When machine learning models are created for clients, they must pass through a Model Risk Management (MRM) evaluation process before deployment. This process requires:

1. **Statistical Evidence** - Descriptive statistics about model inputs (word counts, frequencies)
2. **Performance Metrics** - Model evaluation metrics (ROC curves, AUC scores)
3. **Documentation** - Clear, reproducible reports for non-technical reviewers
4. **Traceability** - Logs and versioned outputs for audit compliance

This project generates the required outputs for the MRM process. Each script addresses a specific MRM requirement:

- **word_statistics.py** → Input data characterization (transcript statistics)
- **word_frequency_analysis.py** → Vocabulary analysis and data distribution
- **tpr_fpr_curve.py** → Model performance evaluation (classification metrics)

---

## Overview
This project contains Python scripts for analyzing datasets and models as part of the Model Risk Management (MRM) process. The scripts process audio transcript data in "phrase reco" format (tab-separated CSV files) to generate statistical analyses and model evaluation metrics.

### Design Principles for Accessibility
As we evolve toward broader accessibility:
- **Simplicity** - Clear function signatures with minimal required parameters
- **Robustness** - Graceful handling of edge cases and malformed data
- **Logging** - Comprehensive logs for debugging and audit trails
- **Documentation** - Inline docstrings and usage examples in `if __name__ == "__main__"` blocks
- **Output clarity** - Self-documenting output filenames with timestamps and dataset names

---

## Scripts

### 1. **word_statistics.py**
**Purpose:** Generate descriptive statistics about the number of unigrams (words) per transcript.

**Recommended Usage (Config-Driven):**
Users modify `config_word_stats.yaml` and run:
```bash
python word_statistics.py
# or with custom config:
python word_statistics.py --config my_analysis.yaml
```

**Config Structure:**
```yaml
output_file: "./outputs/word_stats.csv"
datasets:
  - name: "Analysis"
    manifest_csv: "./files.csv"     # CSV with phrase reco file paths
    file_col: "File"                # Column containing file paths
    group_by_lob: "LineOfBusiness"  # Optional: LOB grouping
    group_by_dataset: "DatasetType" # Optional: DEV/VAL grouping
```

**Grouping Behavior:**
- No grouping: Single combined output
- LOB only: One row per LOB value
- Dataset only: One row per dataset value  
- Both: Creates `{name}_{dataset}_combined` + `{name}_{dataset}_{lob}` rows

**Programmatic API (Legacy, Still Supported):**
- `get_word_count(file)` - Counts words in a single transcript file
- `word_stats_by_label(datasets, file_col, label_col, save_path)` - Statistics grouped by dataset AND label
- `word_stats(datasets, file_col, save_path)` - Statistics grouped by dataset only

**Input Format (Programmatic):**
- Datasets: List of tuples `('dataset_name', dataframe)`
- Dataframe must contain:
  - File path column (phrase reco .csv.zip files)
  - Optional: Label column for grouping

**Output:**
- CSV file with descriptive statistics (count, mean, std, min, 25%, 50%, 75%, max)
- Statistics per dataset or per grouping combination

**Phrase Reco Format Expected:**
```
Nxpr | Channel | Type | Phrase | StartCS | EndCS | Score
```
- Filters for `Type=='T'` rows (transcribed text)

---

### 2. **word_frequency_analysis.py**
**Purpose:** Generate comprehensive unigram frequency analysis across multiple datasets using parallel processing.

**Recommended Usage (Config-Driven):**
Users modify `config_word_frequency.yaml` and run:
```bash
python word_frequency_analysis.py
# or with custom config:
python word_frequency_analysis.py --config my_analysis.yaml
```

**Config Structure:**
```yaml
output_dir: "./outputs"
max_workers: 4  # Optional: auto-detected if omitted
reference_dataset: "DEV"  # Optional: omit for independent mode

datasets:
  - name: "DEV"
    manifest_csv: "./dev_files.csv"
    file_col: "FilePath"
    group_by_lob: "LineOfBusiness"      # Optional: LOB grouping
    group_by_dataset: "DatasetSplit"    # Optional: DEV/VAL grouping
```

**Analysis Modes:**
- **Cross-dataset mode** (when `reference_dataset` is specified):
  - Builds reference unigram set from specified dataset
  - All other datasets count against this reference
  - Use when comparing vocabulary consistency across train/test/validation
- **Independent mode** (when `reference_dataset` is omitted):
  - Each dataset builds own reference from its unigrams
  - Use when datasets have different vocabularies

**Grouping Behavior:**
- No grouping: Single output file
- LOB only: Creates `{name}_combined` + one file per LOB value
- Dataset only: One file per dataset value (no combined)
- Both: Creates `{name}_{dataset}_combined` + `{name}_{dataset}_{lob}` per LOB within each dataset split

**Programmatic API (Legacy, Still Supported):**
- `get_transcript_unigrams(file_path)` - Extracts all unigrams from a single transcript
- `get_dataset_unigrams(file_paths, max_workers, dataset_name)` - Extracts unigrams from entire dataset (parallel processing)
- `cnt_unigrams(ref_word, word_counter)` - Counts occurrences of a reference word
- `word_freq(ref_words, words, max_workers, dataset_name, save_dir)` - Calculates word frequencies against reference set

**Output:**
- CSV file per group/dataset with columns:
  - `Word` - The unigram
  - `{dataset_name} Count` - Absolute frequency
  - `{dataset_name} %` - Relative frequency (percentage)
- Timestamped filenames: `{dataset_name}_word_frequency_analysis_{timestamp}.csv`

**Performance:**
- Uses `ProcessPoolExecutor` for parallel processing
- Progress bars via `tqdm`
- Auto-detects CPU cores (uses half by default)
- Configurable worker count via config

---

### 3. **tpr_fpr_curve.py**
**Purpose:** Generate ROC (Receiver Operating Characteristic) curves for model evaluation.

**Key Functions:**
- `recall_vs_fpr_curve(df, pred_col, truth_col, score_col, dataset_name, save_dir)` - Computes and plots TPR vs FPR (library API)
- `main()` - Config-driven CLI entry point (recommended for users)
- `run_from_config(config)` - Processes multiple datasets from YAML config
- `validate_config(config)` - Comprehensive validation with helpful error messages

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

**Config-Driven Usage (Recommended):**
Users can now run ROC analysis by modifying `config_tpr_v_fpr.yaml`:
```yaml
output_dir: "./outputs"
datasets:
  - csv_path: "./test_predictions.csv"
    name: "Test"
    pred_col: "ModelPrediction"
    truth_col: "TrueValue"
    score_col: "PredictionScore"
    group_by: "LineOfBusiness"  # Optional: creates separate plots per LoB
```

Run: `python tpr_fpr_curve.py`

**Stratification Support:**
When `group_by` is specified, the script generates separate ROC curves for each unique value in that column. Output files are named `tpr_v_fpr_{dataset_name}_{group_value}.png`.

**Multi-Dataset Support:**
Multiple datasets can be analyzed in a single run by adding more entries to the `datasets` list in the config file.

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

**Config-driven (recommended):**
```bash
python word_statistics.py --config my_config.yaml
```

**Programmatic:**
```python
from word_statistics import word_stats
import pandas as pd

datasets = [
    ('DEV', pd.DataFrame({'File': dev_file_paths})),
    ('ITV', pd.DataFrame({'File': itv_file_paths}))
]
word_stats(datasets, 'File', './outputs/word_stats.csv')
```

### word_frequency_analysis.py

**Config-driven (recommended):**
```bash
python word_frequency_analysis.py --config my_config.yaml
```

**Programmatic:**
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

---

## Summary: Script Purposes in MRM Context

### word_statistics.py - **Data Characterization**
**MRM Requirement:** Demonstrate understanding of input data characteristics  
**Output for MRM:** Descriptive statistics showing transcript length distributions across datasets  
**Reviewer Question Answered:** "What is the typical size and variability of input transcripts?"  
**Accessibility Need:** ✅ **ACHIEVED** - Users modify YAML config and click "Run" in VSCode. No Python knowledge required.

### word_frequency_analysis.py - **Vocabulary Analysis**
**MRM Requirement:** Show consistency and distribution of vocabulary across train/test/validation sets  
**Output for MRM:** Word frequency tables showing coverage and distribution  
**Reviewer Question Answered:** "Are there vocabulary shifts between datasets that could affect model performance?"  
**Accessibility Need:** ✅ **ACHIEVED** - Users modify YAML config (specify datasets, grouping, reference mode) and run. Config validation provides clear error messages.

### tpr_fpr_curve.py - **Model Performance Evaluation**
**MRM Requirement:** Standard classification performance metrics (ROC curve, AUC)  
**Output for MRM:** Publication-quality ROC curve plots with AUC values  
**Reviewer Question Answered:** "How well does the model discriminate between classes?"  
**Accessibility Need:** Business users need to generate these plots from prediction files without understanding scikit-learn internals

---

## Evolution Roadmap

**Phase 1 (Current):** Working scripts for technical users  
- ✅ Core analysis functions (word stats, frequency analysis, ROC curves)
- ✅ Logging and error handling
- ✅ Example usage patterns

**Phase 2 (Complete):** Refactoring for UI integration  
- ✅ Standardize input/output interfaces (all scripts)
- ✅ Improve error messages for non-technical users (config validation)
- ✅ Add input validation and helpful error guidance (validate_config)
- ✅ Extract core logic from hardcoded example code (all scripts now config-driven)

**Phase 3 (Next):** UI Development  
- 📋 Simple UI where users can:
  - Point to dataset directories (file browser)
  - Point to model prediction files (file browser)
  - Select which analyses to run (checkboxes)
  - Specify output directory (file browser)
  - Click "Generate MRM Report" button
- 📋 Progress indicators during long-running analyses
- 📋 Summary dashboard showing generated outputs

**Phase 4 (Future):** Enterprise Integration  
- 📋 Configuration templates for common model types
- 📋 Batch processing for multiple models
- 📋 Integration with model deployment pipelines
- 📋 PDF report generation with all MRM artifacts
