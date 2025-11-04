# Proxtract

Proxtract is an interactive CLI for extracting readable project files into a single bundle that is easy to share with large language models.

## Features
- Rich-powered REPL with colorized output, tables, and progress indicators
- Session state for configurable extraction settings
- Command suite for quick extraction, configuration, and help

## Installation

```bash
pip install proxtract
```

Install with the optional ASCII art banner extras by adding `banner`:

```bash
pip install proxtract[banner]
```

## Usage

Launch the REPL with:

```bash
proxtract
```

Or reach for the compact alias:

```bash
prx
```

Inside the session use `/help` to see available commands. Typical flow:

1. Adjust defaults with `/settings` if needed.
2. Run `/extract <path> [output_file]` to stream project files into one document.
3. Exit anytime with `/exit`.

Settings keys accept handy aliases: `/settings max 1024`, `/settings out merged.txt`, `/settings compact off`, `/settings empty on`.

Run a one-off extraction directly from the shell with the short form:

```bash
prx e path/to/project -o bundle.txt
```

### Shell Tab Completion

Shell tab-completion for commands, options, and path arguments is available via
`argcomplete`. After installing Proxtract, enable completion (bash/zsh/fish) with:

```bash
register-python-argcomplete proxtract prx >> ~/.bashrc  # adapt for your shell
```

Restart your shell (or source the file) and enjoy tab-completion for both `proxtract`
and `prx`.

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

For editable development installs, use:

```bash
pip install -e .[dev,banner]
```

## Publishing to PyPI

1. Ensure `dist/` is clean: `rm -rf dist/ build/`
2. Build the distribution artifacts: `python -m build`
3. Inspect the generated wheels and sdist under `dist/`
4. Run a sanity check: `twine check dist/*`
5. Upload to PyPI (or TestPyPI) with `twine upload dist/*`
