# Word Statistics YAML Config - Design Specification

**Date:** 2026-05-12  
**Author:** Claude (Superpowers Brainstorming)  
**Status:** Approved

## Overview

Refactor `word_statistics.py` to support YAML configuration-driven execution, following the successful pattern from `tpr_fpr_curve.py`. This enables non-technical users to generate word count statistics by modifying a config file and clicking run.

## Goals

1. **Config-driven execution:** Users specify datasets, column mappings, and grouping in YAML
2. **Multi-dataset support:** Process multiple datasets in a single run
3. **Flexible grouping:** Support LOB grouping, Dataset grouping, or both with combined rollups
4. **Validation-first:** Catch all configuration and manifest errors before processing
5. **Backward compatibility:** Keep existing function APIs for programmatic/notebook use
6. **VSCode-friendly:** Click "Run" button or use command line
7. **Consistent UX:** Match tpr_fpr_curve.py patterns for user familiarity

## Design Approach

**Strategy:** Minimal refactor - add config layer on top of existing functions.

- Keep `word_stats()` and `word_stats_by_label()` unchanged (library APIs)
- Add new functions for config loading, validation, and orchestration
- Grouping logic in orchestration layer
- Add CLI with argparse for config file specification
- Maintain single-file structure (no module decomposition)

## File Structure

### Modified Files

**`word_statistics.py`** - Add ~150-200 lines:
- `load_config(config_path: str) -> dict`
- `validate_config(config: dict) -> List[str]`
- `run_from_config(config: dict) -> None`
- `main()` with argparse

**No new dependencies** - PyYAML already added from tpr_fpr_curve refactor

### New Files

**`config_word_stats.yaml`** - Template config with inline documentation

## YAML Config Structure

### Schema

```yaml
# Required top-level keys
output_file: string          # Path to output CSV file

datasets: list               # List of dataset configurations (min 1)
  - name: string            # Required: Dataset label for output rows
    manifest_csv: string    # Required: Path to CSV with phrase reco file paths
    file_col: string        # Required: Column name containing file paths
    group_by_lob: string    # Optional: Column name for LOB grouping
    group_by_dataset: string # Optional: Column name for DEV/VAL grouping
```

### Example Config

```yaml
output_file: "./outputs/word_stats.csv"

datasets:
  # Example 1: Simple analysis (no grouping)
  - name: "Q1_Analysis"
    manifest_csv: "./data/q1_files.csv"
    file_col: "File"

  # Example 2: LOB grouping only
  - name: "Q2_Analysis"
    manifest_csv: "./data/q2_files.csv"
    file_col: "File"
    group_by_lob: "LineOfBusiness"  # Creates Q2_Analysis_Commercial, Q2_Analysis_Retail

  # Example 3: Both LOB and Dataset grouping
  - name: "Q3_Analysis"
    manifest_csv: "./data/q3_files.csv"
    file_col: "File"
    group_by_lob: "LineOfBusiness"      # Values: Commercial, Retail
    group_by_dataset: "DatasetType"     # Values: DEV, VAL
    # Creates:
    #   Q3_Analysis_DEV_combined (all DEV)
    #   Q3_Analysis_DEV_Commercial (DEV + Commercial)
    #   Q3_Analysis_DEV_Retail (DEV + Retail)
    #   Q3_Analysis_VAL_combined (all VAL)
    #   Q3_Analysis_VAL_Commercial (VAL + Commercial)
    #   Q3_Analysis_VAL_Retail (VAL + Retail)
```

### Grouping Behavior Matrix

| group_by_lob | group_by_dataset | Output Rows Created |
|--------------|------------------|---------------------|
| Not specified | Not specified | `{name}` - Single combined output |
| Specified | Not specified | `{name}_{lob}` - One row per LOB value |
| Not specified | Specified | `{name}_{dataset}` - One row per dataset value |
| Both specified | Both specified | `{name}_{dataset}_combined` + `{name}_{dataset}_{lob}` |

**Important:** When both groupings are specified, we create:
- One "combined" row per dataset value (all LOBs together)
- Individual rows for each LOB within each dataset value
- **No combined across different dataset values** (e.g., no row combining DEV+VAL)

