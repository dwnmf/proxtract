# Proxtract

Proxtract is a Rich + prompt_toolkit powered CLI that extracts readable project files into a single bundle that is easy to share with large language models.

## Features
- Instant console REPL with history + Tab completion via `prompt_toolkit`
- Rich panels, tables, and progress bars for clear status updates
- Shared configuration state between the REPL and the traditional `extract` subcommand
- Optional persistence to `settings.toml` for quick reloads across sessions

## Installation

```bash
pip install proxtract
```

Install with the optional ASCII art banner extras by adding `banner`:

```bash
pip install proxtract[banner]
```

## Usage

Launching `proxtract` or `prx` without arguments opens the interactive REPL:

```bash
proxtract
```

At the prompt type `help` (or press `Tab`) to see the available commands:

| Command | Description |
| --- | --- |
| `extract [SOURCE] [OUTPUT]` | Run an extraction. Paths fallback to the current config and are prompted for when missing. |
| `set <key> <value>` | Update configuration. Keys: `source_path`, `output_path`, `max_size_kb`, `compact_mode`, `skip_empty`, `use_gitignore`, `force_include`, `include_patterns`, `exclude_patterns`, `count_tokens`, `tokenizer_model`, `copy_clipboard`. |
| `show` / `config` | Render the current settings table. |
| `save` | Persist settings to `~/.config/proxtract/settings.toml`. |
| `help` | Show the command list. |
| `exit` / `quit` | Leave the REPL. |

The REPL provides:
- Tab completion for commands, setting keys, boolean values, and filesystem paths.
- Arrow-key command history (stored under `~/.config/proxtract/history` when possible).
- Rich progress bars during extraction plus a summary table on completion.

### Scripted CLI

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

The script ensures the CLI help works and performs a one-file extraction using the public API.

## Development
- Python 3.9+
- Dependencies managed via `pyproject.toml`

Run the interactive REPL locally without installing by executing `python -m proxtract` from the project root. The banner gracefully falls back to ASCII art if the optional `art` dependency is unavailable.

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
