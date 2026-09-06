from __future__ import annotations

import flet as ft

from yatzy.app import YatzyApp


def main(page: ft.Page) -> None:
    YatzyApp(page).start()


def run() -> None:
    ft.run(main)


if __name__ == "__main__":
    run()
