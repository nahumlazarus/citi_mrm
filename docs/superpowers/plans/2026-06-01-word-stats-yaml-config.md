# Word Statistics YAML Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add YAML configuration-driven execution to word_statistics.py following the tpr_fpr_curve.py pattern

**Architecture:** Additive refactor - add config loading, validation, and orchestration functions on top of existing word_stats() and word_stats_by_label() APIs. New main() entry point with argparse CLI. Four grouping cases handled by run_from_config().

**Tech Stack:** Python 3.7, PyYAML, pandas, argparse

**Reference Spec:** docs/superpowers/specs/2026-05-12-word-stats-yaml-config-design.md

---

## File Structure

**Modified Files:**
- `word_statistics.py` - Add ~180 lines (4 new functions + updated main block)

**New Files:**
- `config_word_stats.yaml` - Template configuration file with inline documentation

**No Changes:**
- `get_word_count()` - Unchanged
- `word_stats()` - Unchanged
- `word_stats_by_label()` - Unchanged (not used in config path but preserved)

---

### Task 1: Add load_config() Function

**Files:**
- Modify: `word_statistics.py` (add after line 89, before `if __name__`)

- [ ] **Step 1: Add yaml import at top of file**

Add after existing imports (around line 10):

```python
import yaml
```

- [ ] **Step 2: Add load_config() function**

Add before `if __name__ == "__main__":` block:

```python
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
```

- [ ] **Step 3: Test load_config() with valid YAML**

Create test file `test_config.yaml`:
```yaml
output_file: "./test.csv"
datasets:
  - name: "Test"
    manifest_csv: "./manifest.csv"
    file_col: "File"
```

Run in Python REPL:
```python
from word_statistics import load_config
config = load_config('test_config.yaml')
assert config['output_file'] == './test.csv'
assert len(config['datasets']) == 1
print("PASS: load_config() loads valid YAML")
```

Expected: Assertion passes, no errors

- [ ] **Step 4: Test load_config() with missing file**

Run in Python REPL:
```python
from word_statistics import load_config
try:
    load_config('nonexistent.yaml')
    assert False, "Should have raised FileNotFoundError"
except FileNotFoundError as e:
    assert "not found" in str(e)
    print("PASS: load_config() raises FileNotFoundError for missing file")
```

Expected: Exception caught with helpful message

- [ ] **Step 5: Commit**

```bash
git add word_statistics.py test_config.yaml
git commit -m "feat(word_stats): add load_config() function for YAML loading"
```

---

### Task 2: Add validate_config() Function

**Files:**
- Modify: `word_statistics.py` (add after load_config())

- [ ] **Step 1: Add typing import for List**

Update imports section (around line 1-10):

```python
from typing import List
```

- [ ] **Step 2: Add validate_config() function**

Add after load_config():

