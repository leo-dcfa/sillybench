# sillybench — agent notes

- Benchmark repo of silly, unscored model tests. The focus is one experiment: `kookaburra-surfing/` ("Generate an SVG of a kookaburra surfing a longboard"). No build/test/lint/config.
- Each **experiment** = a folder at the repo root — except `harness/`, which holds tooling (the runner and the README gallery script), not an experiment.
- Each experiment folder must contain a `prompt.md` recording the exact prompt.
- A model performs the prompt in `prompt.md` and writes its output as a **single file or folder named after that model** inside the experiment folder (e.g. `kookaburra-surfing/claude-opus-5.svg`). Use a folder instead of a single file when the output is multi-part.
- An experiment folder may also hold reference assets (e.g. a photo of a real place), with provenance in `photo-credit.md`. These are for comparing outputs against; a model only uses one if `prompt.md` asks it to.
- Default language: Python; env/package management: `uv`. Harness scripts are stdlib-only.
- Models may NOT look inside other experiment folders. Each model may only read `AGENTS.md`, `README`, and the folder of the experiment it is running.

## Commands

- `uv run harness/run.py <experiment> <model> [--temperature T --top-p P ...]` — run one model on one experiment. Needs `jq` and an OpenCode provider (`--provider`, default `homelab`) in `~/.config/opencode/opencode.json`. Gives the model `web_fetch` + `web_search` (`--no-tools` to disable). Writes `<experiment>/<model>.<ext>`; transcripts land in `harness/logs/` (gitignored). All flags are in README.md → "The harness".
- `uv run harness/gallery.py` — regenerate the README results grid(s) from the SVGs in each `<!-- gallery: <experiment> -->` block. Run it after adding, re-running or removing an output; never edit the grid by hand.
- When committing an output, put hardware, quantization and sampling settings in the commit message — that's the only place they're recorded.
