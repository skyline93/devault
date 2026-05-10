"""Control-plane admin CLI (database helpers). Human and API access is via IAM — use IAM for operators and API keys."""

from __future__ import annotations

import sys

import typer

from devault import __version__

app = typer.Typer(no_args_is_help=True, help="DeVault control-plane admin (legacy user/API-key commands removed; use IAM)")


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-V"):
        typer.echo(__version__)
        return
    app()


if __name__ == "__main__":
    main()
