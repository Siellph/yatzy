from __future__ import annotations

from collections.abc import Callable

import flet as ft

from yatzy.models import (
    DICE_COUNT,
    SUM_MAX,
    SUM_MIN,
    Category,
    ScoreKind,
    TeamPlayer,
    suggested_score,
)
from yatzy.ru import ru_count


def open_score_dialog(
    page: ft.Page,
    category: Category,
    round_label: str,
    current: int | None,
    on_save: Callable[..., None],
    players: list[TeamPlayer] | None = None,
    yatzy_player_id: str | None = None,
) -> None:
    if category.key == "yatzy":
        content = _yatzy_picker(category, current, on_save, page, players or [], yatzy_player_id)
    elif category.kind == ScoreKind.COUNT:
        content = _count_picker(category, current, on_save, page)
    elif category.kind == ScoreKind.FIXED:
        content = _fixed_picker(category, current, on_save, page)
    else:
        content = _sum_picker(category, current, on_save, page)

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(f"{category.title} · раунд {round_label}"),
        content=ft.Container(content=content, width=460),
        content_padding=ft.Padding.only(left=20, right=20, top=8, bottom=4),
        actions_padding=ft.Padding.only(left=12, right=12, bottom=10, top=4),
        inset_padding=ft.Padding.symmetric(horizontal=24, vertical=32),
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        actions=[
            ft.TextButton("Очистить клетку", on_click=lambda _e: _save(page, on_save, None)),
            ft.TextButton("Закрыть", on_click=lambda _e: _close(page)),
        ],
    )
    page.show_dialog(dialog)


def _close(page: ft.Page) -> None:
    page.pop_dialog()


def _save(
    page: ft.Page,
    callback: Callable[..., None],
    value: int | None,
    player: TeamPlayer | None = None,
) -> None:
    _close(page)
    callback(value, player)


def _choice_row(controls: list[ft.Control]) -> ft.Control:
    return ft.Row(
        controls,
        wrap=True,
        spacing=8,
        run_spacing=8,
        alignment=ft.MainAxisAlignment.CENTER,
    )


def _choice_button(label: str, selected: bool, on_click: Callable) -> ft.Button:
    return ft.Button(
        label,
        on_click=on_click,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.PRIMARY_CONTAINER if selected else None,
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
        ),
    )


def _count_picker(
    category: Category,
    current: int | None,
    on_save: Callable[..., None],
    page: ft.Page,
) -> ft.Control:
    buttons = [
        _choice_button(
            f"{count} × {category.face} = {suggested_score(category, count)}",
            current == suggested_score(category, count),
            lambda _e, value=suggested_score(category, count): _save(page, on_save, value),
        )
        for count in range(DICE_COUNT + 1)
    ]
    return ft.Column(
        [
            ft.Text(
                f"{category.hint} · {ru_count(DICE_COUNT, 'кубик', 'кубика', 'кубиков')}",
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Text("Сколько таких костей выпало?", size=13),
            _choice_row(buttons),
        ],
        tight=True,
        spacing=8,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _fixed_picker(
    category: Category,
    current: int | None,
    on_save: Callable[..., None],
    page: ft.Page,
) -> ft.Control:
    score = category.fixed_score or 0
    return ft.Column(
        [
            ft.Text(category.hint, color=ft.Colors.ON_SURFACE_VARIANT),
            _choice_row(
                [
                    _choice_button(
                        f"Засчитать {score}",
                        current == score,
                        lambda _e: _save(page, on_save, score),
                    ),
                    ft.OutlinedButton(
                        "Списать 0",
                        icon=ft.Icons.BLOCK,
                        on_click=lambda _e: _save(page, on_save, 0),
                    ),
                ]
            ),
        ],
        tight=True,
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _yatzy_picker(
    category: Category,
    current: int | None,
    on_save: Callable[..., None],
    page: ft.Page,
    players: list[TeamPlayer],
    yatzy_player_id: str | None,
) -> ft.Control:
    score = category.fixed_score or 50
    chips = [
        _choice_button(
            player.name,
            current == score and player.id == yatzy_player_id,
            lambda _e, item=player: _save(page, on_save, score, item),
        )
        for player in players
    ]
    if players:
        who: list[ft.Control] = [
            ft.Text("Кто выкинул яцзы?", size=13, weight=ft.FontWeight.W_600),
            _choice_row(chips),
        ]
    else:
        who = [
            ft.Text(
                "Добавьте имена в состав команды — тогда яцзы можно будет записать на игрока и собрать статистику.",
                size=13,
                color=ft.Colors.ON_SURFACE_VARIANT,
                text_align=ft.TextAlign.CENTER,
            ),
            _choice_button(
                f"Засчитать {score} без имени",
                current == score,
                lambda _e: _save(page, on_save, score),
            ),
        ]
    return ft.Column(
        [
            ft.Text(category.hint, color=ft.Colors.ON_SURFACE_VARIANT),
            *who,
            _choice_row(
                [
                    ft.OutlinedButton(
                        "Списать 0",
                        icon=ft.Icons.BLOCK,
                        on_click=lambda _e: _save(page, on_save, 0),
                    ),
                ]
            ),
        ],
        tight=True,
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _sum_picker(
    category: Category,
    current: int | None,
    on_save: Callable[..., None],
    page: ft.Page,
) -> ft.Control:
    field = ft.TextField(
        label=f"Сумма {ru_count(DICE_COUNT, 'кость', 'кости', 'костей')}",
        value="" if current is None else str(current),
        keyboard_type=ft.KeyboardType.NUMBER,
        autofocus=True,
        input_filter=ft.InputFilter(regex_string=r"[0-9]*"),
        helper=f"От {SUM_MIN} до {SUM_MAX}, либо 0 если списать",
    )

    def commit(_e: ft.Event[ft.Button] | None = None) -> None:
        raw = (field.value or "").strip()
        if raw == "":
            _save(page, on_save, None)
            return
        number = int(raw)
        if number != 0 and (number < SUM_MIN or number > SUM_MAX):
            field.error = (
                f"Только 0 или {SUM_MIN}–{SUM_MAX}: в игре "
                f"{ru_count(DICE_COUNT, 'кубик', 'кубика', 'кубиков')}"
            )
            page.update()
            return
        field.error = None
        _save(page, on_save, number)

    chips = [
        ft.Container(
            content=ft.Text(str(preset), weight=ft.FontWeight.W_600),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            on_click=lambda _e, value=preset: _save(page, on_save, value),
        )
        for preset in (0, 15, 18, 20, 22, 24, 25, 26, 28, 30)
    ]

    return ft.Column(
        [
            ft.Text(f"{category.hint} · максимум {SUM_MAX}", color=ft.Colors.ON_SURFACE_VARIANT),
            field,
            _choice_row(chips),
            ft.Button("Сохранить", on_click=commit),
        ],
        tight=True,
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )
