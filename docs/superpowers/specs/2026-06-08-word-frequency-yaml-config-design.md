# Word Frequency Analysis YAML Config - Design Specification

**Date:** 2026-06-08  
**Author:** Claude (Superpowers Brainstorming)  
**Status:** Approved

## Overview

Refactor `word_frequency_analysis.py` to support YAML configuration-driven execution, following the successful pattern from `word_statistics.py` and `tpr_fpr_curve.py`. This enables non-technical users to generate word frequency analyses by modifying a config file and clicking run.

## Goals

1. **Config-driven execution:** Users specify datasets, reference dataset, column mappings, and grouping in YAML
2. **Dual analysis modes:** Cross-dataset (shared reference) or independent (self-referencing)
3. **Multi-dataset support:** Process multiple datasets in a single run
4. **Flexible grouping:** Support LOB grouping, Dataset grouping, or both with appropriate aggregations
5. **Validation-first:** Catch all configuration and manifest errors before processing
6. **Backward compatibility:** Keep existing function APIs for programmatic/notebook use
7. **VSCode-friendly:** Click "Run" button or use command line
8. **Consistent UX:** Match word_statistics.py and tpr_fpr_curve.py patterns
9. **Smart resource management:** Auto-detect CPU cores, default to half for safety

## Design Approach

**Strategy:** Minimal additive refactor - add config layer on top of existing functions.

- Keep all existing functions unchanged (`get_transcript_unigrams`, `get_dataset_unigrams`, `cnt_unigrams`, `word_freq`)
- Add new functions for config loading, validation, and orchestration
- Add grouping logic in orchestration layer
- Add CLI with argparse for config file specification
- Maintain single-file structure (no module decomposition)
- Add error handling to `get_transcript_unigrams()` (return empty list on error)

## Architecture

### High-Level Flow

```
User runs: python word_frequency_analysis.py

main()
  ↓
load_config('config_word_frequency.yaml')
  ↓
validate_config(config)  [FAIL-FAST if errors]
  ↓
run_from_config(config)
  ↓
PHASE 1: Build reference (if cross-dataset mode)
  ↓
PHASE 2: Process each dataset with grouping logic
  ↓
PHASE 3: Summary and completion
```

### File Structure

**Modified Files:**
- `word_frequency_analysis.py` - Add ~250-300 lines for config support

**New Files:**
- `config_word_frequency.yaml` - Template config with inline documentation

**No new dependencies** - PyYAML already available from previous refactors

### Key Design Principles

1. **Backward compatibility** - Existing functions unchanged, can still be imported and used programmatically
2. **Fail-fast validation** - Catch all config errors before processing
3. **Continue-on-error processing** - Log individual file failures, keep going
4. **Consistent UX** - Matches word_statistics.py and tpr_fpr_curve.py patterns
5. **Explicit control** - No magic defaults, user must be explicit about reference dataset

## YAML Config Structure

### Schema

```yaml
# Required top-level keys
output_dir: string              # Directory for output CSV files
reference_dataset: string|null  # Dataset name to use as reference, or null for independent mode
max_workers: int|null           # Worker count for parallel processing, null = auto-detect

# Required: List of datasets
datasets: list                  # Min 1 dataset
  - name: string               # Required: Dataset label for output files
    manifest_csv: string       # Required: Path to CSV with phrase reco file paths
    file_col: string           # Required: Column name containing file paths
    group_by_lob: string       # Optional: Column name for LOB grouping
    group_by_dataset: string   # Optional: Column name for DEV/VAL grouping
```

### Example Configs

**Example 1: Cross-dataset mode with LOB grouping**
```yaml
output_dir: "./outputs"
reference_dataset: "DEV"  # DEV is reference for all datasets
max_workers: null         # Auto-detect (half of CPU cores)

datasets:
  - name: "DEV"
    manifest_csv: "./data/dev_files.csv"
    file_col: "File"
    group_by_lob: "LineOfBusiness"
  - name: "ITV"
    manifest_csv: "./data/itv_files.csv"
    file_col: "File"
    group_by_lob: "LineOfBusiness"
  - name: "VAL"
    manifest_csv: "./data/val_files.csv"
    file_col: "File"
    group_by_lob: "LineOfBusiness"
```

