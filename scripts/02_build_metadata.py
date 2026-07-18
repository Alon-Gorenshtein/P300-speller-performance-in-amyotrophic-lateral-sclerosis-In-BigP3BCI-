"""Create a clinical file metadata table from the verified BigP3 cache."""

from __future__ import annotations

import argparse
from pathlib import Path

from bigp3_als.edf import build_file_metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=Path("data/source_cache"))
    parser.add_argument(
        "--output", type=Path, default=Path("output/intermediate/file_metadata.csv")
    )
    arguments = parser.parse_args()
    metadata = build_file_metadata(arguments.cache)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    metadata.to_csv(arguments.output, index=False)
    print(f"wrote {len(metadata)} EDF metadata rows")


if __name__ == "__main__":
    main()
