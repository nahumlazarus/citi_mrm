# Word Frequency Analysis YAML Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add YAML configuration-driven execution to word_frequency_analysis.py following the word_statistics.py pattern

**Architecture:** Minimal additive refactor - add config loading, validation, and orchestration functions on top of existing functions. Add CLI entry point with argparse. Four grouping cases handled by helper functions.

**Tech Stack:** Python 3.7, PyYAML, pandas, argparse

**Reference Spec:** docs/superpowers/specs/2026-06-08-word-frequency-yaml-config-design.md

---

## File Structure

**Modified Files:**
- `word_frequency_analysis.py` - Add ~250-300 lines (6 new functions + error handling update + main block replacement)

**New Files:**
- `config_word_frequency.yaml` - Template configuration file with inline documentation

**No Changes:**
- `get_dataset_unigrams()` - Unchanged
- `cnt_unigrams()` - Unchanged
- `word_freq()` - Unchanged (existing function)

---

### Task 1: Add Required Imports

**Files:**
- Modify: `word_frequency_analysis.py` (lines 1-16, imports section)

- [ ] **Step 1: Verify yaml import exists**

Read the imports section and check if `import yaml` is present.

Run:
```bash
grep -n "^import yaml" word_frequency_analysis.py
```

Expected: Either finds the import or returns nothing (we'll add it if missing)

- [ ] **Step 2: Add missing imports**

If yaml import is missing, add it. Also add argparse, sys, and os imports.

Add these lines after the existing imports (around line 15, after `from typing import Iterable, List`):

```python
import yaml
import argparse
import sys
import os
```

Verify imports are Python 3.7 compatible (no `from __future__` needed).

- [ ] **Step 3: Verify changes**

Run:
```bash
python -m py_compile word_frequency_analysis.py
```

Expected: No syntax errors

- [ ] **Step 4: Commit**

```bash
git add word_frequency_analysis.py
git commit -m "feat(word_freq): add imports for config support (yaml, argparse, sys, os)"
```

---

### Task 2: Add Error Handling to get_transcript_unigrams()

**Files:**
- Modify: `word_frequency_analysis.py:62-75` (get_transcript_unigrams function)

- [ ] **Step 1: Locate the function**

Run:
```bash
grep -n "^def get_transcript_unigrams" word_frequency_analysis.py
```

Expected: Shows line number (around line 62)

- [ ] **Step 2: Replace function with error handling version**

Replace the existing `get_transcript_unigrams()` function with:

```python
def get_transcript_unigrams(file_path: str) -> Iterable[str]:
    """
    Takes in a transcript in phrase reco format and extracts the unigrams.
    Returns empty list on error (logged, not raised).

    Inputs:
    1. Single transcript in phrase reco format.

    Outputs:
    1. List of unigrams from the transcript.
    """
    try:
        tscript = pd.read_csv(file_path, sep='\t', header=None, names=['Nxpr', 'Channel', 'Type', 'Phrase', 'StartCS', 'EndCS', 'Score'])
        words = list(tscript[tscript['Type']=='T']['Phrase'])
        return words
    except Exception as e:
        logger.warning(f"Failed to read {file_path}: {e}")
        return []
```

- [ ] **Step 3: Test the change**

Run:
```bash
python -c "from word_frequency_analysis import get_transcript_unigrams; result = get_transcript_unigrams('nonexistent.zip'); print(f'PASS: Returns {result} on error')"
```

Expected: PASS message, no crash

- [ ] **Step 4: Commit**

```bash
git add word_frequency_analysis.py
git commit -m "fix(word_freq): add error handling to get_transcript_unigrams - returns empty list on failure"
```

---

### Task 3: Add load_config() Function

**Files:**
- Modify: `word_frequency_analysis.py` (add after line 159, before `if __name__`)

- [ ] **Step 1: Add load_config() function**

Add after the `word_freq()` function and before the `if __name__ == "__main__":` block:

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

- [ ] **Step 2: Test with a valid config**

Create a minimal test config:
```bash
echo 'output_dir: "./outputs"
reference_dataset: null
max_workers: null
datasets:
  - name: "Test"
    manifest_csv: "./test.csv"
    file_col: "File"' > test_config_minimal.yaml
```

Run:
```bash
python -c "from word_frequency_analysis import load_config; config = load_config('test_config_minimal.yaml'); print(f\"PASS: Loaded config with {len(config['datasets'])} dataset(s)\")"
```

Expected: PASS message showing 1 dataset

- [ ] **Step 3: Test with missing file**

Run:
```bash
python -c "from word_frequency_analysis import load_config; 
try:
    load_config('nonexistent.yaml')
    print('FAIL: Should have raised FileNotFoundError')
except FileNotFoundError as e:
    print(f'PASS: Caught FileNotFoundError - {e}')"
```

Expected: PASS message with error details

- [ ] **Step 4: Commit**

```bash
git add word_frequency_analysis.py test_config_minimal.yaml
git commit -m "feat(word_freq): add load_config() for YAML loading"
```

---

### Task 4: Add validate_config() Function

**Files:**
- Modify: `word_frequency_analysis.py` (add after load_config())

- [ ] **Step 1: Add validate_config() function**

Add after load_config():

```python
def validate_config(config: dict) -> List[str]:
    """Validate configuration structure and file availability.
    
    Args:
        config: Configuration dictionary from load_config()
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Check config is not empty
    if not config:
        errors.append("Config is empty")
        return errors
    
    # 1. Check top-level structure
    if 'output_dir' not in config or not config['output_dir']:
        errors.append("Missing required field: output_dir")
    elif not isinstance(config['output_dir'], str) or not config['output_dir'].strip():
        errors.append("output_dir must be a non-empty string")
    
    if 'datasets' not in config:
        errors.append("Missing required field: datasets")
        return errors
    
    if not isinstance(config['datasets'], list) or len(config['datasets']) == 0:
        errors.append("datasets must be a non-empty list")
        return errors
    
    # 2. Validate max_workers if present
    max_workers = config.get('max_workers')
    if max_workers is not None:
        if not isinstance(max_workers, int) or max_workers < 1:
            errors.append(f"max_workers must be >= 1, got: {max_workers}")
        elif os.cpu_count() and max_workers > os.cpu_count():
            logger.warning(f"max_workers ({max_workers}) exceeds available CPU cores ({os.cpu_count()})")
    
    # 3. Validate output_dir exists or can be created
    if 'output_dir' in config and config['output_dir']:
        output_dir = Path(config['output_dir'])
        if not output_dir.exists() and not output_dir.parent.exists():
            errors.append(f"output_dir parent does not exist: {output_dir.parent}")
    
    # 4. Validate reference_dataset if specified
    reference_dataset = config.get('reference_dataset')
    if reference_dataset is not None:
        dataset_names = [ds.get('name') for ds in config['datasets']]
        if reference_dataset not in dataset_names:
            errors.append(f"reference_dataset '{reference_dataset}' not found in datasets list. Available: {dataset_names}")
    
    # 5. Track dataset names for duplicate check
    dataset_names = []
    
    # 6. Validate each dataset
    for idx, dataset in enumerate(config['datasets']):
        ds_name = dataset.get('name', f'dataset[{idx}]')
        
        # Check required fields
        if 'name' not in dataset or not dataset['name']:
            errors.append(f"Dataset {idx}: missing required field 'name'")
            ds_name = f'dataset[{idx}]'
        else:
            dataset_names.append(dataset['name'])
        
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
                if not isinstance(dataset['group_by_lob'], str) or not dataset['group_by_lob'].strip():
                    errors.append(f"Dataset '{ds_name}': group_by_lob must be a non-empty string")
                elif dataset['group_by_lob'] not in manifest_df.columns:
                    errors.append(f"Dataset '{ds_name}': group_by_lob column '{dataset['group_by_lob']}' not found in manifest CSV")
            
            # Check group_by_dataset column if specified
            if 'group_by_dataset' in dataset and dataset['group_by_dataset']:
                if not isinstance(dataset['group_by_dataset'], str) or not dataset['group_by_dataset'].strip():
                    errors.append(f"Dataset '{ds_name}': group_by_dataset must be a non-empty string")
                elif dataset['group_by_dataset'] not in manifest_df.columns:
                    errors.append(f"Dataset '{ds_name}': group_by_dataset column '{dataset['group_by_dataset']}' not found in manifest CSV")
            
            # Check manifest has data rows
            if len(manifest_df) == 0:
                errors.append(f"Dataset '{ds_name}': manifest CSV has no data rows")
        
        except Exception as e:
            errors.append(f"Dataset '{ds_name}': failed to load manifest CSV: {e}")
    
    # 7. Check for duplicate dataset names
    seen_names = set()
    for name in dataset_names:
        if name in seen_names:
            errors.append(f"Duplicate dataset name: '{name}'")
        seen_names.add(name)
    
    return errors
```

- [ ] **Step 2: Create test manifest CSV**

```bash
echo 'File,LineOfBusiness,DatasetType
test1.zip,Commercial,DEV
test2.zip,Retail,VAL' > test_manifest.csv
```

- [ ] **Step 3: Test validation with valid config**

Update test_config_minimal.yaml:
```bash
echo 'output_dir: "./outputs"
reference_dataset: "Test"
max_workers: null
datasets:
  - name: "Test"
    manifest_csv: "./test_manifest.csv"
    file_col: "File"
    group_by_lob: "LineOfBusiness"' > test_config_valid.yaml
```

Run:
```bash
python -c "from word_frequency_analysis import load_config, validate_config; config = load_config('test_config_valid.yaml'); errors = validate_config(config); print(f'PASS: Validation returned {len(errors)} errors' if errors == [] else f'FAIL: {errors}')"
```

Expected: PASS with 0 errors

- [ ] **Step 4: Test validation with missing fields**

```bash
echo 'datasets:
  - manifest_csv: "./test.csv"' > test_config_invalid.yaml
```

Run:
```bash
python -c "from word_frequency_analysis import load_config, validate_config; config = load_config('test_config_invalid.yaml'); errors = validate_config(config); print(f'PASS: Caught {len(errors)} errors') if len(errors) > 0 else print('FAIL: Should have found errors'); print('\n'.join(errors))"
```

Expected: PASS with multiple errors listed (output_dir, name, file_col missing)

- [ ] **Step 5: Test validation with nonexistent reference**

```bash
echo 'output_dir: "./outputs"
reference_dataset: "NonExistent"
datasets:
  - name: "Test"
    manifest_csv: "./test_manifest.csv"
    file_col: "File"' > test_config_bad_ref.yaml
```

Run:
```bash
python -c "from word_frequency_analysis import load_config, validate_config; config = load_config('test_config_bad_ref.yaml'); errors = validate_config(config); assert any('NonExistent' in e for e in errors); print(f'PASS: Caught reference_dataset error: {[e for e in errors if \"NonExistent\" in e][0]}')"
```

Expected: PASS showing the reference dataset error

- [ ] **Step 6: Commit**

```bash
git add word_frequency_analysis.py test_manifest.csv test_config_valid.yaml test_config_invalid.yaml test_config_bad_ref.yaml
git commit -m "feat(word_freq): add validate_config() with comprehensive validation"
```

---

### Task 5: Add process_single_group() Helper Function

**Files:**
- Modify: `word_frequency_analysis.py` (add after validate_config())

- [ ] **Step 1: Add process_single_group() function**

Add after validate_config():

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
    logger.info(f"Processing {output_name} ({len(file_paths)} files)")
    
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

- [ ] **Step 2: Verify syntax**

Run:
```bash
python -m py_compile word_frequency_analysis.py
```

Expected: No syntax errors

- [ ] **Step 3: Verify function is importable**

Run:
```bash
python -c "from word_frequency_analysis import process_single_group; print('PASS: process_single_group imported successfully')"
```

Expected: PASS message

- [ ] **Step 4: Commit**

```bash
git add word_frequency_analysis.py
git commit -m "feat(word_freq): add process_single_group() helper for output generation"
```

---

### Task 6: Add process_dataset_with_grouping() Helper Function

**Files:**
- Modify: `word_frequency_analysis.py` (add after process_single_group())

- [ ] **Step 1: Add process_dataset_with_grouping() function**

Add after process_single_group():

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

- [ ] **Step 2: Verify syntax**

Run:
```bash
python -m py_compile word_frequency_analysis.py
```

Expected: No syntax errors

- [ ] **Step 3: Verify function is importable**

Run:
```bash
python -c "from word_frequency_analysis import process_dataset_with_grouping; print('PASS: process_dataset_with_grouping imported successfully')"
```

Expected: PASS message

- [ ] **Step 4: Commit**

```bash
git add word_frequency_analysis.py
git commit -m "feat(word_freq): add process_dataset_with_grouping() with 4-case grouping logic"
```

---

### Task 7: Add run_from_config() Function

**Files:**
- Modify: `word_frequency_analysis.py` (add after process_dataset_with_grouping())

- [ ] **Step 1: Add run_from_config() function**

Add after process_dataset_with_grouping():

```python
def run_from_config(config: dict) -> None:
    """Execute word frequency analysis from validated config.
    
    Args:
        config: Validated configuration dictionary
        
    Note: Config must be validated before calling this function.
    """
    # 1. Extract config values
    output_dir = config['output_dir']
    reference_dataset = config.get('reference_dataset')
    max_workers_config = config.get('max_workers')
    datasets = config['datasets']
    
    # 2. Determine worker count
    if max_workers_config is None:
        max_workers = max(1, os.cpu_count() // 2)
        logger.info(f"Auto-detected max_workers: {max_workers} (half of {os.cpu_count()} cores)")
    else:
        max_workers = max_workers_config
        logger.info(f"Using configured max_workers: {max_workers}")
    
    # 3. Log analysis start
    logger.info("Starting word frequency analysis from config")
    
    # 4. PHASE 1: Build reference (if cross-dataset mode)
    ref_words = None
    is_independent_mode = True
    
    if reference_dataset is not None:
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
    else:
        # Independent mode
        logger.info("Independent mode: each dataset will use own unigrams as reference")
    
    # 5. PHASE 2: Process each dataset
    datasets_processed = 0
    datasets_total = len(datasets)
    
    for dataset in datasets:
        ds_name = dataset['name']
        manifest_csv = dataset['manifest_csv']
        file_col = dataset['file_col']
        group_by_lob = dataset.get('group_by_lob')
        group_by_dataset = dataset.get('group_by_dataset')
        
        try:
            manifest_df = pd.read_csv(manifest_csv)
            logger.info(f"Processing dataset: {ds_name} ({len(manifest_df)} files in manifest)")
            
            # Apply grouping logic
            process_dataset_with_grouping(
                ds_name, manifest_df, file_col,
                group_by_lob, group_by_dataset,
                ref_words, is_independent_mode,
                max_workers, output_dir
            )
            
            datasets_processed += 1
        
        except Exception as e:
            logger.error(f"Failed to process dataset '{ds_name}': {e}")
            continue
    
    # 6. PHASE 3: Summary
    logger.info("Analysis complete")
    logger.info(f"Datasets processed: {datasets_processed}/{datasets_total}")
    if datasets_processed < datasets_total:
        logger.warning(f"{datasets_total - datasets_processed} dataset(s) failed - check log for details")
```

- [ ] **Step 2: Verify syntax**

Run:
```bash
python -m py_compile word_frequency_analysis.py
```

Expected: No syntax errors

- [ ] **Step 3: Verify function is importable**

Run:
```bash
python -c "from word_frequency_analysis import run_from_config; print('PASS: run_from_config imported successfully')"
```

Expected: PASS message

- [ ] **Step 4: Commit**

```bash
git add word_frequency_analysis.py
git commit -m "feat(word_freq): add run_from_config() orchestrator with 3-phase execution"
```

---

### Task 8: Add main() CLI Entry Point

**Files:**
- Modify: `word_frequency_analysis.py` (add after run_from_config())

- [ ] **Step 1: Add main() function**

Add after run_from_config():

```python
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
```

- [ ] **Step 2: Test help message**

Run:
```bash
python word_frequency_analysis.py --help
```

Expected: Shows argparse help with description and --config option

- [ ] **Step 3: Test with missing config**

Run:
```bash
python word_frequency_analysis.py --config nonexistent.yaml
```

Expected: Error message about config file not found, example config structure printed, exits with code 1

- [ ] **Step 4: Commit**

```bash
git add word_frequency_analysis.py
git commit -m "feat(word_freq): add main() CLI entry point with argparse"
```

---

### Task 9: Update if __name__ == "__main__" Block

**Files:**
- Modify: `word_frequency_analysis.py` (lines 160-174, replace example code with main() call)

- [ ] **Step 1: Locate the block**

Run:
```bash
grep -n "^if __name__" word_frequency_analysis.py
```

Expected: Shows line number (around line 160)

- [ ] **Step 2: Replace the entire if __name__ block**

Replace the entire `if __name__ == "__main__":` block with:

```python
if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify the change**

Run:
```bash
tail -5 word_frequency_analysis.py
```

Expected: Shows the new if __name__ block calling main()

- [ ] **Step 4: Test that script imports without running**

Run:
```bash
python -c "import word_frequency_analysis; print('PASS: Script imports without auto-execution')"
```

Expected: PASS message, no analysis runs

- [ ] **Step 5: Commit**

```bash
git add word_frequency_analysis.py
git commit -m "refactor(word_freq): replace example code in __main__ block with main() call"
```

---

### Task 10: Create Template Config File

**Files:**
- Create: `config_word_frequency.yaml`

- [ ] **Step 1: Create template config**

Create `config_word_frequency.yaml`:

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

- [ ] **Step 2: Test loading the template**

Run:
```bash
python -c "from word_frequency_analysis import load_config; config = load_config('config_word_frequency.yaml'); print(f\"PASS: Template loaded - {config['reference_dataset']} reference, {len(config['datasets'])} dataset(s)\")"
```

Expected: PASS message showing DEV reference and 1 dataset

- [ ] **Step 3: Test validation will fail (missing data files)**

Run:
```bash
python word_frequency_analysis.py
```

Expected: Validation error about missing ./data/dev_files.csv (this is expected - template uses example paths)

- [ ] **Step 4: Commit**

```bash
git add config_word_frequency.yaml
git commit -m "feat(word_freq): add template config file with inline documentation"
```

---

### Task 11: Integration Testing

**Files:**
- Test: Complete workflow with real configs

- [ ] **Step 1: Create test data setup**

Create a small test manifest and phrase reco files:

```bash
mkdir -p test_data
echo 'File
test_data/file1.csv.zip
test_data/file2.csv.zip' > test_simple_manifest.csv
```

Create dummy phrase reco files:
```bash
echo -e "1\t1\tT\thello\t0\t50\t1.0\n2\t1\tT\tworld\t50\t100\t1.0" > test_data/file1.csv
echo -e "1\t1\tT\thello\t0\t50\t1.0\n2\t1\tT\ttest\t50\t100\t1.0" > test_data/file2.csv
gzip -c test_data/file1.csv > test_data/file1.csv.zip
gzip -c test_data/file2.csv > test_data/file2.csv.zip
```

- [ ] **Step 2: Create test config for independent mode**

```bash
mkdir -p test_outputs
echo 'output_dir: "./test_outputs"
reference_dataset: null
max_workers: 2

datasets:
  - name: "SimpleTest"
    manifest_csv: "./test_simple_manifest.csv"
    file_col: "File"' > test_config_simple.yaml
```

- [ ] **Step 3: Run independent mode test**

Run:
```bash
python word_frequency_analysis.py --config test_config_simple.yaml
```

Expected: 
- Logs show "Independent mode"
- Logs show "Auto-detected max_workers: 2"
- Creates test_outputs/SimpleTest_word_frequency_*.csv
- No errors

- [ ] **Step 4: Verify output file exists**

Run:
```bash
ls -la test_outputs/SimpleTest_word_frequency_*.csv
```

Expected: File exists with timestamp

- [ ] **Step 5: Check output file content**

Run:
```bash
head -5 test_outputs/SimpleTest_word_frequency_*.csv
```

Expected: Tab-separated CSV with columns: Word, SimpleTest Count, SimpleTest %

- [ ] **Step 6: Create test manifest with grouping columns**

```bash
echo 'File,LineOfBusiness
test_data/file1.csv.zip,Commercial
test_data/file2.csv.zip,Retail' > test_grouped_manifest.csv
```

- [ ] **Step 7: Create test config for LOB grouping**

```bash
echo 'output_dir: "./test_outputs"
reference_dataset: null
max_workers: 2

datasets:
  - name: "GroupedTest"
    manifest_csv: "./test_grouped_manifest.csv"
    file_col: "File"
    group_by_lob: "LineOfBusiness"' > test_config_grouped.yaml
```

- [ ] **Step 8: Run LOB grouping test**

Run:
```bash
python word_frequency_analysis.py --config test_config_grouped.yaml
```

Expected:
- Logs show "Grouping by LOB: 2 groups"
- Creates 3 files: GroupedTest_combined, GroupedTest_Commercial, GroupedTest_Retail
- No errors

- [ ] **Step 9: Verify all grouped output files exist**

Run:
```bash
ls -la test_outputs/GroupedTest_*.csv | wc -l
```

Expected: Shows 3 (or 4 if SimpleTest still there - that's fine)

- [ ] **Step 10: Clean up test files**

Run:
```bash
rm -rf test_data test_outputs test_simple_manifest.csv test_grouped_manifest.csv test_config_simple.yaml test_config_grouped.yaml
rm -f test_config_minimal.yaml test_config_valid.yaml test_config_invalid.yaml test_config_bad_ref.yaml test_manifest.csv
```

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "test(word_freq): verify integration with independent and LOB grouping scenarios"
```

---

### Task 12: Update PROJECT_DOCUMENTATION.md

**Files:**
- Modify: `PROJECT_DOCUMENTATION.md`

- [ ] **Step 1: Locate word_frequency_analysis.py section**

Run:
```bash
grep -n "### 2. \*\*word_frequency_analysis.py\*\*" PROJECT_DOCUMENTATION.md
```

Expected: Shows line number (around line 144)

- [ ] **Step 2: Update the section**

Replace the "### 2. **word_frequency_analysis.py**" section (lines ~144-173) with:

```markdown
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
reference_dataset: "DEV"  # or null for independent mode
max_workers: null         # auto-detect (half of CPU cores)
datasets:
  - name: "DEV"
    manifest_csv: "./files.csv"     # CSV with phrase reco file paths
    file_col: "File"                # Column containing file paths
    group_by_lob: "LineOfBusiness"  # Optional: LOB grouping
```

**Analysis Modes:**
- **Cross-dataset:** Specify reference_dataset - one dataset provides reference vocabulary for all
- **Independent:** Set reference_dataset to null - each dataset uses own vocabulary

**Grouping Behavior:**
- No grouping: Single output per dataset
- LOB only: Creates {name}_combined + one file per LOB value
- Dataset only: One file per dataset value (no combined)
- Both: Creates {name}_{dataset}_combined + {name}_{dataset}_{lob} for each combination

**Programmatic API (Legacy, Still Supported):**
- `get_transcript_unigrams(file_path)` - Extracts all unigrams from a single transcript
- `get_dataset_unigrams(file_paths, max_workers, dataset_name)` - Extracts unigrams from entire dataset (parallel processing)
- `cnt_unigrams(ref_word, word_counter)` - Counts occurrences of a reference word
- `word_freq(ref_words, words, max_workers, dataset_name, save_dir)` - Calculates word frequencies against reference set

**Workflow:**
1. Build reference unigram set from reference dataset (cross-dataset) or each dataset individually (independent)
2. Count occurrences of reference unigrams across all datasets
3. Calculate both absolute counts and percentages

**Input Format:**
- File paths to phrase reco files (.csv.zip format)
- Same tab-separated format as word_statistics.py

**Output:**
- CSV file per dataset (or group) with columns:
  - `Word` - The unigram
  - `{dataset_name} Count` - Absolute frequency
  - `{dataset_name} %` - Relative frequency (percentage)
- Timestamped filenames: `{dataset_name}_word_frequency_analysis_{timestamp}.csv`

**Performance:**
- Uses `ProcessPoolExecutor` for parallel processing
- Progress bars via `tqdm`
- Auto-detects CPU cores (defaults to half for safety)
```

- [ ] **Step 3: Update Example Usage Patterns section**

Find "### word_frequency_analysis.py" under "## Example Usage Patterns" (around line 304) and replace with:

```markdown
### word_frequency_analysis.py

**Config-driven (recommended):**
```bash
python word_frequency_analysis.py --config my_config.yaml
```

**Programmatic:**
```python
from word_frequency_analysis import get_dataset_unigrams, word_freq
import glob

# Build reference set from dev dataset
dev_files = glob.glob("./data/dev/*.zip")
words_dev = get_dataset_unigrams(dev_files, max_workers=4, dataset_name='DEV')
ref_words = list(set(words_dev))

# Analyze other datasets against reference
itv_files = glob.glob("./data/itv/*.zip")
words_itv = get_dataset_unigrams(itv_files, max_workers=4, dataset_name='ITV')
word_freq(ref_words, words_itv, 4, 'ITV', './outputs')
```
```

- [ ] **Step 4: Update Summary section**

Find "### word_frequency_analysis.py - **Vocabulary Analysis**" under "## Summary: Script Purposes in MRM Context" (around line 355) and update the "Accessibility Need" line:

Change:
```markdown
**Accessibility Need:** Semi-technical users need to understand which datasets to compare and where outputs go
```

To:
```markdown
**Accessibility Need:** ✅ **ACHIEVED** - Users modify YAML config and click "Run" in VSCode. Supports cross-dataset and independent analysis modes.
```

- [ ] **Step 5: Update Phase 2 status in Evolution Roadmap**

Find "**Phase 2 (In Progress):**" (around line 378) and update to mark word_frequency_analysis.py complete:

Change:
```markdown
**Phase 2 (In Progress):** Refactoring for UI integration  
- ✅ Standardize input/output interfaces (word_statistics.py, tpr_fpr_curve.py)
- ✅ Improve error messages for non-technical users (config validation)
- ✅ Add input validation and helpful error guidance (validate_config)
- 🔄 Extract core logic from hardcoded example code (word_frequency_analysis.py remaining)
```

To:
```markdown
**Phase 2 (Complete):** Refactoring for UI integration  
- ✅ Standardize input/output interfaces (all three core scripts)
- ✅ Improve error messages for non-technical users (config validation)
- ✅ Add input validation and helpful error guidance (validate_config)
- ✅ Extract core logic from hardcoded example code (all scripts config-driven)
```

- [ ] **Step 6: Verify changes**

Run:
```bash
grep -A 2 "word_frequency_analysis.py" PROJECT_DOCUMENTATION.md | head -10
```

Expected: Shows updated section with config-driven usage mentioned

- [ ] **Step 7: Commit**

```bash
git add PROJECT_DOCUMENTATION.md
git commit -m "docs: update word_frequency_analysis.py documentation for YAML config

- Add config-driven usage examples
- Document analysis modes (cross-dataset vs independent)
- Document grouping behavior
- Mark Phase 2 complete in roadmap"
```

---

### Task 13: Python 3.7 Compatibility Verification

**Files:**
- Test: `word_frequency_analysis.py`

- [ ] **Step 1: Verify no Python 3.8+ syntax**

Run:
```bash
grep -n ":=" word_frequency_analysis.py
```

Expected: No matches (no walrus operators)

Run:
```bash
grep -n "list\[" word_frequency_analysis.py
```

Expected: No matches (no built-in generic type syntax)

- [ ] **Step 2: Compile check**

Run:
```bash
python -m py_compile word_frequency_analysis.py
```

Expected: No syntax errors

- [ ] **Step 3: Import all new functions**

Run:
```bash
python -c "from word_frequency_analysis import load_config, validate_config, process_single_group, process_dataset_with_grouping, run_from_config, main; print('PASS: All new functions importable')"
```

Expected: PASS message

- [ ] **Step 4: Verify backward compatibility**

Run:
```bash
python -c "from word_frequency_analysis import get_transcript_unigrams, get_dataset_unigrams, cnt_unigrams, word_freq; print('PASS: Programmatic API still works')"
```

Expected: PASS message

- [ ] **Step 5: Check typing imports**

Run:
```bash
grep "from typing import" word_frequency_analysis.py
```

Expected: Shows `from typing import Iterable, List` (Python 3.7 compatible)

- [ ] **Step 6: Final verification - no issues found**

If all checks pass, no commit needed. If issues found, fix them and commit:

```bash
# Only if fixes were needed:
git add word_frequency_analysis.py
git commit -m "fix(word_freq): ensure Python 3.7 compatibility"
```

---

## Success Criteria Checklist

After completing all tasks, verify:

- [x] Config file `config_word_frequency.yaml` exists with inline documentation
- [x] User can run `python word_frequency_analysis.py` (uses default config)
- [x] User can run `python word_frequency_analysis.py --config custom.yaml`
- [x] Cross-dataset mode works (shared reference from specified dataset)
- [x] Independent mode works (each dataset self-references)
- [x] All 4 grouping cases implemented (none, LOB, dataset, both)
- [x] Auto-detect worker count (half of cores)
- [x] Validation catches config errors before processing
- [x] Individual file errors don't crash analysis (return empty list)
- [x] Existing functions unchanged (backward compatible)
- [x] Python 3.7 compatible (no 3.8+ syntax)
- [x] Documentation updated in PROJECT_DOCUMENTATION.md
- [x] Consistent UX with word_statistics.py and tpr_fpr_curve.py

## Post-Implementation Notes

**What was built:**
- Config-driven execution for word_frequency_analysis.py
- Two analysis modes (cross-dataset with shared reference, independent self-referencing)
- Four grouping strategies (none, LOB only, dataset only, both)
- Comprehensive validation with helpful error messages
- Auto-detect worker count (half of CPU cores for safety)
- Backward-compatible programmatic API
- Template config file with documentation
- CLI with argparse

**What changed:**
- Added 6 new functions (~250 lines total)
- Modified `get_transcript_unigrams()` to add error handling (1 line change)
- Replaced `if __name__ == "__main__"` example with `main()` call
- Updated PROJECT_DOCUMENTATION.md

**What stayed the same:**
- `get_dataset_unigrams()` - unchanged
- `cnt_unigrams()` - unchanged
- `word_freq()` - unchanged
- All existing logging infrastructure - unchanged
- Output format and statistics - unchanged

**Next Steps:**
- Consider extracting shared config infrastructure across all three scripts (future enhancement)
- Phase 2 now complete - ready for Phase 3 (UI integration)
