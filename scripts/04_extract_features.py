"""Derive session-level calibration P300 features without reading Test data."""

from __future__ import annotations

import argparse
from pathlib import Path

from bigp3_als.features import build_calibration_features


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=Path("data/source_cache"))
    parser.add_argument(
        "--output", type=Path, default=Path("output/intermediate/calibration_features.csv")
    )
    arguments = parser.parse_args()
    features = build_calibration_features(arguments.cache)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(arguments.output, index=False)
    print(f"wrote {len(features)} calibration session feature rows")


if __name__ == "__main__":
    main()
