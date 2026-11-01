"""`sillybench gallery` — regenerate the results grid(s) in README.md.

README.md marks each grid with a pair of comments naming an experiment:

    <!-- gallery: kookaburra-surfing -->
    ...generated, don't edit by hand...
    <!-- /gallery -->

Everything between them is replaced with a table of every .svg and .png
output in that experiment folder, alphabetical, captioned with the model
name. Run it after adding, re-running or removing an output.

Usage:
    uv run sillybench gallery
"""

import re
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
README = REPO / "README.md"
COLS = 3
THUMB_W, THUMB_H = 240, 180  # fits 3 across GitHub's README column; SVGs letterbox to fit
EXTS = {".svg", ".png"}  # PNG: outputs contributed as images (e.g. image-generation models)
PNG_SIG = b"\x89PNG\r\n\x1a\n"
BLOCK = re.compile(r"(<!-- gallery: ([\w.-]+) -->\n).*?(<!-- /gallery -->)", re.S)


def thumb_size(p: Path) -> str:
    """width/height attributes for one thumbnail.

    An SVG letterboxes itself inside the box. A PNG would stretch, so it gets
    the largest size that keeps its own aspect ratio (read from its header).
    """
    if p.suffix == ".png":
        with p.open("rb") as f:
            head = f.read(24)
        if head[:8] == PNG_SIG:
            w, h = struct.unpack(">II", head[16:24])
            if w and h:
                s = min(THUMB_W / w, THUMB_H / h)
                return f'width="{round(w * s)}" height="{round(h * s)}"'
        return f'width="{THUMB_W}"'
    return f'width="{THUMB_W}" height="{THUMB_H}"'


def grid(experiment: str) -> str:
    outputs = sorted(p for p in (REPO / experiment).iterdir() if p.suffix in EXTS)
    if not outputs:
        sys.exit(f"no .svg or .png outputs in {experiment}/")
    rows = []
    for i in range(0, len(outputs), COLS):
        cells = "".join(
            f'<td align="center"><a href="{experiment}/{p.name}">'
            f'<img src="{experiment}/{p.name}" alt="{p.stem}" {thumb_size(p)}></a>'
            f"<br><code>{p.stem}</code></td>"
            for p in outputs[i:i + COLS])
        rows.append(f"<tr>{cells}</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>\n"


def main() -> None:
    """Regenerate the results grid(s) in README.md from each experiment's SVG and PNG outputs."""
    text = README.read_text()
    new, n = BLOCK.subn(lambda m: m[1] + grid(m[2]) + m[3], text)
    if n == 0:
        sys.exit("no <!-- gallery: <experiment> --> block in README.md")
    README.write_text(new)
    print(f"refreshed {n} gallery block(s) in README.md")