**Example with both groupings:**
- Input manifest has: LOB=[Commercial, Retail], DatasetType=[DEV, VAL]
- Output rows (6 total):
  1. `Analysis_DEV_combined` - All DEV records
  2. `Analysis_DEV_Commercial` - DEV Commercial only
  3. `Analysis_DEV_Retail` - DEV Retail only
  4. `Analysis_VAL_combined` - All VAL records
  5. `Analysis_VAL_Commercial` - VAL Commercial only
  6. `Analysis_VAL_Retail` - VAL Retail only

## Component Specifications

### 1. `load_config(config_path: str) -> dict`

**Purpose:** Load and parse YAML config file.

**Implementation:**
```python
import yaml

def load_config(config_path: str) -> dict:
    """Load YAML configuration file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_path}")
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML config: {e}")
```

**Error handling:**
- `FileNotFoundError` → re-raise with helpful message
- `yaml.YAMLError` → re-raise with parse error details

### 2. `validate_config(config: dict) -> List[str]`

**Purpose:** Validate configuration structure and manifest availability. Returns list of error messages (empty if valid).

**Validation checks (in order):**

1. **Top-level structure**
   - `output_file` exists and is non-empty string
   - `datasets` exists and is non-empty list

2. **Per-dataset structure**
   - Required fields present: `name`, `manifest_csv`, `file_col`
   - All required fields are non-empty strings
   - `group_by_lob` (if present) is a non-empty string
   - `group_by_dataset` (if present) is a non-empty string

3. **File system checks**
   - Each `manifest_csv` file exists and is readable
   - Parent directory of `output_file` exists (output_file itself will be created)

4. **Manifest CSV content checks**
   - Each manifest CSV loads successfully (valid format)
   - `file_col` column exists in manifest CSV
   - If `group_by_lob` specified, that column exists in manifest
   - If `group_by_dataset` specified, that column exists in manifest
   - Manifest has at least one data row (not just headers)

5. **Name collision checks**
   - No duplicate dataset `name` values
   - When grouping used, check for potential output name collisions between datasets

**Important:** We do NOT validate that individual phrase reco files exist. Per the design decision (continue on error), we only validate the manifest CSV itself. Missing or corrupt phrase reco files will be handled during processing by `get_word_count()` (returns 0).

**Error message format:**
```
Dataset 'Q1_Analysis': manifest CSV not found: ./missing.csv
Dataset 'Q2_Analysis': column 'File' not found in manifest CSV
Dataset 'Q2_Analysis': group_by_lob column 'LineOfBusiness' not found
Dataset 'Q3_Analysis': group_by_dataset column 'DatasetType' not found
Output file parent does not exist: /nonexistent/path
Duplicate dataset name: 'Q1_Analysis'
```

**Implementation note:** Load each manifest CSV with pandas to verify structure, but don't keep in memory (reload during processing).

### 3. `run_from_config(config: dict) -> None`

**Purpose:** Main orchestrator - processes all datasets from validated config with grouping logic.

**Assumptions:** Config has already been validated.

**Algorithm:**

