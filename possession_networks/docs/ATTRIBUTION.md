# Attribution

## Policy for adapted code

Any code adapted from another source must carry an inline comment at the point of adaptation with: the source URL, the author, the license, and what was changed. Example:

```python
# Adapted from https://example.org/repo/file.py (author, MIT license).
# Changes: converted to canonical coordinates, vectorized the loop.
```

Pull requests that add adapted code without this comment should not be merged.

## Current status

All code in `src/`, `scripts/`, and `tests/` was written for this project. No code has been copied or adapted from other repositories. Where behavior follows a published specification, the module docstring names it:

* `src/possnet/adapters/statsbomb.py`: field meanings and coordinate system follow the StatsBomb Open Data Events documentation (https://github.com/hudl/open-data/tree/master/doc).

## Data

Data provided by StatsBomb (open data). StatsBomb requires its logo on any published analysis. See `DATA_ACCESS.md`.

## Libraries

pandas, NumPy, PyArrow, NetworkX, SciPy, scikit-learn, matplotlib, DuckDB, requests, PyYAML, pytest, ruff. Versions are in `requirements.txt`.

## AI assistance

Parts of this repository were drafted with Claude (Anthropic) and reviewed, run, and tested by the project author. Disclose this in the final report in line with the course policy.
