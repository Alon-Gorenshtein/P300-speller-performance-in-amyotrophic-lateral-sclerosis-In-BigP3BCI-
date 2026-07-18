"""Tests for publication-output validation."""

from __future__ import annotations

import pandas as pd
import pytest

from bigp3_als.render import require_columns


def test_require_columns_rejects_incomplete_analysis_table() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        require_columns(pd.DataFrame({"study": ["StudyF"]}), {"study", "calibration_auc"})