```python
def validate_config(config: dict) -> List[str]:
    """Validate configuration structure and file availability.
    
    Args:
        config: Dictionary from load_config()
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Check top-level structure
    if not config:
        errors.append("Config is empty")
        return errors
    
    if 'output_file' not in config or not config['output_file']:
        errors.append("Missing required field: output_file")
    
    if 'datasets' not in config:
        errors.append("Missing required field: datasets")
        return errors
    
    if not isinstance(config['datasets'], list) or len(config['datasets']) == 0:
        errors.append("datasets must be a non-empty list")
        return errors
    
    # Check output file parent directory exists
    if 'output_file' in config and config['output_file']:
        output_path = Path(config['output_file'])
        if not output_path.parent.exists():
            errors.append(f"Output file parent directory does not exist: {output_path.parent}")
    
    # Track dataset names for duplicate check
    dataset_names = []
    
    # Validate each dataset
    for idx, dataset in enumerate(config['datasets']):
        ds_name = dataset.get('name', f'dataset[{idx}]')
        
        # Check required fields
        if 'name' not in dataset or not dataset['name']:
            errors.append(f"Dataset {idx}: missing required field 'name'")
            ds_name = f'dataset[{idx}]'
        
        if 'manifest_csv' not in dataset or not dataset['manifest_csv']:
            errors.append(f"Dataset '{ds_name}': missing required field 'manifest_csv'")
            continue
        
        if 'file_col' not in dataset or not dataset['file_col']:
            errors.append(f"Dataset '{ds_name}': missing required field 'file_col'")
        
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
                if dataset['group_by_lob'] not in manifest_df.columns:
                    errors.append(f"Dataset '{ds_name}': group_by_lob column '{dataset['group_by_lob']}' not found in manifest CSV")
            
            # Check group_by_dataset column if specified
            if 'group_by_dataset' in dataset and dataset['group_by_dataset']:
                if dataset['group_by_dataset'] not in manifest_df.columns:
                    errors.append(f"Dataset '{ds_name}': group_by_dataset column '{dataset['group_by_dataset']}' not found in manifest CSV")
            
            # Check manifest has data rows
            if len(manifest_df) == 0:
                errors.append(f"Dataset '{ds_name}': manifest CSV has no data rows")
        
        except Exception as e:
            errors.append(f"Dataset '{ds_name}': failed to load manifest CSV: {e}")
        
        # Track name for duplicate check
        if 'name' in dataset:
            dataset_names.append(dataset['name'])
    
    # Check for duplicate names
    seen_names = set()
    for name in dataset_names:
        if name in seen_names:
            errors.append(f"Duplicate dataset name: '{name}'")
        seen_names.add(name)
    
    return errors
```

- [ ] **Step 3: Test validate_config() with valid config**

Update test_config.yaml to have valid manifest:
```yaml
output_file: "./outputs/test.csv"
datasets:
  - name: "Test"
    manifest_csv: "./test_manifest.csv"
    file_col: "File"
```

Create test_manifest.csv:
```csv
File,LineOfBusiness,DatasetType
/path/to/file1.csv.zip,Commercial,DEV
/path/to/file2.csv.zip,Retail,VAL
```

Run in Python REPL:
```python
from word_statistics import load_config, validate_config
config = load_config('test_config.yaml')
errors = validate_config(config)
assert errors == [], f"Expected no errors, got: {errors}"
print("PASS: validate_config() accepts valid config")
```

Expected: No validation errors

- [ ] **Step 4: Test validate_config() with missing fields**

Create bad_config.yaml:
```yaml
datasets:
  - manifest_csv: "./test.csv"
```

Run in Python REPL:
```python
from word_statistics import load_config, validate_config
config = load_config('bad_config.yaml')
errors = validate_config(config)
assert len(errors) > 0
assert any("output_file" in e for e in errors)
assert any("name" in e for e in errors)
assert any("file_col" in e for e in errors)
print(f"PASS: validate_config() caught {len(errors)} errors")
print("\n".join(errors))
```

Expected: Multiple validation errors about missing fields

- [ ] **Step 5: Test validate_config() with missing manifest file**

Create missing_manifest_config.yaml:
```yaml
output_file: "./outputs/test.csv"
datasets:
  - name: "Test"
    manifest_csv: "./nonexistent.csv"
    file_col: "File"
```

Run in Python REPL:
```python
from word_statistics import load_config, validate_config
config = load_config('missing_manifest_config.yaml')
errors = validate_config(config)
assert len(errors) > 0
assert any("not found" in e for e in errors)
print(f"PASS: validate_config() caught missing manifest: {errors[0]}")
```

Expected: Error about manifest CSV not found

- [ ] **Step 6: Commit**

```bash
git add word_statistics.py test_manifest.csv bad_config.yaml missing_manifest_config.yaml
git commit -m "feat(word_stats): add validate_config() with comprehensive validation"
```

---

### Task 3: Add run_from_config() Function