**Output files created:**
- `DEV_combined_word_frequency_2026-06-08_143022.csv` (all DEV LOBs)
- `DEV_Commercial_word_frequency_2026-06-08_143025.csv`
- `DEV_Retail_word_frequency_2026-06-08_143028.csv`
- `ITV_combined_word_frequency_2026-06-08_143031.csv` (all ITV LOBs)
- `ITV_Commercial_word_frequency_2026-06-08_143034.csv`
- `ITV_Retail_word_frequency_2026-06-08_143037.csv`
- `VAL_combined_word_frequency_2026-06-08_143040.csv` (all VAL LOBs)
- `VAL_Commercial_word_frequency_2026-06-08_143043.csv`
- `VAL_Retail_word_frequency_2026-06-08_143046.csv`

**All files use the same reference unigram set** (extracted from full DEV dataset).

---

**Example 2: Independent mode, no grouping**
```yaml
output_dir: "./outputs"
reference_dataset: null  # Independent mode (or omit field)
max_workers: 4           # Explicit worker count

datasets:
  - name: "Analysis_Q1"
    manifest_csv: "./q1_files.csv"
    file_col: "File"
  - name: "Analysis_Q2"
    manifest_csv: "./q2_files.csv"
    file_col: "File"
```

**Output files created:**
- `Analysis_Q1_word_frequency_2026-06-08_143022.csv` (uses own unigrams as reference)
- `Analysis_Q2_word_frequency_2026-06-08_143030.csv` (uses own unigrams as reference)

**Each dataset self-references** - different unigram vocabularies.

---

**Example 3: Cross-dataset with both groupings**
```yaml
output_dir: "./outputs"
reference_dataset: "Q1_Analysis"
max_workers: null

datasets:
  - name: "Q1_Analysis"
    manifest_csv: "./q1_files.csv"
    file_col: "File"
    group_by_lob: "LineOfBusiness"      # Values: Commercial, Retail
    group_by_dataset: "DatasetType"     # Values: DEV, VAL
```

**Manifest CSV structure:**
```
File                          | LineOfBusiness | DatasetType
/path/to/file1.csv.zip       | Commercial     | DEV
/path/to/file2.csv.zip       | Retail         | DEV
/path/to/file3.csv.zip       | Commercial     | VAL
/path/to/file4.csv.zip       | Retail         | VAL
```

**Output files created:**
- `Q1_Analysis_DEV_combined_word_frequency_*.csv` (all DEV LOBs)
- `Q1_Analysis_DEV_Commercial_word_frequency_*.csv`
- `Q1_Analysis_DEV_Retail_word_frequency_*.csv`
- `Q1_Analysis_VAL_combined_word_frequency_*.csv` (all VAL LOBs)
- `Q1_Analysis_VAL_Commercial_word_frequency_*.csv`
- `Q1_Analysis_VAL_Retail_word_frequency_*.csv`

**Reference built from full Q1_Analysis dataset** (all LOBs, all dataset types combined).

### Analysis Modes

**Mode 1: Cross-Dataset Analysis**
- User specifies `reference_dataset: "DatasetName"`
- One dataset designated as reference (typically DEV/training data)
- Extract unique unigrams from **full reference dataset** (ignoring any grouping)
- Count those same reference unigrams in all datasets
- **Use case:** Compare how training vocabulary appears across different datasets

**Mode 2: Independent Analysis**
- User specifies `reference_dataset: null` or omits field entirely
- Each dataset uses its own unigrams as reference
- Extract unique unigrams from dataset, count in same dataset
- **Use case:** Completely independent frequency analyses

### Grouping Behavior Matrix

| reference_dataset | group_by_lob | group_by_dataset | Output Behavior |
|-------------------|--------------|------------------|-----------------|
| "DEV" | Not specified | Not specified | Single reference from DEV, one output per dataset |
| "DEV" | Specified | Not specified | Single reference from full DEV, outputs: `{name}_combined` + `{name}_{lob}` |
| "DEV" | Not specified | Specified | Single reference from full DEV, outputs: `{name}_{dataset}` (no combined) |
| "DEV" | Both specified | Both specified | Single reference from full DEV, outputs: `{name}_{dataset}_combined` + `{name}_{dataset}_{lob}` |
| null/omitted | Any | Any | Each dataset self-references, grouping applied independently |

### Grouping Output Rules

**Rule 1: No grouping**
- Output: `{dataset_name}_word_frequency_*.csv`

