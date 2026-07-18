"""Reconstruct transparent online spelling outcomes from clinical BigP3 EDF files."""

from __future__ import annotations

import argparse
from pathlib import Path

from bigp3_als.trials import build_online_trial_table


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=Path("data/source_cache"))
    parser.add_argument(
        "--output", type=Path, default=Path("output/intermediate/online_trials.csv")
    )
    arguments = parser.parse_args()
    trials = build_online_trial_table(arguments.cache)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    trials.to_csv(arguments.output, index=False)
    print(f"wrote {len(trials)} feedback-phase trial rows")


if __name__ == "__main__":
    main()
