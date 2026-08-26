# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright"]
# ///
"""Render an experiment's HTML outputs to PNG screenshots.

Usage:
    uv run tools/render.py <experiment-folder> [--width W] [--height H] [--wait MS]

Screenshots are written to <experiment-folder>/renders/<model>.png.
"""

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

CHROMIUM = Path("/opt/pw-browsers/chromium")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path, help="experiment folder, e.g. littlecove")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--scale", type=int, default=2, help="device scale factor")
    parser.add_argument("--wait", type=int, default=4000, help="ms to settle animations before capture")
    args = parser.parse_args()

    src = args.experiment
    pages = sorted(src.glob("*.html"))
    if not pages:
        print(f"no .html files in {src}", file=sys.stderr)
        return 1

    out = src / "renders"
    out.mkdir(exist_ok=True)

    launch = {"executable_path": str(CHROMIUM)} if CHROMIUM.exists() else {}
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch)
        page = browser.new_page(
            viewport={"width": args.width, "height": args.height},
            device_scale_factor=args.scale,
        )
        for html in pages:
            page.goto(html.resolve().as_uri())
            page.wait_for_timeout(args.wait)
            dest = out / f"{html.stem}.png"
            page.screenshot(path=str(dest))
            print(dest)
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
