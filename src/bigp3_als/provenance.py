"""Provenance-checked selective ingestion for the BigP3 ALS source archive."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import zipfile


ARCHIVE_SHA256 = "eea294aa34e9ed11e5a25d07e30aeefdf8b2d467a8309e2c38405a289afcd72f"
CLINICAL_STUDIES = frozenset({"StudyF", "StudyL", "StudyN"})


class ProvenanceError(RuntimeError):
    """Raised when an input archive or cached source fails verification."""


@dataclass(frozen=True)
class ArchiveMember:
    """A selected archive member with its authoritative source checksum."""

    zip_path: str
    relative_path: str
    sha256: str
    size_bytes: int


def sha256_file(path: Path) -> str:
    """Return the SHA256 digest of a file without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_archive_sha256(archive_path: Path, expected_sha256: str = ARCHIVE_SHA256) -> None:
    """Raise if the locally downloaded ZIP does not match the pinned digest."""
    observed_sha256 = sha256_file(archive_path)
    if observed_sha256 != expected_sha256:
        raise ProvenanceError(
            "archive SHA256 mismatch: "
            f"expected {expected_sha256}, observed {observed_sha256}"
        )


def _has_appledouble_component(path: str) -> bool:
    return any(component.startswith("._") for component in Path(path).parts)


def _parse_sha256sums(contents: str) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line in contents.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        digest, relative_path = stripped.split(maxsplit=1)
        checksums[relative_path.lstrip("*")] = digest
    return checksums


def _find_member(archive: zipfile.ZipFile, suffix: str) -> str:
    matches = [name for name in archive.namelist() if name.endswith(suffix)]
    if len(matches) != 1:
        raise ProvenanceError(f"expected one {suffix} member, found {len(matches)}")
    return matches[0]


def build_manifest(archive_path: Path) -> list[ArchiveMember]:
    """Select verified F/L/N EDF members from the archive's checksum manifest."""
    with zipfile.ZipFile(archive_path) as archive:
        checksum_member = _find_member(archive, "SHA256SUMS.txt")
        checksums = _parse_sha256sums(archive.read(checksum_member).decode("utf-8"))
        selected: list[ArchiveMember] = []
        for info in archive.infolist():
            zip_path = info.filename
            if _has_appledouble_component(zip_path) or not zip_path.endswith(".edf"):
                continue
            marker = "bigP3BCI-data/"
            if marker not in zip_path:
                continue
            relative_path = zip_path[zip_path.index(marker) :]
            components = Path(relative_path).parts
            if len(components) < 2 or components[1] not in CLINICAL_STUDIES:
                continue
            try:
                expected_sha256 = checksums[relative_path]
            except KeyError as error:
                raise ProvenanceError(f"missing checksum for {relative_path}") from error
            selected.append(
                ArchiveMember(
                    zip_path=zip_path,
                    relative_path=relative_path,
                    sha256=expected_sha256,
                    size_bytes=info.file_size,
                )
            )
    if not selected:
        raise ProvenanceError("no eligible StudyF/StudyL/StudyN EDF members selected")
    return sorted(selected, key=lambda member: member.relative_path)


def _member_sha256(archive: zipfile.ZipFile, member: ArchiveMember) -> str:
    digest = hashlib.sha256()
    with archive.open(member.zip_path) as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_member_sha256(archive_path: Path, member: ArchiveMember) -> None:
    """Raise if a selected source member differs from the archive manifest."""
    with zipfile.ZipFile(archive_path) as archive:
        observed_sha256 = _member_sha256(archive, member)
    if observed_sha256 != member.sha256:
        raise ProvenanceError(
            "member SHA256 mismatch: "
            f"{member.relative_path}; expected {member.sha256}, observed {observed_sha256}"
        )


def _write_member(archive: zipfile.ZipFile, member: ArchiveMember, destination: Path) -> None:
    target = destination / member.relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    with archive.open(member.zip_path) as source, target.open("wb") as output:
        shutil.copyfileobj(source, output, length=1 << 20)
    if sha256_file(target) != member.sha256:
        raise ProvenanceError(f"cached member SHA256 mismatch: {member.relative_path}")


def activate_cache(archive_path: Path, manifest: list[ArchiveMember], cache_path: Path) -> None:
    """Atomically replace a cache with exactly the selected verified members."""
    cache_path = cache_path.resolve()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    staging_path = Path(tempfile.mkdtemp(prefix=f".{cache_path.name}.staging-", dir=cache_path.parent))
    backup_path = cache_path.with_name(f".{cache_path.name}.backup")
    if backup_path.exists():
        raise ProvenanceError(f"refusing to overwrite existing cache backup: {backup_path}")
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for member in manifest:
                _write_member(archive, member, staging_path)
        cached_paths = sorted(
            path.relative_to(staging_path).as_posix()
            for path in staging_path.rglob("*")
            if path.is_file() and not _has_appledouble_component(path.as_posix())
        )
        expected_paths = [member.relative_path for member in manifest]
        if cached_paths != expected_paths:
            raise ProvenanceError("staged cache content does not equal the verified manifest")
        if cache_path.exists():
            os.replace(cache_path, backup_path)
        os.replace(staging_path, cache_path)
        if backup_path.exists():
            shutil.rmtree(backup_path)
    except Exception:
        if staging_path.exists():
            shutil.rmtree(staging_path)
        if backup_path.exists() and not cache_path.exists():
            os.replace(backup_path, cache_path)
        raise


def write_validation_record(
    output_path: Path,
    archive_path: Path,
    manifest: list[ArchiveMember],
) -> None:
    """Write an auditable JSON record of the pinned archive and selected inputs."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "archive_path": str(archive_path.resolve()),
        "archive_sha256": sha256_file(archive_path),
        "expected_archive_sha256": ARCHIVE_SHA256,
        "selected_member_count": len(manifest),
        "members": [asdict(member) for member in manifest],
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
