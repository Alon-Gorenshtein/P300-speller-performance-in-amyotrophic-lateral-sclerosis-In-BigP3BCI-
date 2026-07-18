"""Validate and selectively cache the clinical BigP3 EDF source files."""

from __future__ import annotations

import argparse
from pathlib import Path

from bigp3_als.provenance import (
    activate_cache,
    build_manifest,
    validate_archive_sha256,
    validate_member_sha256,
    write_validation_record,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path("data/source_cache"))
    parser.add_argument(
        "--record", type=Path, default=Path("output/intermediate/manifest_validation.json")
    )
    arguments = parser.parse_args()
    validate_archive_sha256(arguments.archive)
    manifest = build_manifest(arguments.archive)
    for member in manifest:
        validate_member_sha256(arguments.archive, member)
    activate_cache(arguments.archive, manifest, arguments.cache)
    write_validation_record(arguments.record, arguments.archive, manifest)
    print(f"verified and cached {len(manifest)} EDF members")


if __name__ == "__main__":
    main()
