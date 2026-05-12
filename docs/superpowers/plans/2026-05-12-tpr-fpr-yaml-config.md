# TPR vs FPR YAML Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add YAML config-driven execution to `tpr_fpr_curve.py` so non-technical users can generate ROC curves by modifying a config file and clicking run.

**Architecture:** Minimal refactor approach - add config loading, validation, and orchestration layers on top of existing `recall_vs_fpr_curve()` function. Keep backward compatibility for programmatic use.

**Tech Stack:** Python 3.7.4, PyYAML, argparse, pandas, existing sklearn/matplotlib stack

---

## File Structure

**Modified:**
- `tpr_fpr_curve.py` - Add ~150 lines (4 new functions, modified main block)
- `requirements.txt` - Add PyYAML dependency

**Created:**
- `config_tpr_v_fpr.yaml` - Template config with inline documentation

---

## Task 1: Add PyYAML Dependency

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add PyYAML to requirements.txt**

Add after the tqdm section, before the note about standard library:

```python
# YAML configuration support (added 2026-05-12)
PyYAML>=5.4,<6.0  # Python 3.7 compatible
```

- [ ] **Step 2: Install PyYAML in venv**

Run: `source .venv/Scripts/activate && pip install "PyYAML>=5.4,<6.0"`

Expected: Successfully installed PyYAML-X.X.X

- [ ] **Step 3: Verify import works**

Run: `source .venv/Scripts/activate && python -c "import yaml; print('PyYAML version:', yaml.__version__)"`

Expected: PyYAML version: 5.x.x (no errors)

- [ ] **Step 4: Commit dependency**

```bash
git add requirements.txt
git commit -m "deps: add PyYAML for config file support

- Add PyYAML>=5.4,<6.0 (Python 3.7 compatible)
- Required for YAML configuration-driven ROC curve generation"
```

---

## Task 2: Add Config Loading Function

**Files:**
- Modify: `tpr_fpr_curve.py` (after line 19, in imports section and after line 47, before recall_vs_fpr_curve)

- [ ] **Step 1: Add yaml import**

Add to imports section after matplotlib import (after line 19):

```python
import yaml
```

- [ ] **Step 2: Add load_config function**

Add after `_sanitize_filename()` function (after line 47), before `recall_vs_fpr_curve()`:

```python
def load_config(config_path: str) -> dict:
    """
    Load YAML configuration file.
    
    Args:
        config_path: Path to YAML config file
        
    Returns:
        Dictionary with config contents
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is malformed
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

- [ ] **Step 3: Test import and syntax**

Run: `source .venv/Scripts/activate && python -m py_compile tpr_fpr_curve.py`

Expected: No output (successful compilation)

- [ ] **Step 4: Commit load_config function**

```bash
git add tpr_fpr_curve.py
git commit -m "feat: add YAML config loading function

