"""
Integration test for load_config() and validate_config().
Tests the complete flow from YAML to validation.
"""
from word_frequency_analysis import load_config, validate_config

print("=" * 60)
print("Integration Test: Load and Validate Config")
print("=" * 60)

# Test with valid config file
print("\nTest 1: Valid config file")
print("-" * 60)
try:
    config = load_config('test_config.yaml')
    print("Config loaded successfully")
    print(f"Datasets: {[ds['name'] for ds in config['datasets']]}")
    print(f"Output dir: {config['output_dir']}")
    print(f"Max workers: {config['max_workers']}")
    print(f"Reference dataset: {config['reference_dataset']}")

    errors = validate_config(config)
    if errors:
        print("\nValidation FAILED:")
        for err in errors:
            print(f"  - {err}")
    else:
        print("\nValidation PASSED: No errors")
except Exception as e:
    print(f"ERROR: {e}")

# Test with non-existent file
print("\n" + "=" * 60)
print("Test 2: Non-existent config file")
print("-" * 60)
try:
    config = load_config('nonexistent_config.yaml')
    print("FAIL: Should have raised FileNotFoundError")
except FileNotFoundError as e:
    print(f"PASS: Caught expected error - {e}")
except Exception as e:
    print(f"FAIL: Unexpected error - {e}")

# Test with invalid YAML
print("\n" + "=" * 60)
print("Test 3: Invalid YAML syntax")
print("-" * 60)
import tempfile
import os
with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
    f.write("invalid: yaml: syntax: bad:\n  - item1\n  - item2\n  extra: bad")
    temp_file = f.name

try:
    config = load_config(temp_file)
    print("FAIL: Should have raised yaml.YAMLError")
except Exception as e:
    print(f"PASS: Caught error - {type(e).__name__}")
finally:
    os.unlink(temp_file)

print("\n" + "=" * 60)
print("Integration test complete")
print("=" * 60)
