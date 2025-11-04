"""Lightweight headless smoketest for the Proxtract Textual app."""

from __future__ import annotations

import asyncio

from proxtract.state import AppState
from proxtract.tui.app import ProxtractApp


async def _run() -> None:
    app = ProxtractApp(AppState())
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("q")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
