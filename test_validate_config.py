"""
Test script for validate_config() function.
Tests multiple validation scenarios to ensure comprehensive error catching.
"""
import os
import sys
from pathlib import Path
from word_frequency_analysis import validate_config

# Test 1: Valid config
print("=" * 60)
print("Test 1: Valid config")
print("=" * 60)
valid_config = {
    'output_dir': './outputs',
    'max_workers': 2,
    'reference_dataset': 'dev',
    'datasets': [
        {
            'name': 'dev',
            'manifest_csv': 'test_manifest.csv',
            'file_col': 'file_path',
            'group_by_lob': 'lob',
            'group_by_dataset': 'dataset_type'
        }
    ]
}
errors = validate_config(valid_config)
if errors:
    print("FAIL: Expected no errors")
    for err in errors:
        print(f"  - {err}")
else:
    print("PASS: No validation errors")
print()

# Test 2: Empty config
print("=" * 60)
print("Test 2: Empty config")
print("=" * 60)
errors = validate_config({})
if errors and "Config is empty" in errors:
    print("PASS: Caught empty config")
else:
    print("FAIL: Should catch empty config")
print()

# Test 3: Missing output_dir
print("=" * 60)
print("Test 3: Missing output_dir")
print("=" * 60)
missing_output_dir = {
    'datasets': [
        {
            'name': 'dev',
            'manifest_csv': 'test_manifest.csv',
            'file_col': 'file_path'
        }
    ]
}
errors = validate_config(missing_output_dir)
if errors and any("output_dir" in err for err in errors):
    print("PASS: Caught missing output_dir")
else:
    print("FAIL: Should catch missing output_dir")
print()

# Test 4: Empty datasets list
print("=" * 60)
print("Test 4: Empty datasets list")
print("=" * 60)
empty_datasets = {
    'output_dir': './outputs',
    'datasets': []
}
errors = validate_config(empty_datasets)
if errors and any("datasets must be a non-empty list" in err for err in errors):
    print("PASS: Caught empty datasets list")
else:
    print("FAIL: Should catch empty datasets list")
print()

# Test 5: Invalid max_workers
print("=" * 60)
print("Test 5: Invalid max_workers (0)")
print("=" * 60)
invalid_workers = {
    'output_dir': './outputs',
    'max_workers': 0,
    'datasets': [
        {
            'name': 'dev',
            'manifest_csv': 'test_manifest.csv',
            'file_col': 'file_path'
        }
    ]
}
errors = validate_config(invalid_workers)
if errors and any("max_workers must be >= 1" in err for err in errors):
    print("PASS: Caught invalid max_workers")
else:
    print("FAIL: Should catch invalid max_workers")
print()

# Test 6: Missing dataset required fields
print("=" * 60)
print("Test 6: Missing dataset required fields")
print("=" * 60)
missing_fields = {
    'output_dir': './outputs',
    'datasets': [
        {
            'name': 'dev'
            # Missing manifest_csv and file_col
        }
    ]
}
errors = validate_config(missing_fields)
if errors and any("missing required field 'manifest_csv'" in err for err in errors):
    print("PASS: Caught missing manifest_csv")
else:
    print("FAIL: Should catch missing manifest_csv")
if errors and any("missing required field 'file_col'" in err for err in errors):
    print("PASS: Caught missing file_col")
else:
    print("FAIL: Should catch missing file_col")
print()

# Test 7: Non-existent manifest CSV
print("=" * 60)
print("Test 7: Non-existent manifest CSV")
print("=" * 60)
missing_manifest = {
    'output_dir': './outputs',
    'datasets': [
        {
            'name': 'dev',
            'manifest_csv': 'nonexistent_file.csv',
            'file_col': 'file_path'
        }
    ]
}
errors = validate_config(missing_manifest)
if errors and any("manifest CSV not found" in err for err in errors):
    print("PASS: Caught non-existent manifest CSV")
else:
    print("FAIL: Should catch non-existent manifest CSV")
print()

# Test 8: Invalid column in manifest
print("=" * 60)
print("Test 8: Invalid column in manifest")
print("=" * 60)
invalid_column = {
    'output_dir': './outputs',
    'datasets': [
        {
            'name': 'dev',
            'manifest_csv': 'test_manifest.csv',
            'file_col': 'nonexistent_column'
        }
    ]
}
errors = validate_config(invalid_column)
if errors and any("column 'nonexistent_column' not found" in err for err in errors):
    print("PASS: Caught invalid file_col column")
else:
    print("FAIL: Should catch invalid file_col column")
print()

# Test 9: Invalid group_by_lob column
print("=" * 60)
print("Test 9: Invalid group_by_lob column")
print("=" * 60)
invalid_lob_col = {
    'output_dir': './outputs',
    'datasets': [
        {
            'name': 'dev',
            'manifest_csv': 'test_manifest.csv',
            'file_col': 'file_path',
            'group_by_lob': 'invalid_lob_col'
        }
    ]
}
errors = validate_config(invalid_lob_col)
if errors and any("group_by_lob column 'invalid_lob_col' not found" in err for err in errors):
    print("PASS: Caught invalid group_by_lob column")
else:
    print("FAIL: Should catch invalid group_by_lob column")
print()

# Test 10: Invalid reference_dataset
print("=" * 60)
print("Test 10: Invalid reference_dataset")
print("=" * 60)
invalid_ref = {
    'output_dir': './outputs',
    'reference_dataset': 'nonexistent_dataset',
    'datasets': [
        {
            'name': 'dev',
            'manifest_csv': 'test_manifest.csv',
            'file_col': 'file_path'
        }
    ]
}
errors = validate_config(invalid_ref)
if errors and any("reference_dataset 'nonexistent_dataset' not found" in err for err in errors):
    print("PASS: Caught invalid reference_dataset")
else:
    print("FAIL: Should catch invalid reference_dataset")
print()

# Test 11: Duplicate dataset names
print("=" * 60)
print("Test 11: Duplicate dataset names")
print("=" * 60)
duplicate_names = {
    'output_dir': './outputs',
    'datasets': [
        {
            'name': 'dev',
            'manifest_csv': 'test_manifest.csv',
            'file_col': 'file_path'
        },
        {
            'name': 'dev',
            'manifest_csv': 'test_manifest.csv',
            'file_col': 'file_path'
        }
    ]
}
errors = validate_config(duplicate_names)
if errors and any("Duplicate dataset name: 'dev'" in err for err in errors):
    print("PASS: Caught duplicate dataset names")
else:
    print("FAIL: Should catch duplicate dataset names")
print()

# Test 12: Multiple errors at once
print("=" * 60)
print("Test 12: Multiple errors at once")
print("=" * 60)
multiple_errors = {
    'output_dir': '',  # Invalid
    'max_workers': -1,  # Invalid
    'reference_dataset': 'nonexistent',  # Invalid
    'datasets': [
        {
            # Missing name
            'manifest_csv': 'nonexistent.csv',  # File doesn't exist
            'file_col': 'invalid_col'
        }
    ]
}
errors = validate_config(multiple_errors)
if len(errors) >= 3:
    print(f"PASS: Caught multiple errors ({len(errors)} errors)")
    for err in errors:
        print(f"  - {err}")
else:
    print(f"FAIL: Should catch at least 3 errors, got {len(errors)}")
print()

print("=" * 60)
print("Test suite complete")
print("=" * 60)
