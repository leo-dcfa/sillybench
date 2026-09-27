#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["typer>=0.12"]
# ///
"""sillybench gallery — regenerate the results grid(s) in README.md.

README.md marks each grid with a pair of comments naming an experiment:

    <!-- gallery: kookaburra-surfing -->
    ...generated, don't edit by hand...
    <!-- /gallery -->

Everything between them is replaced with a table of every .svg output in
that experiment folder, alphabetical, captioned with the model name. Run it
after adding, re-running or removing an output.

Usage:
    uv run harness/gallery.py
"""

import re
import sys
from pathlib import Path

import typer

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"
COLS = 3
THUMB_W, THUMB_H = 240, 180  # fits 3 across GitHub's README column; SVGs letterbox to fit
BLOCK = re.compile(r"(<!-- gallery: ([\w.-]+) -->\n).*?(<!-- /gallery -->)", re.S)


def grid(experiment: str) -> str:
    svgs = sorted((REPO / experiment).glob("*.svg"))
    if not svgs:
        sys.exit(f"no .svg outputs in {experiment}/")
    rows = []
    for i in range(0, len(svgs), COLS):
        cells = "".join(
            f'<td align="center"><a href="{experiment}/{p.name}">'
            f'<img src="{experiment}/{p.name}" alt="{p.stem}" '
            f'width="{THUMB_W}" height="{THUMB_H}"></a>'
            f"<br><code>{p.stem}</code></td>"
            for p in svgs[i:i + COLS])
        rows.append(f"<tr>{cells}</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>\n"


app = typer.Typer(add_completion=False)


@app.command(help="Regenerate the results grid(s) in README.md from each experiment's SVGs.")
def main() -> None:
    text = README.read_text()
    new, n = BLOCK.subn(lambda m: m[1] + grid(m[2]) + m[3], text)
    if n == 0:
        sys.exit("no <!-- gallery: <experiment> --> block in README.md")
    README.write_text(new)
    print(f"refreshed {n} gallery block(s) in README.md")


if __name__ == "__main__":
    app()
