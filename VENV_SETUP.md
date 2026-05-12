# Virtual Environment Setup for Citi MRM Tools

## Target Environment
- **Python Version:** 3.7.4
- **Package Manager:** Conda base environment
- **Platform:** Windows Server 2019

---

## Option 1: Create Conda Environment (Recommended)

This creates an environment that exactly matches your target Conda Python 3.7.4 base.

### Step 1: Create the environment
```bash
conda create -n citi_mrm python=3.7.4 -y
```

### Step 2: Activate the environment
```bash
conda activate citi_mrm
```

### Step 3: Install dependencies
```bash
# Install from conda-forge for better Python 3.7 compatibility
conda install -c conda-forge pandas=1.3.5 numpy=1.21.6 matplotlib=3.5.3 scikit-learn=1.0.2 tqdm=4.64.1 -y
```

**OR** use pip within the conda environment:
```bash
pip install -r requirements.txt
```

### Step 4: Verify installation
```bash
python --version  # Should show Python 3.7.4
python -c "import pandas; print(pandas.__version__)"
python -c "import numpy; print(numpy.__version__)"
python -c "import sklearn; print(sklearn.__version__)"
python -c "import matplotlib; print(matplotlib.__version__)"
python -c "import tqdm; print(tqdm.__version__)"
```

---

## Option 2: Create Standard Python venv (Alternative)

If you want to use standard Python virtual environments:

### Step 1: Create virtual environment
```bash
python -m venv venv_citi_mrm
```

### Step 2: Activate the environment
**Windows:**
```bash
.\venv_citi_mrm\Scripts\activate
```

**Linux/Mac:**
```bash
source venv_citi_mrm/bin/activate
```

### Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

---

## Recommended Package Versions for Python 3.7.4

Based on compatibility testing with Python 3.7:

```
pandas==1.3.5        # Last version with full Python 3.7 support
numpy==1.21.6        # Last version supporting Python 3.7
matplotlib==3.5.3    # Last version supporting Python 3.7
scikit-learn==1.0.2  # Last version supporting Python 3.7
tqdm==4.64.1         # Works with Python 3.7
```

### Why these versions?
- **pandas 2.0+** requires Python 3.8+
- **numpy 1.22+** dropped Python 3.7 support
- **matplotlib 3.6+** dropped Python 3.7 support
- **scikit-learn 1.1+** dropped Python 3.7 support

---

## Conda Environment File (Alternative Setup)

You can also create an `environment.yml` file:

```yaml
name: citi_mrm
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.7.4
  - pandas=1.3.5
  - numpy=1.21.6
  - matplotlib=3.5.3
  - scikit-learn=1.0.2
  - tqdm=4.64.1
```

Then create the environment:
```bash
conda env create -f environment.yml
```

---

## Testing the Environment

After setup, run the example scripts to verify everything works:

### Test 1: Word Statistics
```bash
# Create dummy test data first
mkdir -p Media/Telco/PhraseReco
mkdir -p outputs

# Run the script (will fail if no data, but imports will be tested)
python word_statistics.py
```

### Test 2: Word Frequency Analysis
```bash
python word_frequency_analysis.py
```

### Test 3: TPR/FPR Curve
```bash
# This one has actual test data
python tpr_fpr_curve.py
```

---

## Compatibility Notes

### Known Issues with Python 3.7:
1. **Type hints:** The scripts use `typing.Iterable` and `typing.List` - these work in 3.7 but in 3.9+ you can use lowercase `list` and `collections.abc.Iterable`
2. **Pathlib:** Fully supported in 3.7.4
3. **f-strings:** Fully supported (introduced in 3.6)
4. **ProcessPoolExecutor:** Fully supported

### What will transfer seamlessly:
- All three scripts are compatible with Python 3.7.4
- No syntax changes needed
- All libraries have stable versions for 3.7
- Logging, pathlib, and concurrent.futures are standard library

### Potential warnings you might see:
- Deprecation warnings from pandas/numpy (safe to ignore)
- sklearn might show FutureWarnings (safe to ignore)

---

## Deactivating the Environment

**Conda:**
```bash
conda deactivate
```

**venv:**
```bash
deactivate
```

---

## Removing the Environment

**Conda:**
```bash
conda env remove -n citi_mrm
```

**venv:**
```bash
# Windows
rmdir /s venv_citi_mrm

# Linux/Mac
rm -rf venv_citi_mrm
```

---

## Development Workflow

1. Develop and test changes locally in your conda environment
2. Ensure all imports are from the approved package list
3. Test scripts with sample data
4. Transfer scripts to target environment
5. Run in target Conda Python 3.7.4 base environment

**Key principle:** Since you're matching the Python version (3.7.4) and using compatible package versions, your scripts should run identically in both environments.

---

## Troubleshooting

### Issue: "No module named X"
```bash
# Verify package installation
conda list  # or pip list
# Reinstall if needed
conda install package_name
```

### Issue: Version conflicts
```bash
# Check installed versions
python -c "import package; print(package.__version__)"
# Force specific version
conda install package=version
```

### Issue: Import errors in target environment
- Verify Python version matches: `python --version`
- Verify all packages are installed in target environment
- Check that target environment has same package versions
