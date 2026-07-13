"""Render the PR mapping-report Markdown/HTML from base and head SSSOM TSVs.

Used by ``.github/workflows/pr-mapping-report.yml``. ``rosetta mapping
report`` (the CLI subcommand) renders the same Markdown/HTML via
``sssom_rosetta.mapping.report``, but doesn't prefix the Markdown with the
hidden PR-comment marker used to find-and-update (rather than duplicate) the
comment across workflow re-runs, so this script calls the module's public
functions directly and adds that marker itself.

The "base" ``.sssom.tsv`` is optional -- if the path is omitted or doesn't
exist (e.g. the PR adds a mapping set for the first time), the diff is
computed against ``base=None`` so every head mapping shows up as "added".
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from sssom_rosetta.mapping.report import (
    diff_mapping_sets,
    load_mapping_set_tsv,
    render_html,
    render_markdown,
)

logger = logging.getLogger(__name__)

#: Hidden marker used to find-and-update (rather than duplicate) the PR
#: comment across workflow re-runs; must match the marker the workflow's
#: "Upsert PR comment" step searches for.
MARKER = "<!-- sssom-rosetta-mapping-report -->"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--head", required=True, type=Path, help="Head ref's .sssom.tsv path."
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=None,
        help=(
            "Base ref's .sssom.tsv path. Omitted or non-existent is treated "
            "as 'no prior version' (every head mapping is reported as added)."
        ),
    )
    parser.add_argument("--title", default="Mapping report")
    parser.add_argument("--output-markdown", required=True, type=Path)
    parser.add_argument("--output-html", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    """Render and write the Markdown (with PR-comment marker) and HTML reports."""
    args = _parse_args()

    head_set = load_mapping_set_tsv(args.head)
    base_set = None
    if args.base is not None and args.base.exists():
        base_set = load_mapping_set_tsv(args.base)
    else:
        logger.info("No base mapping set at %s; diffing against empty base.", args.base)

    diff = diff_mapping_sets(base_set, head_set)
    markdown_text = render_markdown(diff, mapping_set=head_set, title=args.title)

    args.output_markdown.parent.mkdir(parents=True, exist_ok=True)
    args.output_markdown.write_text(f"{MARKER}\n{markdown_text}", encoding="utf-8")

    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(render_html(markdown_text), encoding="utf-8")

    logger.info("Wrote %s and %s", args.output_markdown, args.output_html)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    main()
