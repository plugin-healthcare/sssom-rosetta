"""Ingest and cache licence-gated vocabulary release ZIPs.

Because the LOINC-SNOMED and OMOP/Athena releases can't be fetched from an open
URL (see ``sources.py``), the curator downloads the ZIP manually and this module
ingests that local file: it verifies the checksum (when pinned), then extracts
the archive into ``data/vocabularies/<name>/<version>/`` so downstream parsers
work against stable, cached files. Ingest is idempotent — an already-extracted
cache is reused unless ``force`` is set.
"""

from __future__ import annotations

import hashlib
import logging
import zipfile
from pathlib import Path

from sssom_rosetta.vocabulary.sources import VocabularySource

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path("data/vocabularies")


class VocabularyIngestError(Exception):
    """Raised when a vocabulary ZIP can't be read or extracted."""


class VocabularyChecksumMismatchError(Exception):
    """Raised when a provided ZIP's checksum doesn't match the registry."""

    def __init__(self, source: VocabularySource, actual: str) -> None:
        super().__init__(
            f"Checksum mismatch for vocabulary source {source.name!r} "
            f"(version {source.version!r}): "
            f"expected {source.checksum!r}, got {actual!r}"
        )


def cache_dir_for(source: VocabularySource, cache_dir: Path) -> Path:
    """Return the extraction directory for a source's release."""
    return cache_dir / source.name / source.version


def _is_extracted(target_dir: Path) -> bool:
    """True if ``target_dir`` exists and contains at least one file."""
    return target_dir.is_dir() and any(target_dir.rglob("*"))


def ingest_zip(
    source: VocabularySource,
    zip_path: Path,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    *,
    force: bool = False,
) -> Path:
    """Verify and extract a curator-provided release ZIP into the cache.

    Args:
        source: The registered vocabulary source being ingested.
        zip_path: Path to the locally-downloaded release ZIP.
        cache_dir: Base directory releases are extracted under.
        force: Re-extract even if a populated cache already exists.

    Returns:
        The directory the release was extracted into.

    Raises:
        VocabularyIngestError: If the ZIP is missing or not a valid archive.
        VocabularyChecksumMismatchError: If ``source.checksum`` is pinned and
            the provided ZIP doesn't match it.
    """
    target_dir = cache_dir_for(source, cache_dir)
    if _is_extracted(target_dir) and not force:
        logger.info("Using cached %r release at %s", source.name, target_dir)
        return target_dir

    if not zip_path.is_file():
        raise VocabularyIngestError(f"ZIP not found: {zip_path}")

    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    if source.checksum is not None and digest != source.checksum:
        raise VocabularyChecksumMismatchError(source, digest)
    if source.checksum is None:
        logger.info(
            "No checksum pinned for vocabulary source %r (version %r); "
            "computed SHA-256 %s. Consider backfilling into sources.py.",
            source.name,
            source.version,
            digest,
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(target_dir)
    except zipfile.BadZipFile as exc:
        raise VocabularyIngestError(f"Not a valid ZIP: {zip_path}") from exc

    logger.info("Extracted %r release into %s", source.name, target_dir)
    return target_dir


def find_file(
    root: Path, *, prefix: str = "", suffix: str = "", contains: str = ""
) -> Path:
    """Find exactly one file under ``root`` matching ``prefix``/``suffix``.

    RF2 and Athena packages nest files in per-release subdirectories with
    date-stamped names, so callers locate files by pattern rather than exact
    path. ``contains`` further constrains matches to those whose full path
    contains the given substring (e.g. ``"/Snapshot/"`` to exclude the
    ``Full/`` and ``Delta/`` copies an International RF2 package also ships).

    Raises:
        VocabularyIngestError: If zero or more than one file matches.
    """
    matches = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.name.startswith(prefix)
        and path.name.endswith(suffix)
        and (contains in str(path))
    ]
    if not matches:
        raise VocabularyIngestError(
            f"No file matching prefix={prefix!r} suffix={suffix!r} "
            f"contains={contains!r} under {root}"
        )
    if len(matches) > 1:
        joined = ", ".join(str(match) for match in sorted(matches))
        raise VocabularyIngestError(
            f"Expected exactly one file matching prefix={prefix!r} "
            f"suffix={suffix!r} contains={contains!r} under {root}, "
            f"found: {joined}"
        )
    return matches[0]
