"""Compatibility entry point for the recoverable ruptures benchmark pipeline.

Run the split pipeline directly for normal use:
1. python scripts/analysis/ruptures_penalty_calibration.py
2. python scripts/analysis/ruptures_fault_benchmark.py
3. python scripts/analysis/plot_ruptures_results.py
"""

from __future__ import annotations

from ruptures_fault_benchmark import main


if __name__ == "__main__":
    main()