**Files:**
- Modify: `word_statistics.py` (add after validate_config())

- [ ] **Step 1: Add run_from_config() function**

Add after validate_config():

```python
def run_from_config(config: dict) -> None:
    """Execute word statistics analysis from validated config.
    
    Args:
        config: Validated configuration dictionary
        
    Note: Config must be validated before calling this function.
    """
    all_stats = []
    output_file = config['output_file']
    
    logger.info("Starting word statistics analysis from config")
    
    for dataset in config['datasets']:
        ds_name = dataset['name']
        manifest_csv = dataset['manifest_csv']
        file_col = dataset['file_col']
        group_by_lob = dataset.get('group_by_lob')
        group_by_dataset = dataset.get('group_by_dataset')
        
        try:
            # Load manifest
            manifest_df = pd.read_csv(manifest_csv)
            logger.info(f"Processing dataset: {ds_name} ({len(manifest_df)} files in manifest)")
            
            # Case 1: No grouping
            if not group_by_lob and not group_by_dataset:
                logger.info("No grouping specified - creating single combined output")
                result = word_stats([(ds_name, manifest_df)], file_col, None)
                all_stats.append(result)
            
            # Case 2: LOB grouping only
            elif group_by_lob and not group_by_dataset:
                lob_values = sorted(manifest_df[group_by_lob].unique())
                logger.info(f"Grouping by LOB: {len(lob_values)} groups: {lob_values}")
                for lob_value in lob_values:
                    df_lob = manifest_df[manifest_df[group_by_lob] == lob_value]
                    row_name = f"{ds_name}_{lob_value}"
                    logger.info(f"Processing {row_name} ({len(df_lob)} files)")
                    result = word_stats([(row_name, df_lob)], file_col, None)
                    all_stats.append(result)
            
            # Case 3: Dataset grouping only
            elif not group_by_lob and group_by_dataset:
                dataset_values = sorted(manifest_df[group_by_dataset].unique())
                logger.info(f"Grouping by dataset: {len(dataset_values)} groups: {dataset_values}")
                for dataset_value in dataset_values:
                    df_dataset = manifest_df[manifest_df[group_by_dataset] == dataset_value]
                    row_name = f"{ds_name}_{dataset_value}"
                    logger.info(f"Processing {row_name} ({len(df_dataset)} files)")
                    result = word_stats([(row_name, df_dataset)], file_col, None)
                    all_stats.append(result)
            
            # Case 4: Both LOB and Dataset grouping
            else:
                dataset_values = sorted(manifest_df[group_by_dataset].unique())
                logger.info("Grouping by both LOB and dataset")
                logger.info(f"Found {len(dataset_values)} dataset values: {dataset_values}")
                
                for dataset_value in dataset_values:
                    df_dataset = manifest_df[manifest_df[group_by_dataset] == dataset_value]
                    logger.info(f"Processing {ds_name}_{dataset_value} ({len(df_dataset)} files)")
                    
                    # Create combined for this dataset
                    combined_name = f"{ds_name}_{dataset_value}_combined"
                    logger.info(f"Creating {combined_name}")
                    result = word_stats([(combined_name, df_dataset)], file_col, None)
                    all_stats.append(result)
                    
                    # Create individual LOB splits within this dataset
                    lob_values = sorted(df_dataset[group_by_lob].unique())
                    logger.info(f"Found {len(lob_values)} LOB values: {lob_values}")
                    for lob_value in lob_values:
                        df_lob = df_dataset[df_dataset[group_by_lob] == lob_value]
                        row_name = f"{ds_name}_{dataset_value}_{lob_value}"
                        logger.info(f"Creating {row_name} ({len(df_lob)} files)")
                        result = word_stats([(row_name, df_lob)], file_col, None)
                        all_stats.append(result)
        
        except Exception as e:
            logger.error(f"Failed to process dataset '{ds_name}': {e}")
            continue
    
    # Concatenate all results and save
    if all_stats:
        final_stats = pd.concat(all_stats)
        final_stats.to_csv(output_file, sep='\t', header=True, index=True)
        logger.info(f"Analysis complete: processed {len(config['datasets'])} datasets, created {len(final_stats)} output rows")
        logger.info(f"Saved to {output_file}")
    else:
        logger.error("No statistics generated - all datasets failed")
```

