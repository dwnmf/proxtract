# Proxtract

Proxtract is an interactive CLI for extracting readable project files into a single bundle that is easy to share with large language models.

## Features
- Rich-powered REPL with colorized output, tables, and progress indicators
- Session state for configurable extraction settings
- Command suite for quick extraction, configuration, and help

## Installation

```bash
pip install .
```

## Usage

Launch the REPL with:

```bash
proxtract
```

Inside the session use `/help` to see available commands. Typical flow:

1. Adjust defaults with `/settings` if needed.
2. Run `/extract <path> [output_file]` to stream project files into one document.
3. Exit anytime with `/exit`.

Settings keys accept handy aliases: `/settings max 1024`, `/settings out merged.txt`, `/settings compact off`, `/settings empty on`.

## Verification

After installing, you can confirm the basics operate with the bundled smoke test:

```bash
python scripts/smoke_test.py
```

The script launches the REPL (and exits cleanly) and performs a one-file extraction using the public API.

## Development
- Python 3.9+
- Dependencies managed via `pyproject.toml`

Run the REPL locally without installing by executing `python -m proxtract` from the project root. The banner gracefully falls back to ASCII art if the optional `art` dependency is unavailable.