**Rule 2: LOB grouping only**
- Output: `{dataset_name}_combined_word_frequency_*.csv` (all LOBs together)
- Plus: `{dataset_name}_{lob_value}_word_frequency_*.csv` (one per LOB)

**Rule 3: Dataset grouping only**
- Output: `{dataset_name}_{dataset_value}_word_frequency_*.csv` (one per dataset value)
- **No combined file** for dataset grouping

**Rule 4: Both LOB and Dataset grouping**
- For each dataset_value:
  - Output: `{dataset_name}_{dataset_value}_combined_word_frequency_*.csv` (all LOBs in this dataset value)
  - Plus: `{dataset_name}_{dataset_value}_{lob_value}_word_frequency_*.csv` (one per LOB)

**Key principle:** Reference is ALWAYS built from the full dataset (all groups combined). Grouping only affects output file organization.

## Component Specifications

### 1. `load_config(config_path: str) -> dict`

**Purpose:** Load and parse YAML config file.

**Implementation:**
```python
import yaml

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
```

---

### 2. `validate_config(config: dict) -> List[str]`

**Purpose:** Comprehensive validation before processing starts (fail-fast).

**Validation Checks (in order):**

1. **Top-level structure**
   - `output_dir` exists and is non-empty string
   - `datasets` exists and is non-empty list
   - `max_workers` (if present) is valid integer or null

