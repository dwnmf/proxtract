"""Prompt-toolkit completer for the Proxtract CLI."""

from __future__ import annotations

from dataclasses import dataclass
import shlex
from typing import Dict, Iterable, Mapping, Sequence

from prompt_toolkit.completion import Completer, Completion, PathCompleter
from prompt_toolkit.document import Document


BOOLEAN_CHOICES: Sequence[str] = ("on", "off", "true", "false", "yes", "no", "1", "0")
EXTRACT_FLAGS: Sequence[str] = (
    "--output",
    "-o",
    "--max-size",
    "--compact",
    "--no-compact",
    "--skip-empty",
    "--no-skip-empty",
    "--copy",
)
INCLUDE_SUBCOMMANDS: Sequence[str] = ("list", "add", "remove", "clear")
EXCLUDE_SUBCOMMANDS: Sequence[str] = ("list", "add", "remove", "clear")


@dataclass(frozen=True)
class _AliasLookup:
    aliases: Dict[str, str]
    tokens: Sequence[str]


def _build_alias_lookup(mapping: Mapping[str, Iterable[str]]) -> _AliasLookup:
    aliases: Dict[str, str] = {}
    all_tokens: set[str] = set()
    for canonical, values in mapping.items():
        for value in values:
            lowered = value.lower()
            aliases[lowered] = canonical
            all_tokens.add(value)
    return _AliasLookup(aliases=aliases, tokens=tuple(sorted(all_tokens)))


def _tokenize_command(line: str) -> list[str]:
    """Split *line* emulating shlex while tolerating incomplete input."""

    lexer = shlex.shlex(line, posix=True)
    lexer.whitespace_split = True
    lexer.escape = "\\"

    tokens: list[str] = []
    try:
        while True:
            token = lexer.get_token()
            if token == lexer.eof:
                break
            tokens.append(token)
    except ValueError:
        # When the user types an unfinished quoted fragment, capture it raw.
        if lexer.token:
            tokens.append(lexer.token)
    return tokens


def _split_assignment(token: str) -> tuple[str, str | None]:
    if "=" in token:
        key, value = token.split("=", 1)
        return key, value
    return token, None


class CommandCompleter(Completer):
    """Provide tab autocompletion for the interactive prompt."""

    def __init__(self, commands: Iterable[str], setting_aliases: Mapping[str, Iterable[str]]):
        self._commands = tuple(sorted(commands))
        self._command_set = frozenset(commands)
        self._alias_lookup = _build_alias_lookup(setting_aliases)
        self._path_completer = PathCompleter(expanduser=True)

    # region helpers ---------------------------------------------------------
    def _complete_commands(self, fragment: str) -> Iterable[Completion]:
        start = -len(fragment)
        for command in self._commands:
            if command.startswith(fragment):
                yield Completion(command, start_position=start)

    def _complete_setting_keys(self, fragment: str) -> Iterable[Completion]:
        start = -len(fragment)
        lowered = fragment.lower()
        for token in self._alias_lookup.tokens:
            if token.lower().startswith(lowered):
                yield Completion(token, start_position=start)

    def _complete_boolean(self, fragment: str) -> Iterable[Completion]:
        start = -len(fragment)
        for option in BOOLEAN_CHOICES:
            if option.startswith(fragment.lower()):
                yield Completion(option, start_position=start)

    def _complete_path(self, fragment: str, complete_event) -> Iterable[Completion]:
        leading_quote = fragment[:1] if fragment[:1] in {'"', "'"} else ""
        sanitized = fragment[1:] if leading_quote else fragment

        document = Document(sanitized, len(sanitized))
        for completion in self._path_completer.get_completions(document, complete_event):
            text = completion.text
            if leading_quote and len(text) >= 2 and text[0] == leading_quote and text[-1] == leading_quote:
                text = text[1:-1]

            yield Completion(
                text,
                start_position=-len(sanitized),
                display=completion.display,
                display_meta=completion.display_meta,
                style=getattr(completion, "style", ""),
                selected_style=getattr(completion, "selected_style", ""),
            )

    def _resolve_setting(self, raw: str) -> str | None:
        key = raw.split("=", 1)[0].lower()
        return self._alias_lookup.aliases.get(key)

    def _complete_setting_value(self, target: str, fragment: str, complete_event) -> Iterable[Completion]:
        if target in {"compact", "skip_empty", "use_gitignore", "token_count", "copy_clipboard"}:
            yield from self._complete_boolean(fragment)
        elif target == "output":
            yield from self._complete_path(fragment, complete_event)
        elif target == "tokenizer_model":
            options = ("gpt-4", "gpt-4o", "gpt-3.5-turbo")
            start = -len(fragment)
            for option in options:
                if option.startswith(fragment):
                    yield Completion(option, start_position=start)

    # endregion --------------------------------------------------------------

    def get_completions(self, document: Document, complete_event):
        line = document.current_line_before_cursor

        if not line.strip():
            yield from self._complete_commands("")
            return

        trailing_space = bool(line) and line[-1].isspace()
        parts = _tokenize_command(line)
        if trailing_space:
            parts.append("")

        if not parts:
            yield from self._complete_commands("")
            return

        command_fragment = parts[0]

        if len(parts) == 1 and not trailing_space:
            yield from self._complete_commands(command_fragment)
            return

        command = command_fragment
        if command not in self._command_set:
            yield from self._complete_commands(command_fragment)
            return

        args = parts[1:]
        if not args:
            yield from self._complete_commands("")
            return

        current_arg = args[-1]
        arg_index = len(args) - 1

        if command in {"/help", "/exit", "/quit", "/clear"}:
            return

        if command == "/extract":
            if len(args) == 1:
                frag = current_arg
                if frag.startswith("-"):
                    for flag in EXTRACT_FLAGS:
                        if flag.startswith(frag):
                            yield Completion(flag, start_position=-len(frag))
                else:
                    yield from self._complete_path(frag, complete_event)
                    for flag in EXTRACT_FLAGS:
                        if flag.startswith(frag):
                            yield Completion(flag, start_position=-len(frag))
                return

            prev_token = args[-2] if len(args) >= 2 else ""

            if current_arg.startswith("-"):
                for flag in EXTRACT_FLAGS:
                    if flag.startswith(current_arg):
                        yield Completion(flag, start_position=-len(current_arg))
                return

            if prev_token in {"--output", "-o"}:
                yield from self._complete_path(current_arg, complete_event)
                return

            yield from self._complete_path(current_arg, complete_event)
            return

        if command == "/settings":
            key_token = args[0]
            key_fragment, inline_value_fragment = _split_assignment(key_token)
            target = self._resolve_setting(key_token)

            if arg_index == 0:
                if inline_value_fragment is None:
                    yield from self._complete_setting_keys(key_fragment)
                elif target is not None:
                    yield from self._complete_setting_value(target, inline_value_fragment, complete_event)
                return

            if target is None:
                yield from self._complete_setting_keys(key_fragment)
                return

            value_fragment = current_arg
            if inline_value_fragment is not None and arg_index == 1 and current_arg == "":
                value_fragment = inline_value_fragment

            yield from self._complete_setting_value(target, value_fragment, complete_event)
            return

        if command == "/include":
            if len(args) <= 1:
                frag = current_arg
                for option in INCLUDE_SUBCOMMANDS:
                    if option.startswith(frag):
                        yield Completion(option, start_position=-len(frag))
                return
            return

        if command == "/exclude":
            if len(args) <= 1:
                frag = current_arg
                for option in EXCLUDE_SUBCOMMANDS:
                    if option.startswith(frag):
                        yield Completion(option, start_position=-len(frag))
                return
            return
