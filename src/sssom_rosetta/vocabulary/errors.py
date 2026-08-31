"""Shared base exception for the ``vocabulary`` package.

Each submodule (``fetch``, ``sources``, ``namespaces``, ``dhd``, ...) still
defines its own narrowly-named error class for precise ``except`` clauses
(e.g. ``except DhdSchemaError``), but every one of them also inherits from
:class:`VocabularyError` so callers that don't need that precision -- CLI
commands reporting a single "vocabulary build failed" message, for instance
-- can catch a single common type instead of enumerating every submodule's
error class in a tuple.
"""

from __future__ import annotations


class VocabularyError(Exception):
    """Base class for all errors raised by the ``vocabulary`` package."""
