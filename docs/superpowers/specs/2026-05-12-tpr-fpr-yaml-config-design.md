# TPR vs FPR YAML Config Refactor - Design Specification

**Date:** 2026-05-12  
**Author:** Claude (Superpowers Brainstorming)  
**Status:** Approved

## Overview

Refactor `tpr_fpr_curve.py` to support YAML configuration-driven execution. This enables non-technical users to generate ROC curves by modifying a config file and clicking run, rather than writing Python code. This is a key step toward building a UI tool for automated MRM report generation.

## Goals

1. **Config-driven execution:** Users specify datasets, column mappings, and outputs in YAML
2. **Multi-dataset support:** Process multiple datasets in a single run
3. **Stratification support:** Split analyses by group column (e.g., Line of Business)
4. **Validation-first:** Catch all configuration and data errors before processing
5. **Backward compatibility:** Keep existing function API for programmatic/notebook use
6. **VSCode-friendly:** Click "Run" button or use command line

## Design Approach

**Strategy:** Minimal refactor - add config layer on top of existing function.

- Keep `recall_vs_fpr_curve()` unchanged (library API)
- Add new functions for config loading, validation, and orchestration
- Add CLI with argparse for config file specification
- Maintain single-file structure (no module decomposition)

## File Structure

### Modified Files

**`tpr_fpr_curve.py`** - Add ~150 lines:
- `load_config(config_path: str) -> dict`
- `validate_config(config: dict) -> List[str]`
- `run_from_config(config: dict) -> None`
- `main()` with argparse

**`requirements.txt`** - Add dependency:
- `PyYAML>=5.4,<6.0` (Python 3.7 compatible)

### New Files

**`config_tpr_v_fpr.yaml`** - Template config with inline documentation

## YAML Config Structure

### Schema

```yaml
# Required top-level keys
output_dir: string          # Path to output directory for plots

datasets: list              # List of dataset configurations (min 1)
  - csv_path: string        # Required: Path to CSV file
    name: string            # Required: Dataset label for plots/filenames
    pred_col: string        # Required: Column name for predictions
    truth_col: string       # Required: Column name for ground truth
    score_col: string       # Required: Column name for model scores
    group_by: string        # Optional: Column name to stratify by
```

### Example Config

```yaml
output_dir: "./outputs"

datasets:
  - csv_path: "./dummy_multiclass_predictions.csv"
    name: "Test"
    pred_col: "ModelPrediction"
    truth_col: "TrueValue"
    score_col: "PredictionScore"
    # group_by: "LineOfBusiness"  # Optional stratification

  - csv_path: "./validation_predictions.csv"
    name: "Validation"
    pred_col: "ModelPrediction"
    truth_col: "TrueValue"
    score_col: "PredictionScore"
    group_by: "LineOfBusiness"  # Will create separate plots per LoB
```

### Stratification Behavior

When `group_by` is specified:
- DataFrame is split by unique values in the specified column
- Each group gets its own ROC curve
- Output naming: `tpr_v_fpr_{name}_{group_value}.png`

**Example:**
- `name: "Test"`
- `group_by: "LineOfBusiness"`
- Values: `["Commercial", "Retail"]`
- Outputs: `tpr_v_fpr_Test_Commercial.png`, `tpr_v_fpr_Test_Retail.png`

## Component Specifications

### 1. `load_config(config_path: str) -> dict`

**Purpose:** Load and parse YAML config file.

**Implementation:**
```python
import yaml

def load_config(config_path: str) -> dict:
    """Load YAML configuration file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config
```

**Error handling:**
- `FileNotFoundError` → re-raise with helpful message
- `yaml.YAMLError` → re-raise with parse error details

### 2. `validate_config(config: dict) -> List[str]`

**Purpose:** Validate configuration structure and data availability. Returns list of error messages (empty if valid).

**Validation checks (in order):**

1. **Top-level structure**
   - `output_dir` exists and is non-empty string
   - `datasets` exists and is non-empty list