- [ ] **Step 2: Fix word_stats() to handle None save_path**

Modify word_stats() function to skip save when save_path is None:

Change line 87 from:
```python
word_cnt_analysis.to_csv(save_path, sep='\t', header=True, index=True)
```

To:
```python
if save_path:
    word_cnt_analysis.to_csv(save_path, sep='\t', header=True, index=True)
```

- [ ] **Step 3: Test run_from_config() with no grouping**

Create simple_config.yaml:
```yaml
output_file: "./outputs/test_simple.csv"
datasets:
  - name: "SimpleTest"
    manifest_csv: "./test_manifest.csv"
    file_col: "File"
```

Ensure test_manifest.csv has valid phrase reco file paths (or files that return 0 from get_word_count).

Run:
```bash
mkdir -p outputs
python -c "
from word_statistics import load_config, validate_config, run_from_config
config = load_config('simple_config.yaml')
errors = validate_config(config)
assert errors == [], f'Validation errors: {errors}'
run_from_config(config)
print('PASS: run_from_config() executed with no grouping')
"
```

Expected: Creates outputs/test_simple.csv with one row labeled "SimpleTest"

- [ ] **Step 4: Test run_from_config() with LOB grouping**

Create lob_config.yaml:
```yaml
output_file: "./outputs/test_lob.csv"
datasets:
  - name: "LOBTest"
    manifest_csv: "./test_manifest.csv"
    file_col: "File"
    group_by_lob: "LineOfBusiness"
```

Run:
```bash
python -c "
from word_statistics import load_config, validate_config, run_from_config
config = load_config('lob_config.yaml')
errors = validate_config(config)
assert errors == [], f'Validation errors: {errors}'
run_from_config(config)
print('PASS: run_from_config() executed with LOB grouping')
"
```

Expected: Creates outputs/test_lob.csv with rows "LOBTest_Commercial" and "LOBTest_Retail"

- [ ] **Step 5: Test run_from_config() with both groupings**

Create both_config.yaml:
```yaml
output_file: "./outputs/test_both.csv"
datasets:
  - name: "BothTest"
    manifest_csv: "./test_manifest.csv"
    file_col: "File"
    group_by_lob: "LineOfBusiness"
    group_by_dataset: "DatasetType"
```

Run:
```bash
python -c "
from word_statistics import load_config, validate_config, run_from_config
config = load_config('both_config.yaml')
errors = validate_config(config)
assert errors == [], f'Validation errors: {errors}'
run_from_config(config)
import pandas as pd
result = pd.read_csv('outputs/test_both.csv', sep='\t', index_col=0)
expected_rows = ['BothTest_DEV_combined', 'BothTest_DEV_Commercial', 'BothTest_DEV_Retail', 
                 'BothTest_VAL_combined', 'BothTest_VAL_Commercial', 'BothTest_VAL_Retail']
for row in expected_rows:
    assert row in result.index, f'Missing expected row: {row}'
print(f'PASS: run_from_config() created all {len(result)} expected rows')
"
```

Expected: Creates outputs/test_both.csv with 6 rows following the naming pattern

- [ ] **Step 6: Commit**

```bash
git add word_statistics.py simple_config.yaml lob_config.yaml both_config.yaml
git commit -m "feat(word_stats): add run_from_config() with 4-case grouping logic"
```

---

### Task 4: Add main() CLI Entry Point

**Files:**
- Modify: `word_statistics.py` (add after run_from_config(), replace `if __name__` block)

