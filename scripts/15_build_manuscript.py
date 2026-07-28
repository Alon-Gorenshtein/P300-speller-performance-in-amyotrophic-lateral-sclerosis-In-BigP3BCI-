"""Render the manuscript, cover letter, and supplement to PDF and DOCX with pandoc.

The PDFs previously committed under manuscript/ are stale: they render manuscript.md, the
pre-widening four-cohort draft, not manuscript_expanded.md, the current eighteen-cohort one. No
render script existed before this one, so a stale PDF could sit next to a current markdown source
indefinitely without anyone noticing. This script is now the only way any of the three documents
gets rendered, so that cannot happen again.

Pandoc's markdown reader consumes `![]() {width=NN%}` image attributes without any extra flag; a
literal `{width=NN%}` in a rendered PDF means the PDF was not produced by pandoc, not that an
extension is missing.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

TARGETS = {
    "manuscript": Path("manuscript/manuscript_expanded.md"),
    "cover_letter": Path("manuscript/cover_letter_expanded.md"),
    "supplement": Path("supplementary/supplement_expanded.md"),
}

PDF_ENGINE = "xelatex"
BODY_FONT_SIZE = "12pt"

# Pandoc renders every pipe table as a LaTeX `longtable` sized off the full body font, and the
# widest tables here (Table 2's 9 columns, Table S6's 13) hyphenate to one syllable per column and
# overprint their headers at 12pt with 1-inch margins. `\AtBeginEnvironment` from etoolbox scopes
# `\small` to just the longtable environment, so table text shrinks without touching body text
# anywhere else in the document.
TABLE_HEADER_INCLUDES = (
    r"\usepackage{etoolbox}"
    r"\usepackage{pdflscape}"
    r"\AtBeginEnvironment{longtable}{\small}"
)


def _require_tools() -> None:
    for tool in ("pandoc", PDF_ENGINE):
        if shutil.which(tool) is None:
            raise SystemExit(f"{tool} is not on PATH; install it before running this script")


def render(name: str, source: Path, output_directory: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"{name}: no source file at {source}")
    output_directory.mkdir(parents=True, exist_ok=True)
    resource_path = str(source.parent.resolve())
    pdf_path = output_directory / f"{name}.pdf"
    docx_path = output_directory / f"{name}.docx"

    subprocess.run(
        [
            "pandoc", str(source.resolve()),
            "--from", "markdown",
            "--pdf-engine", PDF_ENGINE,
            "--resource-path", resource_path,
            "-V", f"fontsize={BODY_FONT_SIZE}",
            "-V", "geometry:margin=1in",
            "-V", f"header-includes:{TABLE_HEADER_INCLUDES}",
            "-o", str(pdf_path),
        ],
        check=True,
    )
    subprocess.run(
        [
            "pandoc", str(source.resolve()),
            "--from", "markdown",
            "--resource-path", resource_path,
            "-o", str(docx_path),
        ],
        check=True,
    )
    print(f"wrote {pdf_path}")
    print(f"wrote {docx_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", type=Path, default=Path("build_expanded"))
    parser.add_argument("--only", choices=sorted(TARGETS), default=None)
    arguments = parser.parse_args()

    _require_tools()
    names = [arguments.only] if arguments.only else sorted(TARGETS)
    for name in names:
        render(name, TARGETS[name], arguments.output_directory)


if __name__ == "__main__":
    main()