2. **Per-dataset structure**
   - All required fields present: `csv_path`, `name`, `pred_col`, `truth_col`, `score_col`
   - All required fields are non-empty strings
   - `group_by` (if present) is a non-empty string

3. **File system checks**
   - Each `csv_path` file exists and is readable
   - Parent directory of `output_dir` exists (output_dir itself will be created)

4. **CSV content checks**
   - Each CSV loads successfully (valid format)
   - Required columns exist: `pred_col`, `truth_col`, `score_col` in CSV headers
   - If `group_by` specified, that column exists in CSV headers
   - CSV has at least one data row (not just headers)

5. **Name collision checks**
   - No duplicate dataset `name` values
   - When `group_by` used, check for potential `{name}_{group_value}` collisions
   - Example: Can't have `name="Test"` and `name="Test_Commercial"` if first dataset uses `group_by` that produces "Commercial" value

**Error message format:**
```
Dataset 'Test': CSV file not found: ./missing.csv
Dataset 'Validation': Missing required column 'PredictionScore'
Dataset 'Test': group_by column 'LoB' not found in CSV
Output directory parent does not exist: /nonexistent/path
Duplicate dataset name: 'Test'
Name collision detected: 'Test_Commercial' (from stratification and explicit name)
```

**Implementation note:** Load each CSV with pandas to verify structure, but don't keep in memory (reload during processing).

### 3. `run_from_config(config: dict) -> None`

**Purpose:** Main orchestrator - processes all datasets from validated config.

**Assumptions:** Config has already been validated.

**Algorithm:**

```
1. Create output_dir if it doesn't exist
2. Log analysis start with timestamp
3. Initialize success/failure counters

4. For each dataset in config['datasets']:
   a. Try:
      - Load CSV into DataFrame
      - If group_by NOT specified:
        * Call recall_vs_fpr_curve(df, ..., dataset_name=name, save_dir=output_dir)
      - If group_by IS specified:
        * Get unique values from group_by column
        * Sort values for consistent ordering
        * Log: "Found N groups: value1, value2, ..."
        * For each group_value:
          - Filter DataFrame: df[df[group_by] == group_value]
          - Call recall_vs_fpr_curve(df_filtered, ..., 
                                     dataset_name=f"{name}_{group_value}", 
                                     save_dir=output_dir)
   b. Except Exception as e:
      - Log error: f"Failed to process dataset '{name}': {e}"
      - Increment failure counter
      - Continue to next dataset
   c. Else:
      - Increment success counter

5. Log summary: "Analysis complete: {success}/{total} datasets processed successfully"
6. If any failures, exit with code 1, otherwise exit with code 0
```

**Logging behavior:**
- One log entry per major step (load CSV, found N groups, plotting, saving, etc.)
- Existing `recall_vs_fpr_curve()` function already logs appropriately
- Summary at end shows success/failure counts

**Example log output (without group_by):**
```
2026-05-12 15:30:00 | citi_mrm_tools | Starting ROC analysis from config
2026-05-12 15:30:00 | citi_mrm_tools | Processing dataset: Test
2026-05-12 15:30:01 | citi_mrm_tools | Loaded CSV from ./dummy_multiclass_predictions.csv
2026-05-12 15:30:01 | citi_mrm_tools | Plotting TPR v FPR
2026-05-12 15:30:01 | citi_mrm_tools | Saved ROC plot to outputs/tpr_v_fpr_Test.png
2026-05-12 15:30:01 | citi_mrm_tools | dataset=Test | rows=100 | auc=0.850000
2026-05-12 15:30:01 | citi_mrm_tools | Analysis complete: 1/1 datasets processed successfully
```