```
1. Initialize empty list to collect all stat DataFrames: all_stats = []
2. Log analysis start with timestamp

3. For each dataset in config['datasets']:
   ds_name = dataset['name']
   manifest_csv = dataset['manifest_csv']
   file_col = dataset['file_col']
   group_by_lob = dataset.get('group_by_lob')
   group_by_dataset = dataset.get('group_by_dataset')
   
   Try:
      a. Load manifest CSV into DataFrame
      b. Log: "Processing dataset: {ds_name}"
      
      c. Determine grouping strategy:
      
      # Case 1: No grouping
      If (not group_by_lob) and (not group_by_dataset):
         - Log: "No grouping specified"
         - result = word_stats([({ds_name}, manifest_df)], file_col, temp_output)
         - Append result to all_stats
      
      # Case 2: LOB grouping only
      Elif group_by_lob and (not group_by_dataset):
         - lob_values = sorted(manifest_df[group_by_lob].unique())
         - Log: "Grouping by LOB: {len(lob_values)} groups: {lob_values}"
         - For each lob_value in lob_values:
            * df_lob = manifest_df[manifest_df[group_by_lob] == lob_value]
            * row_name = f"{ds_name}_{lob_value}"
            * Log: "Processing {row_name} ({len(df_lob)} files)"
            * result = word_stats([(row_name, df_lob)], file_col, temp_output)
            * Append result to all_stats
      
      # Case 3: Dataset grouping only
      Elif (not group_by_lob) and group_by_dataset:
         - dataset_values = sorted(manifest_df[group_by_dataset].unique())
         - Log: "Grouping by dataset: {len(dataset_values)} groups: {dataset_values}"
         - For each dataset_value in dataset_values:
            * df_dataset = manifest_df[manifest_df[group_by_dataset] == dataset_value]
            * row_name = f"{ds_name}_{dataset_value}"
            * Log: "Processing {row_name} ({len(df_dataset)} files)"
            * result = word_stats([(row_name, df_dataset)], file_col, temp_output)
            * Append result to all_stats
      
      # Case 4: Both LOB and Dataset grouping
      Else: # both group_by_lob and group_by_dataset
         - dataset_values = sorted(manifest_df[group_by_dataset].unique())
         - Log: "Grouping by both LOB and dataset"
         - Log: "Found {len(dataset_values)} dataset values: {dataset_values}"
         - For each dataset_value in dataset_values:
            * df_dataset = manifest_df[manifest_df[group_by_dataset] == dataset_value]
            * Log: "Processing {ds_name}_{dataset_value} ({len(df_dataset)} files)"
            
            # Create combined for this dataset
            * combined_name = f"{ds_name}_{dataset_value}_combined"
            * Log: "Creating {combined_name}"
            * result = word_stats([(combined_name, df_dataset)], file_col, temp_output)
            * Append result to all_stats
            
            # Create individual LOB splits within this dataset
            * lob_values = sorted(df_dataset[group_by_lob].unique())
            * Log: "Found {len(lob_values)} LOB values: {lob_values}"
            * For each lob_value in lob_values:
               - df_lob = df_dataset[df_dataset[group_by_lob] == lob_value]
               - row_name = f"{ds_name}_{dataset_value}_{lob_value}"
               - Log: "Creating {row_name} ({len(df_lob)} files)"
               - result = word_stats([(row_name, df_lob)], file_col, temp_output)
               - Append result to all_stats
   
   Except Exception as e:
      - Log error: "Failed to process dataset '{ds_name}': {e}"
      - Continue to next dataset

4. Concatenate all collected DataFrames: final_stats = pd.concat(all_stats)
5. Save to output_file: final_stats.to_csv(output_file, sep='\t', header=True, index=True)
6. Log summary: "Analysis complete: processed {num_datasets} datasets, created {num_rows} output rows"
7. Log: "Saved to {output_file}"
```

**Notes:**
- Use `temp_output = None` or in-memory path when calling `word_stats()` since we're collecting results to save later
- Actually, better: let `word_stats()` return the DataFrame without saving, we'll save the concatenated result
- Individual phrase reco file failures are handled silently by existing `get_word_count()` (returns 0)
- Manifest loading failures are caught and logged, processing continues to next dataset

**Logging example:**
```
2026-05-12 16:00:00 | citi_mrm_tools | Starting word statistics analysis from config
2026-05-12 16:00:01 | citi_mrm_tools | Processing dataset: Q3_Analysis
2026-05-12 16:00:01 | citi_mrm_tools | Grouping by both LOB and dataset
2026-05-12 16:00:01 | citi_mrm_tools | Found 2 dataset values: DEV, VAL
2026-05-12 16:00:01 | citi_mrm_tools | Processing Q3_Analysis_DEV (45 files)
2026-05-12 16:00:01 | citi_mrm_tools | Creating Q3_Analysis_DEV_combined
2026-05-12 16:00:05 | citi_mrm_tools | Found 2 LOB values: Commercial, Retail
2026-05-12 16:00:05 | citi_mrm_tools | Creating Q3_Analysis_DEV_Commercial (25 files)
2026-05-12 16:00:10 | citi_mrm_tools | Creating Q3_Analysis_DEV_Retail (20 files)
2026-05-12 16:00:15 | citi_mrm_tools | Processing Q3_Analysis_VAL (30 files)
2026-05-12 16:00:15 | citi_mrm_tools | Creating Q3_Analysis_VAL_combined
2026-05-12 16:00:18 | citi_mrm_tools | Found 2 LOB values: Commercial, Retail
2026-05-12 16:00:18 | citi_mrm_tools | Creating Q3_Analysis_VAL_Commercial (18 files)
2026-05-12 16:00:21 | citi_mrm_tools | Creating Q3_Analysis_VAL_Retail (12 files)
2026-05-12 16:00:24 | citi_mrm_tools | Analysis complete: 1 dataset processed, 6 output rows created
2026-05-12 16:00:24 | citi_mrm_tools | Saved to ./outputs/word_stats.csv
```

