"""Central ``build-<source>`` target registry shared by the CLI and the ``just`` recipes.

``cli.py`` previously re-implemented the same five steps -- look up the
registered source, resolve its ingested release directory, check it exists,
build the graph, write the Turtle file -- once per ``vocabulary build-*``
subcommand, and ``vocabulary merge`` hardcoded a second copy of the resulting
filename list. :data:`BUILD_TARGETS` names each build/write pipeline once;
:func:`build_target` runs the shared steps for any of them, and
:func:`merge_candidates` derives ``merge``'s input file list from the same
registry.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sssom_rosetta.vocabulary import dhd, loinc_snomed, omop, snomed_international
from sssom_rosetta.vocabulary.errors import VocabularyError
from sssom_rosetta.vocabulary.fetch import cache_dir_for
from sssom_rosetta.vocabulary.sources import VocabularySource, get_vocabulary_source


@dataclass(frozen=True)
class BuildTarget:
    """One registered ``rosetta vocabulary build-<source>`` pipeline's source/build/write wiring.

    Attributes:
        command_name: The CLI subcommand name, e.g. ``"build-omop"``.
        source_name: Registry key in ``VOCABULARY_SOURCES``, e.g. ``"omop"``.
        output_filename: Turtle filename written under the build output
            directory, e.g. ``"omop.ttl"``.
        build: ``(release_dir) -> graph``, e.g. ``omop.build_from_release``.
        write: ``(graph, output_path) -> output_path``, e.g. ``omop.write_ttl``.
    """

    command_name: str
    source_name: str
    output_filename: str
    build: Callable[[Path], Any]
    write: Callable[[Any, Path], Path]


#: One entry per ``rosetta vocabulary build-*`` CLI subcommand, in the merge
#: order ``vocabulary merge``/:func:`merge_candidates` use (OMOP is the base
#: layer; the rest are optional additions -- see ``merge.merge_ttl_files``).
BUILD_TARGETS: tuple[BuildTarget, ...] = (
    BuildTarget("build-omop", "omop", "omop.ttl", omop.build_from_release, omop.write_ttl),
    BuildTarget(
        "build-snomed-international",
        "snomed-international",
        "snomed-international.ttl",
        snomed_international.build_from_release,
        snomed_international.write_ttl,
    ),
    BuildTarget(
        "build-loinc-snomed",
        "loinc-snomed",
        "loinc-snomed.ttl",
        loinc_snomed.build_from_release,
        loinc_snomed.write_ttl,
    ),
    BuildTarget(
        "build-dhd-diagnosethesaurus",
        "dhd-thesauri",
        "dhd-diagnosethesaurus.ttl",
        lambda release_dir: dhd.build_from_release(release_dir, "dt"),
        dhd.write_ttl,
    ),
    BuildTarget(
        "build-dhd-verrichtingenthesaurus",
        "dhd-thesauri",
        "dhd-verrichtingenthesaurus.ttl",
        lambda release_dir: dhd.build_from_release(release_dir, "vt"),
        dhd.write_ttl,
    ),
)

_BUILD_TARGETS_BY_COMMAND: dict[str, BuildTarget] = {target.command_name: target for target in BUILD_TARGETS}


class MissingReleaseError(VocabularyError):
    """Raised when a ``build-*`` target's release hasn't been ingested yet."""

    def __init__(self, target: BuildTarget, release_dir: Path) -> None:
        """Build the error message pointing at the ``ingest`` command that fixes it."""
        super().__init__(
            f"no ingested release at {release_dir}. Run 'rosetta vocabulary ingest {target.source_name} <zip>' first."
        )


def get_build_target(command_name: str) -> BuildTarget:
    """Look up a registered build target by its CLI ``command_name``."""
    return _BUILD_TARGETS_BY_COMMAND[command_name]


def build_target(target: BuildTarget, output_dir: Path, cache_dir: Path) -> Path:
    """Run one registered ``build-*`` pipeline end-to-end, writing a snapshot sidecar alongside.

    Raises:
        MissingReleaseError: If ``target``'s release hasn't been ingested yet.
        VocabularyError: Or a subclass, if ``target.build`` itself fails
            (e.g. ``dhd.DhdFormatVersionError`` on a format-version mismatch).
    """
    source = get_vocabulary_source(target.source_name)
    release_dir = cache_dir_for(source, cache_dir)
    if not release_dir.is_dir():
        raise MissingReleaseError(target, release_dir)

    graph = target.build(release_dir)
    output_path = target.write(graph, output_dir / target.output_filename)
    _write_snapshot_metadata(output_path, source)
    return output_path


def _write_snapshot_metadata(ttl_path: Path, source: VocabularySource) -> None:
    """Write a ``<ttl_path>.meta.json`` sidecar recording what/when this build ran.

    Downstream consumers (docs generation, provenance audits) can therefore
    answer "which pinned source version produced this .ttl, and when" without
    parsing Turtle or recomputing a hash themselves.
    """
    metadata = {
        "source_name": source.name,
        "source_version": source.version,
        "format_version": source.format_version,
        "built_at": datetime.now(UTC).isoformat(),
    }
    ttl_path.with_suffix(".meta.json").write_text(json.dumps(metadata, indent=2) + "\n")


def merge_candidates(output_dir: Path) -> list[Path]:
    """Return the ``build-*`` output paths under ``output_dir`` that exist, for ``vocabulary merge``.

    Derives the candidate filename list from :data:`BUILD_TARGETS` instead of
    a second hardcoded list that could drift from the one above.
    """
    return [path for target in BUILD_TARGETS if (path := output_dir / target.output_filename).exists()]
