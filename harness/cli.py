"""The `sillybench` CLI: `uv run sillybench --help`.

Each subcommand's code lives in its own module; this file only wires them
into one Typer app, which pyproject.toml exposes as the `sillybench` script.
"""

import typer

from harness import gallery, run

# no locals in tracebacks: `run` holds the provider's api key
app = typer.Typer(add_completion=False, no_args_is_help=True,
                  pretty_exceptions_show_locals=False,
                  help="Silly benchmarks to test models on.")
app.command("run")(run.main)
app.command("gallery")(gallery.main)