2. **Worker count validation**
   - If specified, must be >= 1
   - Warn if exceeds `os.cpu_count()` (log warning, don't error)

3. **Output directory validation**
   - `output_dir` exists or parent directory exists for creation
   - Error: `"output_dir does not exist: {path}"`

4. **Reference dataset validation**
   - If `reference_dataset` specified and not null, it must match a dataset name
   - Error: `"reference_dataset '{name}' not found in datasets list. Available: {list}"`

5. **Per-dataset structure validation**
   - Required fields present: `name`, `manifest_csv`, `file_col`
   - All required fields are non-empty strings
   - `group_by_lob` (if present) is non-empty string
   - `group_by_dataset` (if present) is non-empty string

6. **File system checks**
   - Each `manifest_csv` file exists
   - Error: `"Dataset '{name}': manifest CSV not found: {path}"`

7. **Manifest content validation**
   - Each manifest CSV loads successfully with pandas
   - `file_col` column exists in manifest
   - If `group_by_lob` specified, that column exists
   - If `group_by_dataset` specified, that column exists
   - Manifest has at least one data row (not just headers)
   - Errors include dataset name and specific issue

8. **Name collision checks**
   - No duplicate dataset names
   - Error: `"Duplicate dataset name: '{name}'"`

**Returns:** List of error messages (empty if valid)

**Error message format:**
```
Configuration validation failed:
  - reference_dataset 'DEV' not found in datasets list. Available: ['Training', 'Test']
  - Dataset 'Training': manifest CSV not found: ./missing.csv
  - Dataset 'Test': column 'LineOfBusiness' not found in manifest CSV
  - max_workers must be >= 1, got: 0
```

**Implementation note:** Load each manifest CSV with pandas to verify structure, but don't keep in memory (reload during processing).

---

### 3. `run_from_config(config: dict) -> None`

**Purpose:** Main orchestrator for config-driven execution.

**Assumptions:** Config has already been validated.

**Algorithm:**

```
1. Extract config values
   - output_dir = config['output_dir']
   - reference_dataset = config.get('reference_dataset')
   - max_workers = config.get('max_workers')
   - datasets = config['datasets']

2. Determine worker count
   If max_workers is None:
     max_workers = max(1, os.cpu_count() // 2)
     logger.info(f"Auto-detected max_workers: {max_workers} (half of {os.cpu_count()} cores)")
   Else:
     logger.info(f"Using configured max_workers: {max_workers}")

3. Log analysis start
   logger.info("Starting word frequency analysis from config")

4. PHASE 1: Build reference (if cross-dataset mode)
   If reference_dataset is not None:
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
   Else:
     # Independent mode
     logger.info("Independent mode: each dataset will use own unigrams as reference")
     ref_words = None
     is_independent_mode = True

5. PHASE 2: Process each dataset
   For each dataset in datasets:
     ds_name = dataset['name']
     manifest_csv = dataset['manifest_csv']
     file_col = dataset['file_col']
     group_by_lob = dataset.get('group_by_lob')
     group_by_dataset = dataset.get('group_by_dataset')
     
     Try:
       manifest_df = pd.read_csv(manifest_csv)
       logger.info(f"Processing dataset: {ds_name} ({len(manifest_df)} files in manifest)")
       
       # Apply grouping logic (see Grouping Logic section)
       process_dataset_with_grouping(
         ds_name, manifest_df, file_col, 
         group_by_lob, group_by_dataset,
         ref_words, is_independent_mode,
         max_workers, output_dir
       )
     
     Except Exception as e:
       logger.error(f"Failed to process dataset '{ds_name}': {e}")
       continue  # Don't let one dataset failure stop others

6. PHASE 3: Summary
   logger.info("Analysis complete")
   # Log summary of outputs created
```

**Helper function:** `process_dataset_with_grouping()` handles the 4 grouping cases (see next section).

---

### 4. `main()` - CLI Entry Point

**Purpose:** Parse command-line arguments, orchestrate config loading/validation/execution.

**Implementation:**
```python
import argparse
import sys

def main():
    """CLI entry point for config-driven word frequency analysis."""
    parser = argparse.ArgumentParser(
        description='Generate word frequency analysis from phrase reco files using YAML configuration.'
    )
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config_word_frequency.yaml',
        help='Path to YAML config file (default: config_word_frequency.yaml)'
    )
    args = parser.parse_args()
    
    # Check config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        print("\nCreate a config file or specify one with --config", file=sys.stderr)
        print("\nExample config structure:", file=sys.stderr)
        print("output_dir: \"./outputs\"", file=sys.stderr)
        print("reference_dataset: \"DEV\"  # or null for independent mode", file=sys.stderr)
        print("max_workers: null  # auto-detect", file=sys.stderr)
        print("datasets:", file=sys.stderr)
        print("  - name: \"DEV\"", file=sys.stderr)
        print("    manifest_csv: \"./files.csv\"", file=sys.stderr)
        print("    file_col: \"File\"", file=sys.stderr)
        sys.exit(1)
    
    # Load config
    try:
        config = load_config(str(config_path))
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Validate config
    errors = validate_config(config)
    if errors:
        print("Configuration validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
    
    # Run analysis
    try:
        run_from_config(config)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"Analysis failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Command-line usage:**
```bash
# Use default config
python word_frequency_analysis.py

# Specify custom config
python word_frequency_analysis.py --config my_analysis.yaml
python word_frequency_analysis.py -c my_analysis.yaml

# Help
python word_frequency_analysis.py --help
```

**VSCode integration:**
- User clicks "Run Python File" button → uses default `config_word_frequency.yaml`
- No command-line configuration needed for simple case

## Grouping Logic Implementation

### Helper Function: `process_dataset_with_grouping()`

```python
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
```

### Helper Function: `process_single_group()`

```python
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
```

## Error Handling Strategy

### Validation Phase (Fail-Fast)

**Philosophy:** Catch all configuration and setup errors BEFORE processing starts. Exit immediately with clear error messages.

**Errors that stop execution:**
- Missing or empty config file
- Invalid YAML syntax
- Missing required fields
- Invalid data types
- Missing manifest files
- Reference dataset doesn't exist in datasets list
- Missing columns in manifest CSV
- Invalid worker count
- Output directory doesn't exist (and can't be created)

**Error message format:**
```
Configuration validation failed:
  - reference_dataset 'DEV' not found in datasets list. Available: ['Training', 'Test']
  - Dataset 'Training': manifest CSV not found: ./missing.csv
  - Dataset 'Test': column 'LineOfBusiness' not found in manifest CSV
  - max_workers must be >= 1, got: 0
```

User sees complete list of issues, can fix all at once.

### Processing Phase (Continue-on-Error)

**Philosophy:** Don't let individual file failures stop the entire analysis. Log errors, continue processing, report summary at end.

**Individual file failures:**
- Corrupted phrase reco files
- Missing files referenced in manifest
- Pandas read errors
- Malformed CSV structure

**Implementation:** Add error handling to `get_transcript_unigrams()`:

```python
def get_transcript_unigrams(file_path: str) -> Iterable[str]:
    """Extract unigrams from single transcript.
    
    Returns empty list on error (logged, not raised).
    """
    try:
        tscript = pd.read_csv(file_path, sep='\t', header=None, 
                             names=['Nxpr', 'Channel', 'Type', 'Phrase', 
                                   'StartCS', 'EndCS', 'Score'])
        words = list(tscript[tscript['Type']=='T']['Phrase'])
        return words
    except Exception as e:
        logger.warning(f"Failed to read {file_path}: {e}")
        return []  # Return empty, don't crash
```

**Dataset-level failures:**
- Entire dataset processing wrapped in try/except in `run_from_config()`
- Log error with dataset name
- Continue to next dataset
- Don't let one dataset failure stop others

**Parallel processing failures:**
- ProcessPoolExecutor handles individual task failures
- Failed tasks return empty lists
- Processing continues with successful tasks

### Summary Reporting

At the end of `run_from_config()`, log summary:

```python
logger.info("Analysis complete")
logger.info(f"Datasets processed: {datasets_success}/{datasets_total}")
logger.info(f"Output files created: {output_count}")
logger.info(f"Check log file for details: citi_mrm_tools.log")
```

Example output:
```
2026-06-08 14:30:45 | citi_mrm_tools | Analysis complete
2026-06-08 14:30:45 | citi_mrm_tools | Datasets processed: 2/3 (1 failed)
2026-06-08 14:30:45 | citi_mrm_tools | Output files created: 8
2026-06-08 14:30:45 | citi_mrm_tools | Check log file for details: citi_mrm_tools.log
```

## Template Config File

**File:** `config_word_frequency.yaml`

```yaml
# Word Frequency Analysis Configuration
#
# Generates word frequency analysis (unigram counts and percentages) from phrase reco files.
#
# Run: python word_frequency_analysis.py
#
# Required fields:
#   - output_dir: Directory for output CSV files
#   - datasets: List of at least one dataset to analyze
#
# Per-dataset required fields:
#   - name: Dataset label (used in output filenames)
#   - manifest_csv: Path to CSV file containing phrase reco file paths
#   - file_col: Column name in manifest CSV with file paths
#
# Optional top-level fields:
#   - reference_dataset: Dataset name to use as reference for all analyses
#                       Set to null (or omit) for independent mode (each dataset self-references)
#   - max_workers: Number of parallel workers for processing
#                 Set to null (or omit) to auto-detect (uses half of CPU cores)
#
# Optional per-dataset grouping fields:
#   - group_by_lob: Column name for Line of Business grouping
#   - group_by_dataset: Column name for DEV/VAL dataset grouping
#
# Analysis Modes:
#   CROSS-DATASET: Specify reference_dataset
#     - One dataset provides the reference vocabulary
#     - All datasets analyzed against that same vocabulary
#     - Use case: Compare how training vocabulary appears in validation/test sets
#
#   INDEPENDENT: Set reference_dataset to null or omit
#     - Each dataset uses its own vocabulary as reference
#     - Completely independent analyses
#     - Use case: Separate frequency analyses for unrelated datasets
#
# Grouping Behavior:
#   - No grouping: Single output per dataset
#   - LOB only: Creates {name}_combined + one file per LOB value
#   - Dataset only: One file per dataset value (no combined)
#   - Both: Creates {name}_{dataset}_combined + {name}_{dataset}_{lob} for each combination

# Output directory for all CSV files
output_dir: "./outputs"

# Reference dataset for cross-dataset analysis (or null for independent mode)
# If specified, this dataset's vocabulary is used as the reference for all analyses
reference_dataset: "DEV"  # Change to null for independent mode

# Worker count for parallel processing (null = auto-detect as half of CPU cores)
max_workers: null

# List of datasets to analyze
datasets:
  # Example 1: Simple analysis (no grouping)
  - name: "DEV"
    manifest_csv: "./data/dev_files.csv"
    file_col: "File"

  # Example 2: LOB grouping (commented out)
  # Creates: ITV_combined, ITV_Commercial, ITV_Retail
  #
  # - name: "ITV"
  #   manifest_csv: "./data/itv_files.csv"
  #   file_col: "File"
  #   group_by_lob: "LineOfBusiness"

  # Example 3: Both LOB and Dataset grouping (commented out)
  # Creates: Q1_DEV_combined, Q1_DEV_Commercial, Q1_DEV_Retail,
  #          Q1_VAL_combined, Q1_VAL_Commercial, Q1_VAL_Retail
  #
  # - name: "Q1_Analysis"
  #   manifest_csv: "./data/q1_files.csv"
  #   file_col: "File"
  #   group_by_lob: "LineOfBusiness"
  #   group_by_dataset: "DatasetType"
```

## Backward Compatibility

### Unchanged Components

**Functions that remain 100% unchanged:**
- `_setup_logger()` - Logging infrastructure
- `get_dataset_unigrams()` - Extract unigrams from dataset (parallel)
- `cnt_unigrams()` - Count single word occurrences
- `word_freq()` - Generate frequency CSV

**Modified Components:**
- `get_transcript_unigrams()` - Add try/except error handling (return empty list on error)
- `if __name__ == "__main__"` block - Replace example code with `main()` call

### Programmatic API Still Works

Existing notebooks or scripts that import and call functions directly will continue to work unchanged:

```python
# This still works exactly as before
from word_frequency_analysis import get_dataset_unigrams, word_freq
import glob

# Get file paths
files = glob.glob("./data/*.zip")

# Extract unigrams
words = get_dataset_unigrams(files, max_workers=4, dataset_name='MyData')

# Build reference
ref_words = list(set(words))

# Generate frequency analysis
word_freq(ref_words, words, 4, 'MyData', './outputs')
```

**Why backward compatibility matters:**
- Existing analysis notebooks can continue running
- No need to migrate existing workflows
- Config-driven interface is additive, not a replacement

## Dependencies

**No new dependencies needed** - PyYAML was already added in tpr_fpr_curve refactor.

**Existing dependencies from requirements.txt:**
- pandas, numpy (data processing)
- tqdm (progress bars)
- concurrent.futures (parallel processing)
- collections.Counter (word counting)
- PyYAML (config loading)
- Standard library: logging, pathlib, glob, datetime, typing, argparse, sys, os

**Python 3.7 compatibility:**
- Use `typing.List` instead of built-in `list` type hint
- Use `typing.Iterable` instead of `collections.abc.Iterable`
- No f-strings in type hints
- No assignment expressions (`:=`)
- No structural pattern matching
- All dependencies already Python 3.7 compatible

## Testing Strategy

### Manual Validation Testing

**Test `validate_config()` with:**
1. Valid config (all fields correct) → no errors
2. Missing `output_dir` → error
3. Missing `datasets` → error
4. Empty datasets list → error
5. Invalid `max_workers` (0, negative, non-integer) → error
6. Missing manifest file → error
7. Reference dataset doesn't exist → error with available list
8. Missing `file_col` in manifest → error
9. Missing `group_by_lob` column in manifest → error
10. Duplicate dataset names → error
11. Empty manifest CSV (no data rows) → error

### Integration Testing Scenarios

**Test complete workflow:**

1. **Simple case:** Single dataset, no grouping, independent mode
   - Verify: Single output file, uses own unigrams as reference

2. **Cross-dataset:** DEV as reference, ITV analyzed against it
   - Verify: Both outputs have same unigram vocabulary, different counts

3. **LOB grouping only:** Creates combined + per-LOB files
   - Verify: N+1 files (1 combined + N per LOB), all use same reference

4. **Dataset grouping only:** Creates per-dataset files (no combined)
   - Verify: N files (one per dataset value), no combined file

5. **Both groupings:** Creates nested structure
   - Verify: M * (N+1) files (for M dataset values, N LOBs per dataset)

6. **Auto-detect workers:** Config has `max_workers: null`
   - Verify: Log shows auto-detected value (half of cores)

7. **Error scenarios:**
   - Corrupted phrase reco file → logged, processing continues
   - Dataset failure → logged, next dataset processes
   - Invalid config → fails fast with clear errors

### Validation Commands

```bash
# Python 3.7 syntax check
python -m py_compile word_frequency_analysis.py

# Python 3.7 compatibility check
grep -n ":=" word_frequency_analysis.py  # Should find nothing (no walrus)
grep -n "list\[" word_frequency_analysis.py  # Should find nothing (no built-in generics)

# Import test
python -c "from word_frequency_analysis import load_config, validate_config, run_from_config, main; print('PASS: All imports successful')"

# Backward compatibility test
python -c "from word_frequency_analysis import get_dataset_unigrams, word_freq; print('PASS: Programmatic API still works')"
```

### Test Data Needs

**Minimal test data:**
- Sample manifest CSV with File, LineOfBusiness, DatasetType columns
- 4-6 small phrase reco files (.csv.zip format) for quick testing
- One intentionally corrupted file (test error handling)

**Can reuse existing project data if available**

## Success Criteria

### Functionality Checklist

- [ ] Config file `config_word_frequency.yaml` exists with inline documentation
- [ ] User can run `python word_frequency_analysis.py` (uses default config)
- [ ] User can run `python word_frequency_analysis.py --config custom.yaml`
- [ ] Cross-dataset mode works (shared reference from specified dataset)
- [ ] Independent mode works (each dataset self-references)
- [ ] Case 1 grouping works: No grouping → single output
- [ ] Case 2 grouping works: LOB only → combined + per-LOB files
- [ ] Case 3 grouping works: Dataset only → per-dataset files (no combined)
- [ ] Case 4 grouping works: Both → nested structure with combined per dataset value
- [ ] Auto-detect worker count works (half of cores when null)
- [ ] Explicit worker count works (uses specified value)
- [ ] Validation catches all config errors before processing
- [ ] Individual file errors don't crash analysis (logged, continue)
- [ ] Dataset errors don't crash analysis (logged, continue to next)
- [ ] Summary reports success/failure counts

### Backward Compatibility Checklist

- [ ] Existing functions unchanged (can still import/use programmatically)
- [ ] `get_transcript_unigrams()` returns empty list on error (not raises)
- [ ] Python 3.7 compatible (no 3.8+ syntax)
- [ ] No new dependencies (PyYAML already available)

### User Experience Checklist

- [ ] Clear error messages with dataset context
- [ ] Reference dataset validation with available list
- [ ] Progress logged to `citi_mrm_tools.log`
- [ ] Summary shows datasets processed, files created
- [ ] Consistent UX with word_statistics.py and tpr_fpr_curve.py
- [ ] Help message shows usage: `python word_frequency_analysis.py --help`
- [ ] VSCode "Run" button works with default config

### Documentation Checklist

- [ ] PROJECT_DOCUMENTATION.md updated with config-driven usage
- [ ] Config template has comprehensive inline documentation
- [ ] Usage examples clear (cross-dataset vs independent)
- [ ] Grouping behavior documented with examples
- [ ] Phase 2 marked complete in roadmap

## Implementation Notes

### Code Organization

- Add new functions at bottom of file, before `if __name__ == "__main__"` block
- Keep imports grouped: stdlib, third-party, local
- yaml import already present (verify or add if needed)
- Add argparse, sys, os imports
- Modify `if __name__ == "__main__"` block to call `main()` instead of inline example

### Python 3.7 Compatibility

- Use `typing.List` instead of `list[str]`
- Use `typing.Iterable` instead of `collections.abc.Iterable`
- Use `typing.Optional` instead of `X | None`
- No assignment expressions (`:=`)
- No f-strings in type hints
- All dependencies already Python 3.7 compatible

### Logging

- Reuse existing `logger` instance (already configured)
- Add new log statements following existing format
- No changes to logging configuration
- Log key events:
  - Analysis start
  - Mode (cross-dataset vs independent)
  - Reference building (cross-dataset mode)
  - Dataset processing start
  - Grouping strategy
  - Each output file creation
  - Errors (warning for files, error for datasets)
  - Analysis complete summary

### Worker Count Auto-Detection

```python
import os

max_workers = config.get('max_workers')
if max_workers is None:
    max_workers = max(1, os.cpu_count() // 2)
    logger.info(f"Auto-detected max_workers: {max_workers} (half of {os.cpu_count()} cores)")
else:
    logger.info(f"Using configured max_workers: {max_workers}")
```

**Safety:** Uses half of cores to leave headroom for:
- OS operations
- Other user tasks (browser, email, etc.)
- Other corporate services on shared servers
- Memory-intensive pandas operations

## Timeline Estimate

**Implementation:** 3-4 hours
- Add new functions (load_config, validate_config, run_from_config, main): 1.5 hours
- Implement grouping logic (helper functions): 1 hour
- Add error handling to get_transcript_unigrams: 15 minutes
- Create template config: 30 minutes
- Testing and refinement: 1 hour

**Risk:** Low - Additive changes only, following proven pattern from word_statistics.py

## Future Enhancements (Out of Scope)

- Shared config infrastructure across all three scripts (extract common code)
- Progress bars for long-running analyses (already has tqdm in parallel tasks)
- Combined output CSV with all datasets side-by-side
- HTML report generation
- UI integration (Phase 3 of project)
- Parallel dataset processing (currently sequential)
- Sort output by frequency (current code does this in example, consider making configurable)