**Example log output (with group_by):**
```
2026-05-12 15:30:00 | citi_mrm_tools | Processing dataset: Test (grouped by LineOfBusiness)
2026-05-12 15:30:00 | citi_mrm_tools | Found 2 groups: Commercial, Retail
2026-05-12 15:30:00 | citi_mrm_tools | Processing group: Test_Commercial (45 rows)
2026-05-12 15:30:01 | citi_mrm_tools | Saved ROC plot to outputs/tpr_v_fpr_Test_Commercial.png
2026-05-12 15:30:01 | citi_mrm_tools | dataset=Test_Commercial | rows=45 | auc=0.820000
2026-05-12 15:30:01 | citi_mrm_tools | Processing group: Test_Retail (55 rows)
2026-05-12 15:30:02 | citi_mrm_tools | Saved ROC plot to outputs/tpr_v_fpr_Test_Retail.png
2026-05-12 15:30:02 | citi_mrm_tools | dataset=Test_Retail | rows=55 | auc=0.880000
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
        description='Generate TPR vs FPR (ROC) curves from model predictions using YAML configuration.'
    )
    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config_tpr_v_fpr.yaml',
        help='Path to YAML config file (default: config_tpr_v_fpr.yaml)'
    )
    args = parser.parse_args()
    
    # Check config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        print("\nCreate a config file or specify one with --config", file=sys.stderr)
        print("\nExample config structure:", file=sys.stderr)
        print("output_dir: \"./outputs\"", file=sys.stderr)
        print("datasets:", file=sys.stderr)
        print("  - csv_path: \"./predictions.csv\"", file=sys.stderr)
        print("    name: \"Test\"", file=sys.stderr)
        print("    pred_col: \"ModelPrediction\"", file=sys.stderr)
        print("    truth_col: \"TrueValue\"", file=sys.stderr)
        print("    score_col: \"PredictionScore\"", file=sys.stderr)
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
python tpr_fpr_curve.py

# Specify custom config
python tpr_fpr_curve.py --config my_analysis.yaml
python tpr_fpr_curve.py -c my_analysis.yaml

# Help
python tpr_fpr_curve.py --help
```

**VSCode integration:**
- User clicks "Run Python File" button → uses default `config_tpr_v_fpr.yaml`
- No command-line configuration needed for simple case

## Template Config File

**File:** `config_tpr_v_fpr.yaml`

```yaml
# TPR vs FPR (ROC Curve) Analysis Configuration
# 
# This config file drives automated ROC curve generation.
# Modify the settings below and run: python tpr_fpr_curve.py
#
# Required fields:
#   - output_dir: Directory where plots will be saved
#   - datasets: List of at least one dataset to analyze
#
# Per-dataset required fields:
#   - csv_path: Path to CSV file with predictions
#   - name: Label for this dataset (used in plot titles and filenames)
#   - pred_col: Column name containing model predictions
#   - truth_col: Column name containing ground truth labels
#   - score_col: Column name containing model confidence scores
#
# Optional per-dataset fields:
#   - group_by: Column name to stratify analysis (e.g., "LineOfBusiness")
#               Creates separate plots for each unique value in this column

# Output directory for all generated plots
output_dir: "./outputs"

# List of datasets to analyze
datasets:
  # Example 1: Simple analysis of one dataset
  - csv_path: "./dummy_multiclass_predictions.csv"
    name: "Test"
    pred_col: "ModelPrediction"
    truth_col: "TrueValue"
    score_col: "PredictionScore"

  # Example 2: Analysis stratified by Line of Business (commented out)
  # Uncomment and modify to add more datasets
  #
  # - csv_path: "./validation_predictions.csv"
  #   name: "Validation"
  #   pred_col: "ModelPrediction"
  #   truth_col: "TrueValue"
  #   score_col: "PredictionScore"
  #   group_by: "LineOfBusiness"  # Creates separate plot per LoB value
```

## Backward Compatibility

**Unchanged components:**
- `_setup_logger()` - No modifications
- `_sanitize_filename()` - No modifications
- `recall_vs_fpr_curve()` - **No modifications to function signature or behavior**

**Why:** Existing notebooks or scripts that import and call `recall_vs_fpr_curve()` directly will continue to work unchanged. The config-driven interface is additive, not a replacement.

