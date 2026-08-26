# sillybench — agent notes

- Brand-new benchmark repo; no build/test/lint/config yet.
- Each **experiment** = a folder at the repo root (e.g. `kookaburra-surfing/`).
- Each experiment folder must contain a `prompt.md` recording the exact prompt.
- A model performs the prompt in `prompt.md` and writes its output as a **single file or folder named after that model** inside the experiment folder (e.g. `kookaburra-surfing/claude-opus-5.svg`). Use a folder instead of a single file when the output is multi-part.
- Default language: Python; env/package management: `uv`.
- No other commands exist to document yet; if they appear, add them here.
- An experiment folder may also hold reference assets (e.g. `littlecove/little-cove.jpg`), with provenance in `photo-credit.md`. These are for comparing outputs against; a model only uses one if `prompt.md` asks it to.
- Models may NOT look inside other experiment folders. Each model may only read `AGENTS.md`, `README`, and the folder of the experiment it is running.
