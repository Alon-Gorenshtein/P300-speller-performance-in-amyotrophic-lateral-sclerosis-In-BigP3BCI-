"""Render publication figures from the frozen external validation outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from bigp3_als.render import render_all


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=Path, default=Path("output/final/analysis_records.csv"))
    parser.add_argument("--predictions", type=Path, default=Path("output/final/external_validation_predictions.csv"))
    parser.add_argument("--metrics", type=Path, default=Path("output/final/external_validation_metrics.csv"))
    parser.add_argument("--directory", type=Path, default=Path("output/final/figures"))
    arguments = parser.parse_args()
    render_all(pd.read_csv(arguments.records), pd.read_csv(arguments.predictions), pd.read_csv(arguments.metrics), arguments.directory)
    print("rendered three publication figures as PDF and 600-DPI PNG")


if __name__ == "__main__":
    main()
