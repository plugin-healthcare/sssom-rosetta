"""Tests for the vocabulary source registry (no network, no filesystem)."""

from __future__ import annotations

import pytest

from sssom_rosetta.vocabulary.sources import (
    VOCABULARY_SOURCES,
    UnknownVocabularySourceError,
    VocabularySource,
    get_vocabulary_source,
)


def test_registry_contains_loinc_snomed() -> None:
    source = VOCABULARY_SOURCES["loinc-snomed"]
    assert source.name == "loinc-snomed"
    assert source.kind == "rf2"
    assert source.download_page == "https://loincsnomed.org/downloads"
    assert source.checksum is None


def test_registry_contains_omop() -> None:
    source = VOCABULARY_SOURCES["omop"]
    assert source.name == "omop"
    assert source.kind == "athena"
    assert source.download_page == "https://athena.ohdsi.org/"


def test_registry_contains_snomed_international() -> None:
    source = VOCABULARY_SOURCES["snomed-international"]
    assert source.name == "snomed-international"
    assert source.kind == "rf2"
    assert source.version == "20260101"


def test_get_vocabulary_source_returns_registered() -> None:
    source = get_vocabulary_source("omop")
    assert isinstance(source, VocabularySource)
    assert source is VOCABULARY_SOURCES["omop"]


def test_get_vocabulary_source_unknown_raises() -> None:
    with pytest.raises(UnknownVocabularySourceError) as exc_info:
        get_vocabulary_source("nope")
    message = str(exc_info.value)
    assert "nope" in message
    assert "loinc-snomed" in message
    assert "omop" in message


def test_vocabulary_source_is_frozen() -> None:
    source = get_vocabulary_source("omop")
    with pytest.raises(AttributeError):
        source.version = "9.9.9"  # type: ignore[misc]