### 4. `main()` - CLI Entry Point

**Purpose:** Parse command-line arguments, orchestrate config loading/validation/execution.

**Implementation:**
```python
import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description='Generate word count statistics from phrase reco files using YAML configuration.'
    )
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config_word_stats.yaml',
        help='Path to YAML config file (default: config_word_stats.yaml)'
    )
    args = parser.parse_args()
    
    # Check config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        print("\nCreate a config file or specify one with --config", file=sys.stderr)
        print("\nExample config structure:", file=sys.stderr)
        print("output_file: \"./outputs/word_stats.csv\"", file=sys.stderr)
        print("datasets:", file=sys.stderr)
        print("  - name: \"Analysis\"", file=sys.stderr)
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
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Command-line usage:**
```bash
# Use default config
python word_statistics.py

# Specify custom config
python word_statistics.py --config my_analysis.yaml
python word_statistics.py -c my_analysis.yaml

# Help
python word_statistics.py --help
```

**VSCode integration:**
- User clicks "Run Python File" button → uses default `config_word_stats.yaml`
- No command-line configuration needed for simple case

## Template Config File

**File:** `config_word_stats.yaml`

```yaml
# Word Statistics Analysis Configuration
# 
# Generates descriptive statistics (count, mean, std, min, 25%, 50%, 75%, max)
# about word counts per transcript from phrase reco files.
# 
# Run: python word_statistics.py
#
# Required fields:
#   - output_file: Path to output CSV file
#   - datasets: List of at least one dataset to analyze
#
# Per-dataset required fields:
#   - name: Dataset label (used in output row names)
#   - manifest_csv: Path to CSV file containing phrase reco file paths
#   - file_col: Column name in manifest CSV with file paths
#
# Optional per-dataset grouping fields:
#   - group_by_lob: Column name for Line of Business grouping
#   - group_by_dataset: Column name for DEV/VAL dataset grouping
#
# Grouping behavior:
#   - Neither specified: Single combined output row
#   - Only LOB: One row per LOB value
#   - Only Dataset: One row per dataset value
#   - Both: Creates dataset_combined + dataset_lob rows
#           (NO combined across different dataset values)

# Output CSV file path
output_file: "./outputs/word_stats.csv"

# List of datasets to analyze
datasets:
  # Example 1: Simple analysis (no grouping)
  - name: "Q1_Analysis"
    manifest_csv: "./data/q1_files.csv"
    file_col: "File"

  # Example 2: LOB grouping (commented out)
  # Creates: Q2_Analysis_Commercial, Q2_Analysis_Retail, etc.
  #
  # - name: "Q2_Analysis"
  #   manifest_csv: "./data/q2_files.csv"
  #   file_col: "File"
  #   group_by_lob: "LineOfBusiness"

  # Example 3: Both LOB and Dataset grouping (commented out)
  # Creates: Q3_DEV_combined, Q3_DEV_Commercial, Q3_DEV_Retail,
  #          Q3_VAL_combined, Q3_VAL_Commercial, Q3_VAL_Retail
  #
  # - name: "Q3_Analysis"
  #   manifest_csv: "./data/q3_files.csv"
  #   file_col: "File"
  #   group_by_lob: "LineOfBusiness"
  #   group_by_dataset: "DatasetType"
```

## Backward Compatibility

**Unchanged components:**
- `_setup_logger()` - No modifications
- `get_word_count()` - **No modifications** - keeps current error handling (returns 0 on failure)
- `word_stats()` - **No modifications to function signature or behavior**
- `word_stats_by_label()` - **No modifications to function signature or behavior**

**Why:** Existing notebooks or scripts that import and call these functions directly will continue to work unchanged. The config-driven interface is additive, not a replacement.

**Example of continued programmatic use:**
```python
from word_statistics import word_stats
import pandas as pd
import glob

