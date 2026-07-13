"""Download-and-cache ontology loader.

Fetches an ``OntologySource``'s Turtle file over HTTP, caches it under
``data/ontologies/<name>/<version>/ontology.ttl`` (reproducible fetch: see
AGENTS.md design principle 6), verifies its checksum when one is pinned in
the registry, and parses the cached file into an ``rdflib.Graph``.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import requests
from rdflib import Graph

from sssom_rosetta.ontology.sources import OntologySource

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path("data/ontologies")


class OntologyFetchError(Exception):
    """Raised when downloading an ontology source fails."""

    def __init__(self, url: str, exc: Exception) -> None:
        super().__init__(f"Failed to fetch ontology from {url!r}: {exc}")


class ChecksumMismatchError(Exception):
    """Raised when a downloaded ontology's checksum doesn't match the registry."""

    def __init__(self, source: OntologySource, actual: str) -> None:
        super().__init__(
            f"Checksum mismatch for ontology source {source.name!r} "
            f"(version {source.version!r}): "
            f"expected {source.checksum!r}, got {actual!r}"
        )


def _cache_path(source: OntologySource, cache_dir: Path) -> Path:
    """Return the local cache path for a source's ontology file."""
    return cache_dir / source.name / source.version / "ontology.ttl"


def fetch_ontology(
    source: OntologySource,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    *,
    force: bool = False,
) -> Path:
    """Download and cache an ontology source's Turtle file.

    If the cached file already exists, the download is skipped (idempotent,
    no network call) unless ``force`` is True.

    Args:
        source: The ontology source to fetch.
        cache_dir: Base directory under which sources are cached, one
            subdirectory per ``<name>/<version>``.
        force: Re-download even if a cached file already exists.

    Returns:
        Path to the cached Turtle file.

    Raises:
        OntologyFetchError: If the HTTP request fails.
        ChecksumMismatchError: If ``source.checksum`` is set and doesn't
            match the downloaded bytes.
    """
    path = _cache_path(source, cache_dir)
    if path.exists() and not force:
        logger.info("Using cached ontology for %r at %s", source.name, path)
        return path

    logger.info("Fetching ontology %r from %s", source.name, source.download_url)
    try:
        response = requests.get(source.download_url, timeout=60)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise OntologyFetchError(source.download_url, exc) from exc

    content = response.content
    digest = hashlib.sha256(content).hexdigest()

    if source.checksum is not None:
        if digest != source.checksum:
            raise ChecksumMismatchError(source, digest)
    else:
        logger.info(
            "No checksum pinned for ontology source %r (version %r); "
            "computed SHA-256 %s. Consider backfilling this into sources.py.",
            source.name,
            source.version,
            digest,
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    logger.info("Cached ontology %r at %s", source.name, path)
    return path


def load_ontology(
    source: OntologySource,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    *,
    force: bool = False,
) -> Graph:
    """Fetch (if needed) and parse an ontology source into an ``rdflib.Graph``.

    Args:
        source: The ontology source to load.
        cache_dir: Base directory under which sources are cached.
        force: Re-download even if a cached file already exists.

    Returns:
        A populated ``rdflib.Graph`` parsed from the cached Turtle file.
    """
    path = fetch_ontology(source, cache_dir, force=force)
    graph = Graph()
    graph.parse(path, format="turtle")
    return graph
