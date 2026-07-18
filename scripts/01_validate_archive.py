"""Validate and selectively cache the clinical BigP3 EDF source files."""

from __future__ import annotations

import argparse
from pathlib import Path
import json

from bigp3_als.provenance import (
    ARCHIVE_SHA256,
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
    parser.add_argument(
        "--studies",
        nargs="+",
        default=None,
        help="Optional subset of prespecified ALS source studies, for resumable ingestion.",
    )
    parser.add_argument(
        "--stage",
        choices=("all", "archive", "members", "cache"),
        default="all",
        help="Run all stages or a resumable archive, member, or cache stage.",
    )
    arguments = parser.parse_args()
    selected_studies = None if arguments.studies is None else frozenset(arguments.studies)
    archive_record = arguments.record.with_suffix(".archive.json")
    manifest = build_manifest(arguments.archive, selected_studies)
    observed_archive_sha256: str | None = None
    if arguments.stage in {"all", "archive"}:
        print("verifying archive SHA256", flush=True)
        validate_archive_sha256(arguments.archive)
        observed_archive_sha256 = ARCHIVE_SHA256
        archive_record.write_text(
            json.dumps(
                {
                    "archive_path": str(arguments.archive.resolve()),
                    "archive_sha256": observed_archive_sha256,
                    "expected_archive_sha256": ARCHIVE_SHA256,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    if arguments.stage in {"all", "members"}:
        if arguments.stage == "members":
            if not archive_record.exists():
                raise FileNotFoundError("an archive-verification record is required before member verification")
            archived = json.loads(archive_record.read_text(encoding="utf-8"))
            if archived["archive_path"] != str(arguments.archive.resolve()) or archived["archive_sha256"] != ARCHIVE_SHA256:
                raise ValueError("archive-verification record does not match the pinned archive")
            observed_archive_sha256 = archived["archive_sha256"]
        print(f"verifying {len(manifest)} source EDF checksums", flush=True)
        for member_index, member in enumerate(manifest, start=1):
            validate_member_sha256(arguments.archive, member)
            if member_index % 100 == 0 or member_index == len(manifest):
                print(f"verified {member_index}/{len(manifest)} EDF checksums", flush=True)
        assert observed_archive_sha256 is not None
        write_validation_record(arguments.record, arguments.archive, manifest, observed_archive_sha256)
    if arguments.stage in {"all", "cache"}:
        if not arguments.record.exists():
            raise FileNotFoundError("a completed verification record is required before caching")
        recorded = json.loads(arguments.record.read_text(encoding="utf-8"))
        expected_paths = [member.relative_path for member in manifest]
        recorded_paths = [member["relative_path"] for member in recorded["members"]]
        if recorded_paths != expected_paths:
            raise ValueError("verification record does not match the requested source manifest")
        print("materializing verified cache", flush=True)
        activate_cache(arguments.archive, manifest, arguments.cache)
    if arguments.stage == "archive":
        print("archive SHA256 verified")
    elif arguments.stage == "members":
        print(f"verified {len(manifest)} EDF members")
    elif arguments.stage == "cache":
        print(f"cached {len(manifest)} previously verified EDF members")
    else:
        print(f"verified and cached {len(manifest)} EDF members")


if __name__ == "__main__":
    main()