- Add load_config() to read and parse YAML config files
- Include error handling for missing files and malformed YAML
- Add yaml import"
```

---

## Task 3: Add Config Validation Function

**Files:**
- Modify: `tpr_fpr_curve.py` (add after load_config function)

- [ ] **Step 1: Add typing import for List**

Add to imports section at top of file (after line 14):

```python
from typing import Optional, Tuple, Iterable, List
```

(Replace existing typing import line)

- [ ] **Step 2: Add os.path import**

Add to imports section after pathlib import (after line 11):

```python
import os
```

- [ ] **Step 3: Add validate_config function**

Add after `load_config()` function:

```python
def validate_config(config: dict) -> List[str]:
    """
    Validate configuration structure and data availability.
    
    Args:
        config: Configuration dictionary from YAML
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # 1. Top-level structure
    if not config:
        errors.append("Config is empty")
        return errors
    
    if 'output_dir' not in config:
        errors.append("Missing required field: output_dir")
    elif not isinstance(config['output_dir'], str) or not config['output_dir'].strip():
        errors.append("output_dir must be a non-empty string")
    
    if 'datasets' not in config:
        errors.append("Missing required field: datasets")
        return errors  # Can't continue without datasets
    
    if not isinstance(config['datasets'], list) or len(config['datasets']) == 0:
        errors.append("datasets must be a non-empty list")
        return errors
    
    # 2. Per-dataset structure validation
    required_fields = ['csv_path', 'name', 'pred_col', 'truth_col', 'score_col']
    dataset_names = []
    potential_names = set()  # Track all possible output names for collision detection
    
    for i, dataset in enumerate(config['datasets']):
        if not isinstance(dataset, dict):
            errors.append(f"Dataset {i}: must be a dictionary")
            continue
        
        ds_name = dataset.get('name', f'dataset_{i}')
        
        # Check required fields
        for field in required_fields:
            if field not in dataset:
                errors.append(f"Dataset '{ds_name}': missing required field '{field}'")
            elif not isinstance(dataset[field], str) or not dataset[field].strip():
                errors.append(f"Dataset '{ds_name}': field '{field}' must be a non-empty string")
        
        # Check optional group_by field
        if 'group_by' in dataset:
            if not isinstance(dataset['group_by'], str) or not dataset['group_by'].strip():
                errors.append(f"Dataset '{ds_name}': field 'group_by' must be a non-empty string if present")
        
        # Track dataset names for duplicate check
        dataset_names.append(ds_name)
    
    # Check for duplicate names
    seen_names = set()
    for name in dataset_names:
        if name in seen_names:
            errors.append(f"Duplicate dataset name: '{name}'")
        seen_names.add(name)
    
    # If structural validation failed, don't proceed to file checks
    if errors:
        return errors
    
    # 3. File system checks
    output_dir = config['output_dir']
    output_parent = os.path.dirname(os.path.abspath(output_dir))
    if output_parent and not os.path.exists(output_parent):
        errors.append(f"Output directory parent does not exist: {output_parent}")
    
    # 4. CSV content checks
    for dataset in config['datasets']:
        ds_name = dataset['name']
        csv_path = dataset['csv_path']
        
        # Check file exists
        if not os.path.exists(csv_path):
            errors.append(f"Dataset '{ds_name}': CSV file not found: {csv_path}")
            continue
        
        # Try to load CSV and check columns
        try:
            df = pd.read_csv(csv_path)
            
            if len(df) == 0:
                errors.append(f"Dataset '{ds_name}': CSV file is empty (no data rows)")
            
            # Check required columns exist
            for col_key in ['pred_col', 'truth_col', 'score_col']:
                col_name = dataset[col_key]
                if col_name not in df.columns:
                    available = ', '.join(df.columns[:5])
                    errors.append(
                        f"Dataset '{ds_name}': column '{col_name}' not found in CSV. "
                        f"Available columns: {available}..."
                    )
            
            # Check group_by column if specified
            if 'group_by' in dataset:
                group_col = dataset['group_by']
                if group_col not in df.columns:
                    errors.append(f"Dataset '{ds_name}': group_by column '{group_col}' not found in CSV")
                else:
                    # Collect potential output names for collision detection
                    group_values = df[group_col].unique()
                    for val in group_values:
                        potential_name = f"{ds_name}_{val}"
                        if potential_name in potential_names or potential_name in dataset_names:
                            errors.append(
                                f"Name collision detected: '{potential_name}' "
                                f"(from stratification conflicts with existing name)"
                            )
                        potential_names.add(potential_name)
            else:
                potential_names.add(ds_name)
                
        except Exception as e:
            errors.append(f"Dataset '{ds_name}': failed to load CSV: {e}")
    
    return errors
```

- [ ] **Step 4: Test compilation**

Run: `source .venv/Scripts/activate && python -m py_compile tpr_fpr_curve.py`

Expected: No output (successful compilation)

- [ ] **Step 5: Commit validate_config function**

```bash
git add tpr_fpr_curve.py
git commit -m "feat: add comprehensive config validation

- Add validate_config() with 5-stage validation
- Check top-level structure, per-dataset fields, file system, CSV content
- Detect name collisions including stratification conflicts
- Return all errors at once for better UX"
```

---

## Task 4: Add Config Orchestration Function

**Files:**
- Modify: `tpr_fpr_curve.py` (add after validate_config function)

- [ ] **Step 1: Add sys import**

Add to imports section after re import (after line 12):

```python
import sys
```

- [ ] **Step 2: Add run_from_config function**

Add after `validate_config()` function:

```python
def run_from_config(config: dict) -> None:
    """
    Process all datasets from validated config.
    
    Args:
        config: Validated configuration dictionary
        
    Returns:
        None (exits with code 0 if all succeeded, 1 if any failed)
    """
    output_dir = config['output_dir']
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    logger.info('Starting ROC analysis from config')
    
    success_count = 0
    failure_count = 0
    total_count = len(config['datasets'])
    
    for dataset in config['datasets']:
        ds_name = dataset['name']
        csv_path = dataset['csv_path']
        pred_col = dataset['pred_col']
        truth_col = dataset['truth_col']
        score_col = dataset['score_col']
        group_by = dataset.get('group_by')
        
        try:
            # Load CSV
            logger.info(f"Processing dataset: {ds_name}")
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded CSV from {csv_path}")
            
            if group_by:
                # Stratified analysis
                logger.info(f"Dataset grouped by {group_by}")
                group_values = sorted(df[group_by].unique())
                logger.info(f"Found {len(group_values)} groups: {', '.join(map(str, group_values))}")
                
                for group_value in group_values:
                    df_group = df[df[group_by] == group_value]
                    group_name = f"{ds_name}_{group_value}"
                    logger.info(f"Processing group: {group_name} ({len(df_group)} rows)")
                    
                    recall_vs_fpr_curve(
                        df=df_group,
                        pred_col=pred_col,
                        truth_col=truth_col,
                        score_col=score_col,
                        dataset_name=group_name,
                        save_dir=output_dir
                    )
            else:
                # Simple analysis
                recall_vs_fpr_curve(
                    df=df,
                    pred_col=pred_col,
                    truth_col=truth_col,
                    score_col=score_col,
                    dataset_name=ds_name,
                    save_dir=output_dir
                )
            
            success_count += 1
            
        except Exception as e:
            logger.error(f"Failed to process dataset '{ds_name}': {e}")
            failure_count += 1
    
    # Log summary
    logger.info(f"Analysis complete: {success_count}/{total_count} datasets processed successfully")
    
    # Exit with appropriate code
    if failure_count > 0:
        sys.exit(1)
```

- [ ] **Step 3: Test compilation**

Run: `source .venv/Scripts/activate && python -m py_compile tpr_fpr_curve.py`

Expected: No output (successful compilation)

- [ ] **Step 4: Commit run_from_config function**

```bash
git add tpr_fpr_curve.py
git commit -m "feat: add config orchestration function

- Add run_from_config() to process all datasets
- Support stratification via group_by column
- Continue on error with success/failure tracking
- Exit with code 1 if any dataset fails"
```

---

## Task 5: Add CLI Main Function

**Files:**
- Modify: `tpr_fpr_curve.py` (add after run_from_config, replace if __name__ block)

- [ ] **Step 1: Add argparse import**

Add to imports section after sys import:

```python
import argparse
```

- [ ] **Step 2: Add main function**

Add after `run_from_config()` function, before the `if __name__ == "__main__"` block:

```python
def main():
    """
    CLI entry point for config-driven ROC curve generation.
    """
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
```

- [ ] **Step 3: Replace if __name__ block**

Replace the existing `if __name__ == "__main__":` block (lines 120-140) with:

```python
if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Test compilation**

Run: `source .venv/Scripts/activate && python -m py_compile tpr_fpr_curve.py`

Expected: No output (successful compilation)

- [ ] **Step 5: Test help flag**

Run: `source .venv/Scripts/activate && python tpr_fpr_curve.py --help`

Expected: Help text showing usage and --config option

- [ ] **Step 6: Commit main function**

```bash
git add tpr_fpr_curve.py
git commit -m "feat: add CLI entry point with argparse

- Add main() function with --config argument parsing
- Replace example code in if __name__ block
- Provide helpful error messages for missing config
- Support default config_tpr_v_fpr.yaml lookup"
```

---

## Task 6: Create Template Config File

**Files:**
- Create: `config_tpr_v_fpr.yaml`

- [ ] **Step 1: Create config template**

Create file `config_tpr_v_fpr.yaml` with content:

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

- [ ] **Step 2: Verify YAML syntax**

Run: `source .venv/Scripts/activate && python -c "import yaml; yaml.safe_load(open('config_tpr_v_fpr.yaml'))"`

Expected: No output (valid YAML)

- [ ] **Step 3: Commit config template**

```bash
git add config_tpr_v_fpr.yaml
git commit -m "feat: add template config file for ROC analysis

- Create config_tpr_v_fpr.yaml with inline documentation
- Include example using dummy_multiclass_predictions.csv
- Show commented example for stratification with group_by"
```

---

## Task 7: End-to-End Testing

**Files:**
- Test: `tpr_fpr_curve.py`, `config_tpr_v_fpr.yaml`

- [ ] **Step 1: Clean previous outputs**

Run: `rm -rf outputs test_tpr_fpr`

Expected: Directories removed (or don't exist)

- [ ] **Step 2: Test with default config**

Run: `source .venv/Scripts/activate && python tpr_fpr_curve.py`

Expected:
- Script runs without errors
- Log messages appear showing "Starting ROC analysis", "Processing dataset: Test"
- Plot created at `outputs/tpr_v_fpr_Test.png`
- Log file `citi_mrm_tools.log` updated with analysis summary

- [ ] **Step 3: Verify output file exists**

Run: `ls -l outputs/tpr_v_fpr_Test.png`

Expected: File exists, size > 0

- [ ] **Step 4: Check log file**

Run: `tail -20 citi_mrm_tools.log`

Expected: See entries for "Starting ROC analysis", "Processing dataset: Test", "Analysis complete: 1/1"

- [ ] **Step 5: Test with explicit config flag**

Run: `source .venv/Scripts/activate && python tpr_fpr_curve.py --config config_tpr_v_fpr.yaml`

Expected: Same behavior as step 2 (uses same config)

- [ ] **Step 6: Test missing config error**

Run: `source .venv/Scripts/activate && python tpr_fpr_curve.py --config nonexistent.yaml`

Expected: Error message "Config file not found: nonexistent.yaml" with example config structure

- [ ] **Step 7: Create test config with wrong column name**

Create `test_bad_config.yaml`:

```yaml
output_dir: "./outputs"
datasets:
  - csv_path: "./dummy_multiclass_predictions.csv"
    name: "BadTest"
    pred_col: "WrongColumn"
    truth_col: "TrueValue"
    score_col: "PredictionScore"
```

- [ ] **Step 8: Test validation catches bad column**

Run: `source .venv/Scripts/activate && python tpr_fpr_curve.py --config test_bad_config.yaml`

Expected: Validation error "Dataset 'BadTest': column 'WrongColumn' not found in CSV"

- [ ] **Step 9: Clean up test files**

Run: `rm test_bad_config.yaml`

Expected: Test file removed

- [ ] **Step 10: Document test results**

No commit - testing complete. All validation and execution paths tested successfully.

---

## Task 8: Update Documentation

**Files:**
- Modify: `QUICK_START.md`, `PROJECT_DOCUMENTATION.md`

- [ ] **Step 1: Update QUICK_START.md with YAML config usage**

Add after the existing "ROC Curve" section (around line 67):

```markdown
### ROC Curve (YAML Config - Recommended)
```python
# 1. Edit config_tpr_v_fpr.yaml with your settings
# 2. Run the script
python tpr_fpr_curve.py

# Or specify custom config
python tpr_fpr_curve.py --config my_analysis.yaml
```

**Config format:**
```yaml
output_dir: "./outputs"
datasets:
  - csv_path: "./predictions.csv"
    name: "Test"
    pred_col: "ModelPrediction"
    truth_col: "TrueValue"
    score_col: "PredictionScore"
    # group_by: "LineOfBusiness"  # Optional stratification
```

### ROC Curve (Programmatic - Legacy)
```

(Keep the existing code example below this as the legacy programmatic approach)

- [ ] **Step 2: Update PROJECT_DOCUMENTATION.md script description**

Find the tpr_fpr_curve.py section (around line 70) and update the "Key Function" description:

Replace:
```markdown
**Key Function:**
- `recall_vs_fpr_curve(df, pred_col, truth_col, score_col, dataset_name, save_dir)` - Computes and plots TPR vs FPR
```

With:
```markdown
**Key Functions:**
- `recall_vs_fpr_curve(df, pred_col, truth_col, score_col, dataset_name, save_dir)` - Computes and plots TPR vs FPR (library API)
- `main()` - Config-driven CLI entry point (recommended for users)
- `run_from_config(config)` - Processes multiple datasets from YAML config
- `validate_config(config)` - Comprehensive validation with helpful error messages
```

- [ ] **Step 3: Add new usage section to PROJECT_DOCUMENTATION.md**

Add after the current tpr_fpr_curve.py "Output" section (around line 96):

```markdown
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
```

- [ ] **Step 4: Commit documentation updates**

```bash
git add QUICK_START.md PROJECT_DOCUMENTATION.md
git commit -m "docs: update for YAML config-driven ROC analysis

- Add YAML config examples to QUICK_START.md
- Document new functions and config-driven usage
- Show stratification and multi-dataset support
- Mark programmatic API as legacy but still supported"
```

---

## Task 9: Final Integration Commit

**Files:**
- All modified files

- [ ] **Step 1: Verify all changes are committed**

Run: `git status`

Expected: "nothing to commit, working tree clean"

- [ ] **Step 2: Review commit history**

Run: `git log --oneline -10`

Expected: See all commits from this implementation (dependency, functions, config, tests, docs)

- [ ] **Step 3: Run final end-to-end validation**

Run: `source .venv/Scripts/activate && python tpr_fpr_curve.py`

Expected: Clean execution, plot created, no errors

- [ ] **Step 4: Verify backward compatibility**

Test programmatic API still works. Run in Python:

```python
source .venv/Scripts/activate
python << 'EOF'
from tpr_fpr_curve import recall_vs_fpr_curve
import pandas as pd

df = pd.read_csv('dummy_multiclass_predictions.csv')
recall_vs_fpr_curve(
    df,
    pred_col='ModelPrediction',
    truth_col='TrueValue',
    score_col='PredictionScore',
    dataset_name='BackwardCompatTest',
    save_dir='./outputs'
)
print("Backward compatibility test passed")
EOF
```

Expected: "Backward compatibility test passed", no errors

- [ ] **Step 5: Clean test outputs**

Run: `rm outputs/tpr_v_fpr_BackwardCompatTest.png`

Expected: Test file removed

---

## Self-Review Checklist

**Spec coverage:**
- ✅ Config loading (Task 2)
- ✅ Config validation (Task 3) - all 5 validation stages
- ✅ Multi-dataset support (Task 4)
- ✅ Stratification with group_by (Task 4)
- ✅ CLI with argparse (Task 5)
- ✅ Template config file (Task 6)
- ✅ Backward compatibility (Task 9, step 4)
- ✅ Documentation updates (Task 8)
- ✅ PyYAML dependency (Task 1)

**Placeholder scan:**
- ✅ No TBDs or TODOs
- ✅ All code blocks complete
- ✅ All test commands include expected output

**Type consistency:**
- ✅ Function signatures match spec exactly
- ✅ Config dict keys consistent across all functions
- ✅ Dataset field names match template and validation

**Task independence:**
- ✅ Each task has explicit file paths
- ✅ Each step can be executed independently
- ✅ Commits after each logical unit

## Success Criteria

After completing this plan:

1. ✅ User can modify `config_tpr_v_fpr.yaml` and run `python tpr_fpr_curve.py`
2. ✅ User can specify custom config with `--config` flag
3. ✅ Multiple datasets process in one run
4. ✅ Stratification by group column works (group_by field)
5. ✅ Validation catches errors before processing (validate_config)
6. ✅ Existing `recall_vs_fpr_curve()` API unchanged
7. ✅ Clear error messages (validation, missing config, bad columns)
8. ✅ All outputs logged to `citi_mrm_tools.log`
9. ✅ Documentation updated (QUICK_START.md, PROJECT_DOCUMENTATION.md)
10. ✅ VSCode "Run" button works with default config
