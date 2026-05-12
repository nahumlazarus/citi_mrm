# Quick Start Guide - Citi MRM Tools

## TL;DR - Get Started in 3 Steps

### 1. Create Environment
```bash
conda env create -f environment.yml
conda activate citi_mrm
```

### 2. Verify Installation
```bash
python --version  # Should show 3.7.4
python -c "import pandas, numpy, sklearn, matplotlib, tqdm; print('All packages loaded successfully')"
```

### 3. Run Example
```bash
python tpr_fpr_curve.py
```

---

## What Each Script Does

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| **word_statistics.py** | Word count statistics per transcript | Phrase reco files + labels | CSV with descriptive stats |
| **word_frequency_analysis.py** | Unigram frequency analysis (parallel) | Phrase reco files | CSV with word counts & percentages |
| **tpr_fpr_curve.py** | ROC curve generation | Model predictions + scores | PNG plot + AUC metric |

---

## Quick Code Examples

### Word Statistics
```python
from word_statistics import word_stats
import pandas as pd
import glob

# Prepare datasets
dev_files = glob.glob("./data/dev/*.zip")
datasets = [('DEV', pd.DataFrame({'File': dev_files}))]

# Generate statistics
stats = word_stats(datasets, 'File', './outputs/word_stats.csv')
print(stats)
```

### Word Frequency Analysis
```python
from word_frequency_analysis import get_dataset_unigrams, word_freq
import glob

# Extract unigrams
files = glob.glob("./data/dev/*.zip")
words = get_dataset_unigrams(files, max_workers=4, dataset_name='DEV')

# Create reference set
ref_words = list(set(words))

# Count frequencies
counts = word_freq(ref_words, words, 4, 'DEV', './outputs')
```

### ROC Curve
```python
from tpr_fpr_curve import recall_vs_fpr_curve
import pandas as pd

# Load predictions
df = pd.read_csv('predictions.csv')

# Generate ROC curve
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

## File Locations

- **Scripts:** `*.py` (project root)
- **Documentation:** `*.md` (project root)
- **Configuration:** `environment.yml`, `requirements.txt`
- **Test Data:** `dummy_multiclass_predictions.csv`
- **Logs:** `citi_mrm_tools.log` (auto-generated)

---

## Environment Compatibility

### Your Development Environment:
- Windows Server 2019
- Bash shell (Git Bash/WSL)
- Conda/venv support

### Target Environment:
- Conda Python 3.7.4 base
- Same package versions as `environment.yml`

**Result:** Scripts developed here will run identically in target environment.

---

## Common Commands

```bash
# Activate environment
conda activate citi_mrm

# Deactivate
conda deactivate

# Update packages (be careful with Python 3.7 compatibility!)
conda update --all

# Export current environment
conda env export > environment_snapshot.yml

# List installed packages
conda list

# Check package versions
python -c "import pandas; print(pandas.__version__)"
```

---

## Need Help?

1. Check `PROJECT_DOCUMENTATION.md` for detailed script documentation
2. Check `VENV_SETUP.md` for environment setup troubleshooting
3. Check `citi_mrm_tools.log` for execution logs
4. Run scripts with `-h` or check `if __name__ == "__main__"` blocks for examples

---

## Next Steps

1. ✅ Environment set up
2. ✅ Test with dummy data
3. 📝 Prepare your actual phrase reco files
4. 🚀 Run analyses on your datasets
5. 📊 Review outputs in `./outputs/` directory
