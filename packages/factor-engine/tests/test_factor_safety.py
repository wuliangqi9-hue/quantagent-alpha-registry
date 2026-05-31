from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from crypto_factors.mantle_native import _rolling_zscore, _first_safe_float  # noqa: E402
from crypto_factors.market import calculate_market_factors  # noqa: E402


class TestFactorSafety(unittest.TestCase):
    def test_rolling_zscore_accepts_small_window(self) -> None:
        df = pd.DataFrame({"value": [1.0, 2.0, 3.0]})
        _rolling_zscore(df, "value", 2, "value_z")
        self.assertIn("value_z", df.columns)

    def test_market_factors_do_not_emit_inf_for_zero_low(self) -> None:
        rows = 40
        df = pd.DataFrame(
            {
                "open": [1.0] * rows,
                "high": [2.0] * rows,
                "low": [0.0] * rows,
                "close": [1.0] * rows,
                "volume": [100.0] * rows,
            }
        )
        out = calculate_market_factors(df, window=24)
        numeric = out.select_dtypes(include=[np.number])
        self.assertFalse(np.isinf(numeric.to_numpy()).any())

    def test_first_safe_float_skips_empty_string(self) -> None:
        self.assertEqual(_first_safe_float("", "12.5"), 12.5)


if __name__ == "__main__":
    unittest.main()
