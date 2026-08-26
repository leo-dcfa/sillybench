# sillybench — agent notes

- Brand-new benchmark repo; no build/test/lint/config yet.
- Each **experiment** = a folder at the repo root (e.g. `kookaburra-surfing/`).
- Each experiment folder must contain a `prompt.md` recording the exact prompt.
- A model performs the prompt in `prompt.md` and writes its output as a **single file or folder named after that model** inside the experiment folder (e.g. `kookaburra-surfing/claude-opus-5.svg`). Use a folder instead of a single file when the output is multi-part.
- Default language: Python; env/package management: `uv`.
- No other commands exist to document yet; if they appear, add them here.
- An experiment folder may also hold reference assets the prompt points at (e.g. `littlecove/little-cove.jpg`), with provenance in `photo-credit.md`. Vision experiments only run on multimodal models.
- Models may NOT look inside other experiment folders. Each model may only read `AGENTS.md`, `README`, and the folder of the experiment it is running.