- [ ] **Step 1: Add argparse and sys imports**

Add to imports section:

```python
import argparse
import sys
```

- [ ] **Step 2: Add main() function**

Add after run_from_config():

```python
def main():
    """CLI entry point for config-driven word statistics analysis."""
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
```

- [ ] **Step 3: Replace `if __name__ == "__main__"` block**

Replace the entire existing `if __name__ == "__main__":` block (lines 91-110) with:

```python
if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Test CLI with missing config file**

Run:
```bash
python word_statistics.py --config nonexistent.yaml
```

Expected: Error message about config file not found, example config structure printed, exits with code 1

- [ ] **Step 5: Test CLI with valid config**

Run:
```bash
python word_statistics.py --config simple_config.yaml
```

Expected: Executes successfully, creates output file, logs show analysis progress

- [ ] **Step 6: Test CLI with default config (will fail, expected)**

Run:
```bash
python word_statistics.py
```

Expected: Error about config_word_stats.yaml not found (we'll create this in next task)

- [ ] **Step 7: Commit**

```bash
git add word_statistics.py
git commit -m "feat(word_stats): add main() CLI entry point with argparse"
```

---

### Task 5: Create Template Config File

**Files:**
- Create: `config_word_stats.yaml`

- [ ] **Step 1: Create template config file**

Create `config_word_stats.yaml`:

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

- [ ] **Step 2: Test default config CLI (will fail, expected - no data files)**

Run:
```bash
python word_statistics.py
```

Expected: Validation error about manifest CSV not found (./data/q1_files.csv) - this is correct, template points to example paths

- [ ] **Step 3: Test help message**

Run:
```bash
python word_statistics.py --help
```

Expected: Shows argparse help with description and --config option

- [ ] **Step 4: Commit**

```bash
git add config_word_stats.yaml
git commit -m "feat(word_stats): add template config file with inline documentation"
```

---

### Task 6: Integration Testing

**Files:**
- Test: `word_statistics.py` with real workflow

- [ ] **Step 1: Create realistic test manifest**

Create `integration_test_manifest.csv`:
```csv
File,LineOfBusiness,DatasetType
test_file1.csv.zip,Commercial,DEV
test_file2.csv.zip,Commercial,DEV
test_file3.csv.zip,Retail,DEV
test_file4.csv.zip,Commercial,VAL
test_file5.csv.zip,Retail,VAL
test_file6.csv.zip,Retail,VAL
```

Note: These files don't need to exist - get_word_count() will return 0, which is fine for integration test

- [ ] **Step 2: Create integration test config**

Create `integration_test_config.yaml`:
```yaml
output_file: "./outputs/integration_test.csv"
datasets:
  - name: "IntegrationTest"
    manifest_csv: "./integration_test_manifest.csv"
    file_col: "File"
    group_by_lob: "LineOfBusiness"
    group_by_dataset: "DatasetType"
```

- [ ] **Step 3: Run full integration test**

Run:
```bash
python word_statistics.py --config integration_test_config.yaml
```

Expected: Completes successfully, creates outputs/integration_test.csv

- [ ] **Step 4: Verify output structure**

Run:
```bash
python -c "
import pandas as pd
result = pd.read_csv('outputs/integration_test.csv', sep='\t', index_col=0)
print('Output rows:')
print(result.index.tolist())

expected = [
    'IntegrationTest_DEV_combined',
    'IntegrationTest_DEV_Commercial',
    'IntegrationTest_DEV_Retail',
    'IntegrationTest_VAL_combined',
    'IntegrationTest_VAL_Commercial',
    'IntegrationTest_VAL_Retail'
]

for row_name in expected:
    assert row_name in result.index, f'Missing row: {row_name}'

