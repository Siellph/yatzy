from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from yatzy.lan_sync import format_token, mask_code_input
from yatzy.ui.widgets import body

_DIALOG_WIDTH = 320


def _dialog_block(*controls: ft.Control) -> ft.Column:
    return ft.Column(
        list(controls),
        tight=True,
        spacing=12,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        width=_DIALOG_WIDTH,
    )


def _note(text: str) -> ft.Text:
    return ft.Text(
        text,
        size=13,
        color=ft.Colors.ON_SURFACE_VARIANT,
        text_align=ft.TextAlign.CENTER,
        width=_DIALOG_WIDTH,
    )

if TYPE_CHECKING:
    from yatzy.app import YatzyApp


def open_sync_menu(app: YatzyApp) -> None:
    app.page.show_dialog(
        ft.AlertDialog(
            title=ft.Text("Синхронизация по Wi‑Fi"),
            content=ft.Column(
                [
                    body("Оба устройства в одной сети. Один показывает код, второй его вводит.", muted=True),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.WIFI_TETHERING),
                        title=ft.Text("Показать код"),
                        subtitle=ft.Text("Это устройство раздаёт турниры"),
                        on_click=lambda _e: _open_host(app),
                    ),
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.KEYBOARD),
                        title=ft.Text("Ввести код"),
                        subtitle=ft.Text("Забрать турниры с другого устройства"),
                        on_click=lambda _e: _open_guest(app),
                    ),
                ],
                tight=True,
                spacing=0,
            ),
            actions=[ft.TextButton("Закрыть", on_click=lambda _e: app.page.pop_dialog())],
        )
    )


def _open_host(app: YatzyApp) -> None:
    app.page.pop_dialog()
    host = app.start_lan_host()
    if host is None:
        return
    app.page.show_dialog(
        ft.AlertDialog(
            title=ft.Text("Покажите этот код"),
            content=_dialog_block(
                ft.Text(
                    format_token(host.token),
                    size=36,
                    weight=ft.FontWeight.W_800,
                    text_align=ft.TextAlign.CENTER,
                    width=_DIALOG_WIDTH,
                ),
                _note("На втором устройстве: синхронизация → ввести код."),
                ft.TextField(
                    label="Если не находится, введите целиком",
                    value=host.invite,
                    read_only=True,
                    text_align=ft.TextAlign.CENTER,
                    width=_DIALOG_WIDTH,
                ),
            ),
            actions=[ft.TextButton("Закрыть", on_click=lambda _e: app.stop_lan_host())],
        )
    )


def _open_guest(app: YatzyApp) -> None:
    app.page.pop_dialog()

    def reformat(event: ft.Event[ft.TextField]) -> None:
        formatted = mask_code_input(event.control.value or "")
        if event.control.value != formatted:
            event.control.value = formatted
            event.control.update()

    field = ft.TextField(
        label="Код",
        hint_text="AB 23 CD",
        autofocus=True,
        text_align=ft.TextAlign.CENTER,
        content_padding=ft.Padding.symmetric(horizontal=20, vertical=14),
        capitalization=ft.TextCapitalization.CHARACTERS,
        autocorrect=False,
        enable_suggestions=False,
        width=_DIALOG_WIDTH,
        on_change=reformat,
        on_submit=lambda _e: app.page.run_task(app.join_lan_sync, field.value or ""),
    )
    app.page.show_dialog(
        ft.AlertDialog(
            title=ft.Text("Введите код"),
            content=_dialog_block(
                _note("Код с другого экрана. Если не находится — скопируйте строку целиком."),
                field,
                _note("Как на другом экране, либо адрес целиком."),
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _e: app.page.pop_dialog()),
                ft.Button(
                    "Подключить",
                    icon=ft.Icons.SYNC,
                    on_click=lambda _e: app.page.run_task(app.join_lan_sync, field.value or ""),
                ),
            ],
        )
    )