**Example of continued programmatic use:**
```python
from tpr_fpr_curve import recall_vs_fpr_curve
import pandas as pd

df = pd.read_csv('predictions.csv')
recall_vs_fpr_curve(
    df,
    pred_col='ModelPrediction',
    truth_col='TrueValue',
    score_col='PredictionScore',
    dataset_name='MyTest',
    save_dir='./outputs'
)
```

## Dependencies

**New dependency:**
- `PyYAML>=5.4,<6.0`
  - Python 3.7 compatible
  - Stable, widely-used library (~50KB)
  - No known security issues in this version range

**Add to `requirements.txt`:**
```
# Existing dependencies remain unchanged

# YAML configuration support (added 2026-05-12)
PyYAML>=5.4,<6.0
```

## Error Handling Strategy

**Philosophy:** Fail fast with clear error messages for non-technical users.

**Validation phase (before processing):**
- All errors collected and reported at once
- Script exits with code 1 before any processing starts
- Users see complete list of what needs to be fixed

**Processing phase (during execution):**
- Continue on error - don't let one bad dataset block others
- Log each error with dataset name and specific failure reason
- Summary at end shows success/failure counts
- Exit code 1 if any failures, 0 if all succeeded

**Error message principles:**
- Include context (which dataset, which file, which column)
- Suggest fix when obvious (e.g., "Column 'Score' not found. Available columns: ...")
- Avoid technical jargon where possible

## Testing Strategy

**Manual testing (during implementation):**
1. Valid single dataset config
2. Valid multi-dataset config
3. Config with group_by (stratification)
4. Missing config file
5. Malformed YAML
6. Missing required fields
7. CSV file not found
8. Wrong column names
9. Empty CSV
10. Name collision scenarios

**Test with existing dummy data:**
- Use `dummy_multiclass_predictions.csv` as test input
- Verify plots generate correctly
- Verify logging output is readable

**Post-implementation validation:**
- Run with default config after creating template
- Verify VSCode "Run" button works
- Verify command-line `--config` flag works
- Check log file for expected output

## Success Criteria

1. ✅ User can modify `config_tpr_v_fpr.yaml` and click "Run" in VSCode
2. ✅ User can specify custom config file via command line
3. ✅ Multiple datasets process in one run
4. ✅ Stratification by group column works (e.g., Line of Business)
5. ✅ Validation catches config errors before processing
6. ✅ Existing programmatic API (`recall_vs_fpr_curve()`) unchanged
7. ✅ Clear error messages for non-technical users
8. ✅ All outputs logged to `citi_mrm_tools.log`

## Future Extensions (Out of Scope)

- Multi-class ROC curves (OvR, OvO strategies)
- Confidence intervals on ROC curves
- Additional metrics (precision-recall curves, confusion matrices)
- HTML report generation
- UI integration (next phase of project)

## Implementation Notes

**Code organization:**
- Add new functions at bottom of file, before `if __name__ == "__main__"` block
- Keep imports grouped: stdlib, third-party (pandas, numpy, sklearn, matplotlib, yaml), local
- Add PyYAML import: `import yaml`
- Add argparse import: `import argparse`
- Add sys import: `import sys`
- Modify `if __name__ == "__main__"` block to call `main()` instead of inline example

**Python 3.7 compatibility:**
- Use `typing.List` instead of built-in `list` type hint
- No f-strings in type hints
- No assignment expressions (`:=`)
- PyYAML 5.4 is compatible with Python 3.7

**Logging:**
- Reuse existing `logger` instance (already configured)
- Add new log statements follow existing format
- No changes to logging configuration

## Timeline Estimate

**Implementation:** 2-3 hours
- Add new functions: 1 hour
- Add CLI with argparse: 30 minutes
- Create template config: 30 minutes
- Testing and refinement: 1 hour

**Low risk** - Additive changes only, no refactoring of core logic.