print(f'PASS: All {len(expected)} expected rows present')
print('Columns:', result.columns.tolist())
assert 'count' in result.columns
assert 'mean' in result.columns
assert 'std' in result.columns
print('PASS: All expected columns present')
"
```

Expected: All 6 rows present with correct names, all stat columns present

- [ ] **Step 5: Verify log file**

Run:
```bash
tail -20 citi_mrm_tools.log
```

Expected: Log entries showing:
- "Starting word statistics analysis from config"
- "Processing dataset: IntegrationTest"
- "Grouping by both LOB and dataset"
- "Found 2 dataset values: ['DEV', 'VAL']"
- Individual processing messages for each row
- "Analysis complete: processed 1 datasets, created 6 output rows"
- "Saved to ./outputs/integration_test.csv"

- [ ] **Step 6: Clean up test files**

Run:
```bash
rm -f test_config.yaml test_manifest.csv bad_config.yaml missing_manifest_config.yaml
rm -f simple_config.yaml lob_config.yaml both_config.yaml
rm -f integration_test_manifest.csv integration_test_config.yaml
rm -f outputs/test_*.csv outputs/integration_test.csv
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "test(word_stats): verify integration with all grouping scenarios"
```

---

### Task 7: Documentation Update

**Files:**
- Modify: `PROJECT_DOCUMENTATION.md`

- [ ] **Step 1: Update word_statistics.py section**

Find the "### 1. **word_statistics.py**" section (around line 93) and replace it with:

```markdown
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
```

- [ ] **Step 2: Update Example Usage Patterns section**

Find "### word_statistics.py" under "## Example Usage Patterns" (around line 260) and replace with:

```markdown
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
```

- [ ] **Step 3: Update Summary section**

Find "### word_statistics.py - **Data Characterization**" under "## Summary: Script Purposes in MRM Context" (around line 312) and update the "Accessibility Need" line:

Change from:
```markdown
**Accessibility Need:** Non-technical users need to run this without understanding parallel processing or DataFrame operations
```

To:
```markdown
**Accessibility Need:** ✅ **ACHIEVED** - Users modify YAML config and click "Run" in VSCode. No Python knowledge required.
```

- [ ] **Step 4: Update Phase 2 status in Evolution Roadmap**

Find "**Phase 2 (In Progress):**" (around line 340) and update word_statistics.py status:

Change:
```markdown
**Phase 2 (In Progress):** Refactoring for UI integration  
- 🔄 Standardize input/output interfaces
- 🔄 Improve error messages for non-technical users
- 🔄 Add input validation and helpful error guidance
- 🔄 Extract core logic from hardcoded example code
```

To:
```markdown
**Phase 2 (In Progress):** Refactoring for UI integration  
- ✅ Standardize input/output interfaces (word_statistics.py, tpr_fpr_curve.py)
- ✅ Improve error messages for non-technical users (config validation)
- ✅ Add input validation and helpful error guidance (validate_config)
- 🔄 Extract core logic from hardcoded example code (word_frequency_analysis.py remaining)
```

- [ ] **Step 5: Verify documentation changes**

Run:
```bash
grep -n "word_statistics.py" PROJECT_DOCUMENTATION.md | head -5
```

Expected: Shows updated sections with config-driven usage mentioned

- [ ] **Step 6: Commit**

```bash
git add PROJECT_DOCUMENTATION.md
git commit -m "docs: update word_statistics.py documentation for YAML config"
```

---

### Task 8: Final Validation

**Files:**
- Test: Complete workflow validation

- [ ] **Step 1: Verify all imports work**

Run:
```bash
python -c "from word_statistics import load_config, validate_config, run_from_config, main; print('PASS: All new functions importable')"
```

Expected: No import errors

- [ ] **Step 2: Verify backward compatibility**

Create backward_compat_test.py:
```python
"""Test that programmatic API still works unchanged."""
from word_statistics import word_stats, get_word_count
import pandas as pd

# Test get_word_count with nonexistent file
count = get_word_count('nonexistent.csv.zip')
assert count == 0, f"Expected 0, got {count}"
print("PASS: get_word_count() returns 0 for missing file")