files = glob.glob("./data/*.zip")
datasets = [('MyAnalysis', pd.DataFrame({'File': files}))]
stats = word_stats(datasets, 'File', './output.csv')
```

## Dependencies

**No new dependencies needed** - PyYAML was already added in tpr_fpr_curve refactor.

Existing dependencies from requirements.txt:
- pandas, numpy, matplotlib, logging, pathlib, glob, re, datetime

## Error Handling Strategy

**Philosophy:** Fail fast with clear error messages during validation, continue on error during processing.

**Validation phase (before processing):**
- All manifest and config errors collected and reported at once
- Script exits with code 1 before any processing starts
- Users see complete list of what needs to be fixed

**Processing phase (during execution):**
- Continue on dataset error - don't let one bad manifest block others
- Log each error with dataset name and specific failure reason
- Individual phrase reco file failures handled silently by `get_word_count()` (returns 0)
- Summary at end shows success counts
- Exit code 0 (all datasets succeed) or 1 (any dataset failed)

**Error message principles:**
- Include context (which dataset, which file, which column)
- Suggest fix when obvious
- Avoid technical jargon where possible

## Testing Strategy

**Manual testing (during implementation):**
1. Valid single dataset config (no grouping)
2. Valid config with LOB grouping only
3. Valid config with Dataset grouping only
4. Valid config with both LOB and Dataset grouping
5. Multiple datasets in one config
6. Missing config file
7. Malformed YAML
8. Missing required fields
9. Manifest CSV not found
10. Wrong column names in manifest
11. Empty manifest CSV
12. Duplicate dataset names

**Test data needs:**
- Sample manifest CSV with File, LineOfBusiness, DatasetType columns
- Can reuse phrase reco files from existing project if available

**Post-implementation validation:**
- Run with default config after creating template
- Verify VSCode "Run" button works
- Verify command-line `--config` flag works
- Check log file for expected output
- Verify output CSV has correct row structure for each grouping scenario

## Success Criteria

1. ✅ User can modify `config_word_stats.yaml` and click "Run" in VSCode
2. ✅ User can specify custom config file via command line
3. ✅ Multiple datasets process in one run
4. ✅ LOB grouping works (creates one row per LOB)
5. ✅ Dataset grouping works (creates one row per dataset value)
6. ✅ Combined grouping works (creates dataset_combined + dataset_lob rows)
7. ✅ Validation catches config errors before processing
8. ✅ Existing programmatic APIs (`word_stats`, `word_stats_by_label`) unchanged
9. ✅ Clear error messages for non-technical users
10. ✅ All outputs logged to `citi_mrm_tools.log`
11. ✅ Output CSV contains descriptive statistics with correct row names
12. ✅ Consistent UX with tpr_fpr_curve.py

## Future Extensions (Out of Scope)

- Parallel processing of datasets (currently sequential)
- Progress bars for long-running analyses
- Summary statistics report (beyond the CSV)
- Integration with word_frequency_analysis.py config
- HTML report generation
- UI integration (Phase 3 of project)

## Implementation Notes

**Code organization:**
- Add new functions at bottom of file, before `if __name__ == "__main__"` block
- Keep imports grouped: stdlib, third-party, local
- yaml import already present from existing work
- Add argparse and sys imports
- Modify `if __name__ == "__main__"` block to call `main()` instead of inline example

**Python 3.7 compatibility:**
- Use `typing.List` instead of built-in `list` type hint
- No f-strings in type hints
- No assignment expressions (`:=`)
- All dependencies already Python 3.7 compatible

**Logging:**
- Reuse existing `logger` instance (already configured)
- Add new log statements follow existing format
- No changes to logging configuration

**Working with word_stats() return value:**
- Currently `word_stats()` both saves to file and returns DataFrame
- For config-driven use, we need to collect DataFrames before saving
- Options:
  A. Pass `None` or dummy path to `word_stats()`, rely on returned DataFrame
  B. Modify `word_stats()` to make `save_path` optional
  C. Call with temp path, ignore saved file, use returned DataFrame
- **Recommendation:** Option C (least invasive) - pass temp path, use returned DataFrame, save concatenated result

## Timeline Estimate

**Implementation:** 2-3 hours
- Add new functions: 1 hour
- Add CLI with argparse: 30 minutes
- Create template config: 30 minutes
- Testing and refinement: 1 hour

**Low risk** - Additive changes only, following proven tpr_fpr_curve pattern.
