"""Tests for the ontology loader (all HTTP calls mocked, no network)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

import pytest
from rdflib import Graph

from sssom_rosetta.ontology.loader import (
    ChecksumMismatchError,
    OntologyFetchError,
    fetch_ontology,
    load_ontology,
)
from sssom_rosetta.ontology.sources import OntologySource

FIXTURE_TTL = b"""\
@prefix ex: <http://example.org/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

ex:Foo a rdfs:Class ;
    rdfs:label "Foo" .

ex:Bar a rdfs:Class ;
    rdfs:label "Bar" .
"""


def _make_source(checksum: str | None = None) -> OntologySource:
    return OntologySource(
        name="test-source",
        version="1.0.0",
        iri="http://example.org/test-source",
        download_url="https://example.org/ontology.ttl",
        checksum=checksum,
    )


class _FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


def test_fetch_ontology_downloads_and_caches(tmp_path: Path) -> None:
    source = _make_source()
    with patch("sssom_rosetta.ontology.loader.requests.get") as mock_get:
        mock_get.return_value = _FakeResponse(FIXTURE_TTL)
        path = fetch_ontology(source, cache_dir=tmp_path)

    assert mock_get.call_count == 1
    expected_path = tmp_path / "test-source" / "1.0.0" / "ontology.ttl"
    assert path == expected_path
    assert path.exists()
    assert path.read_bytes() == FIXTURE_TTL


def test_fetch_ontology_cache_hit_skips_network_call(tmp_path: Path) -> None:
    source = _make_source()
    cached_path = tmp_path / "test-source" / "1.0.0" / "ontology.ttl"
    cached_path.parent.mkdir(parents=True)
    cached_path.write_bytes(FIXTURE_TTL)

    with patch("sssom_rosetta.ontology.loader.requests.get") as mock_get:
        path = fetch_ontology(source, cache_dir=tmp_path)

    mock_get.assert_not_called()
    assert path == cached_path


def test_fetch_ontology_force_redownloads(tmp_path: Path) -> None:
    source = _make_source()
    cached_path = tmp_path / "test-source" / "1.0.0" / "ontology.ttl"
    cached_path.parent.mkdir(parents=True)
    cached_path.write_bytes(b"stale content")

    with patch("sssom_rosetta.ontology.loader.requests.get") as mock_get:
        mock_get.return_value = _FakeResponse(FIXTURE_TTL)
        path = fetch_ontology(source, cache_dir=tmp_path, force=True)

    mock_get.assert_called_once()
    assert path.read_bytes() == FIXTURE_TTL


def test_fetch_ontology_checksum_mismatch_raises(tmp_path: Path) -> None:
    source = _make_source(checksum="0" * 64)
    with patch("sssom_rosetta.ontology.loader.requests.get") as mock_get:
        mock_get.return_value = _FakeResponse(FIXTURE_TTL)
        with pytest.raises(ChecksumMismatchError):
            fetch_ontology(source, cache_dir=tmp_path)


def test_fetch_ontology_checksum_match_succeeds(tmp_path: Path) -> None:
    digest = hashlib.sha256(FIXTURE_TTL).hexdigest()
    source = _make_source(checksum=digest)
    with patch("sssom_rosetta.ontology.loader.requests.get") as mock_get:
        mock_get.return_value = _FakeResponse(FIXTURE_TTL)
        path = fetch_ontology(source, cache_dir=tmp_path)
    assert path.read_bytes() == FIXTURE_TTL


def test_fetch_ontology_network_error_raises_ontology_fetch_error(
    tmp_path: Path,
) -> None:
    import requests

    source = _make_source()
    with patch("sssom_rosetta.ontology.loader.requests.get") as mock_get:
        mock_get.side_effect = requests.ConnectionError("boom")
        with pytest.raises(OntologyFetchError) as exc_info:
            fetch_ontology(source, cache_dir=tmp_path)

    assert source.download_url in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_load_ontology_returns_populated_graph(tmp_path: Path) -> None:
    source = _make_source()
    with patch("sssom_rosetta.ontology.loader.requests.get") as mock_get:
        mock_get.return_value = _FakeResponse(FIXTURE_TTL)
        graph = load_ontology(source, cache_dir=tmp_path)

    assert isinstance(graph, Graph)
    assert len(graph) > 0
    labels = {
        str(o)
        for _, _, o in graph.triples((None, None, None))
        if str(o) in {"Foo", "Bar"}
    }
    assert labels == {"Foo", "Bar"}