# Test word_stats programmatic API
datasets = [('Test', pd.DataFrame({'File': ['fake1.zip', 'fake2.zip']}))]
result = word_stats(datasets, 'File', None)
assert len(result) == 1, f"Expected 1 row, got {len(result)}"
assert 'Test' in result.index, "Expected 'Test' in index"
print("PASS: word_stats() programmatic API works")

print("\nAll backward compatibility tests passed!")
```

Run:
```bash
python backward_compat_test.py
```

Expected: Both tests pass

- [ ] **Step 3: Verify Python 3.7 compatibility**

Run:
```bash
python -m py_compile word_statistics.py
```

Expected: No syntax errors, compiles cleanly

- [ ] **Step 4: Check for Python 3.8+ syntax**

Run:
```bash
grep -n ":=" word_statistics.py && echo "FAIL: Found walrus operator" || echo "PASS: No walrus operators"
grep -n "list\[" word_statistics.py && echo "FAIL: Found built-in generic" || echo "PASS: No built-in generics"
```

Expected: Both checks pass (no walrus operators, no built-in generics)

- [ ] **Step 5: Verify config file validation catches common errors**

Run quick validation tests:
```bash
python -c "
from word_statistics import validate_config

# Empty config
errors = validate_config({})
assert len(errors) > 0
print(f'PASS: Empty config caught ({len(errors)} errors)')

# Missing datasets
errors = validate_config({'output_file': 'test.csv'})
assert any('datasets' in e for e in errors)
print('PASS: Missing datasets caught')

# Empty datasets list
errors = validate_config({'output_file': 'test.csv', 'datasets': []})
assert any('non-empty' in e for e in errors)
print('PASS: Empty datasets list caught')

print('All validation tests passed!')
"
```

Expected: All validation checks work correctly

- [ ] **Step 6: Clean up test files**

Run:
```bash
rm -f backward_compat_test.py
```

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "test(word_stats): verify backward compatibility and Python 3.7 compliance"
```

---

## Success Criteria Checklist

After completing all tasks, verify:

- [x] Config file `config_word_stats.yaml` exists with inline documentation
- [x] User can run `python word_statistics.py` (uses default config)
- [x] User can run `python word_statistics.py --config custom.yaml`
- [x] Multiple datasets process in one run
- [x] All four grouping cases work (none, LOB, dataset, both)
- [x] Validation catches config errors before processing
- [x] Error messages are clear and include context
- [x] Existing APIs (`word_stats`, `word_stats_by_label`, `get_word_count`) unchanged
- [x] Output CSV format matches existing format (tab-separated, descriptive stats)
- [x] All operations logged to `citi_mrm_tools.log`
- [x] Python 3.7 compatible (no walrus operators, uses `typing.List`)
- [x] Documentation updated in PROJECT_DOCUMENTATION.md
- [x] Consistent UX with tpr_fpr_curve.py

## Post-Implementation Notes

**What was built:**
- Config-driven execution for word_statistics.py
- Four grouping strategies (none, LOB, dataset, both)
- Comprehensive validation with helpful error messages
- Backward-compatible programmatic API
- Template config file with documentation
- CLI with argparse

**What changed:**
- Added 4 new functions (~180 lines total)
- Modified `word_stats()` to handle `None` save_path (1 line change)
- Replaced `if __name__ == "__main__"` example with `main()` call
- Updated PROJECT_DOCUMENTATION.md

**What stayed the same:**
- `get_word_count()` - unchanged
- `word_stats()` signature and behavior - unchanged (except optional save)
- `word_stats_by_label()` - completely unchanged
- All existing logging infrastructure - unchanged
- Output format and statistics - unchanged

**Next Steps:**
- Refactor `word_frequency_analysis.py` with same YAML config pattern
- Consider UI development (Phase 3 of project roadmap)
