# Coding Standards

## 1. Python & Environment
- Target **Python 3.13** (`.venv\Scripts\python.exe`).
- Follow PEP 8 formatting (line length `<= 100` characters, 4-space indentation, double quotes or consistent style).
- Include explicit **type hints** on all public function signatures, methods, and return types.
- Add concise **Google-style or NumPy-style docstrings** to all modules, classes, and public functions.

## 2. Modularity & Reuse
- Keep functions small, single-purpose, and shallowly nested (prefer early returns).
- Never copy-paste transformation or parsing logic across files; extract shared helpers (e.g., regex/unit parsers, metric computations, plotting helpers).
- Parameterize differences using config dicts/YAML or mapping tables rather than long `if/elif` chains.
- Preserve existing comments/docstrings unless modifying the documented behavior.

## 3. Paths, Config & Logging
- Always use `pathlib.Path` (never string concatenation with `\` or `/` or hardcoded `D:\...` absolute paths inside `src/`).
- Resolve project root relative to module location or configuration loader (`src/utils/config.py`).
- Use Python's standard `logging` module inside `src/` instead of bare `print()` statements (`print` is acceptable only in standalone CLI/EDA scripts when appropriate).
- Fix `random_state` / random seeds from `config/config.yaml` (default `42`) for all splits, samplers, and stochastic models.

## 4. Pandas & Scikit-Learn Best Practices
- Avoid `SettingWithCopyWarning`: explicitly `.copy()` filtered DataFrames before mutating columns.
- Use `pd.read_csv(..., low_memory=False)` when loading mixed-type raw CSV columns.
- Never fit transformers on the combined dataset before train/test splitting.
- Ensure custom transformers inherit `(BaseEstimator, TransformerMixin)`, expose `__init__` parameters identically as attributes (sklearn `clone()` requirement), and return `self` from `fit()`.
