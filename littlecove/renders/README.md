# littlecove — rendered output

Static screenshots of each model's HTML in this experiment folder, so the
results can be compared without opening a browser.

| render | source |
| --- | --- |
| `deepseek-v4-flash-0731.png` | `../deepseek-v4-flash-0731.html` |
| `qwen3.8-27b.png` | `../qwen3.8-27b.html` |

Captured with headless Chromium at a 1600×1000 viewport, 2× device scale
(3200×2000 px images), after a 4s settle so the CSS animations are past their
opening frames. These are single frames — the sources are animated, so open the
HTML for the moving version.

Regenerate:

```
uv run tools/render.py littlecove
```
