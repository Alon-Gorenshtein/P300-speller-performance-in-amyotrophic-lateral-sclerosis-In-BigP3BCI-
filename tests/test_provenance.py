"""Tests for immutable, selective BigP3 source ingestion."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

from bigp3_als.provenance import (
    ProvenanceError,
    activate_cache,
    build_manifest,
    sha256_file,
    validate_archive_sha256,
    validate_member_sha256,
)


def _write_archive(path: Path, *, corrupt_manifest: bool = False) -> None:
    payloads = {
        "fixture/bigP3BCI-data/StudyF/F_01/SE001/Train/F_01.edf": b"train",
        "fixture/bigP3BCI-data/StudyL/L_01/SE001/Test/L_01.edf": b"test",
        "fixture/bigP3BCI-data/StudyA/A_01/SE001/Test/A_01.edf": b"not clinical",
        "fixture/bigP3BCI-data/StudyF/F_01/SE001/Train/._F_01.edf": b"sidecar",
    }
    checksums = []
    for member, payload in payloads.items():
        relative = member.removeprefix("fixture/")
        digest = hashlib.sha256(payload).hexdigest()
        if corrupt_manifest and relative.endswith("L_01.edf"):
            digest = "0" * 64
        checksums.append(f"{digest} {relative}")
    with zipfile.ZipFile(path, "w") as archive:
        for member, payload in payloads.items():
            archive.writestr(member, payload)
        archive.writestr("fixture/SHA256SUMS.txt", "\n".join(checksums) + "\n")


def test_manifest_selects_only_clinical_studies_and_rejects_sidecars(tmp_path: Path) -> None:
    archive = tmp_path / "fixture.zip"
    _write_archive(archive)

    manifest = build_manifest(archive)

    assert [member.relative_path for member in manifest] == [
        "bigP3BCI-data/StudyF/F_01/SE001/Train/F_01.edf",
        "bigP3BCI-data/StudyL/L_01/SE001/Test/L_01.edf",
    ]


def test_wrong_archive_sha256_aborts(tmp_path: Path) -> None:
    archive = tmp_path / "fixture.zip"
    _write_archive(archive)

    with pytest.raises(ProvenanceError, match="archive SHA256 mismatch"):
        validate_archive_sha256(archive, "0" * 64)


def test_manifest_checksum_mismatch_aborts(tmp_path: Path) -> None:
    archive = tmp_path / "fixture.zip"
    _write_archive(archive, corrupt_manifest=True)
    manifest = build_manifest(archive)

    with pytest.raises(ProvenanceError, match="member SHA256 mismatch"):
        validate_member_sha256(archive, manifest[1])


def test_cache_activation_contains_exactly_verified_selected_members(tmp_path: Path) -> None:
    archive = tmp_path / "fixture.zip"
    _write_archive(archive)
    manifest = build_manifest(archive)
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "obsolete.txt").write_text("remove me", encoding="utf-8")

    activate_cache(archive, manifest, cache)

    cached_paths = sorted(
        path.relative_to(cache).as_posix() for path in cache.rglob("*") if path.is_file()
    )
    assert cached_paths == [member.relative_path for member in manifest]
    for member in manifest:
        assert sha256_file(cache / member.relative_path) == member.sha256
