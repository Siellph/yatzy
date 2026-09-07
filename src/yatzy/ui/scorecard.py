from __future__ import annotations

from collections.abc import Callable

import flet as ft

from yatzy.models import (
    ALL_CATEGORIES,
    LOWER_CATEGORIES,
    ROUNDS_PER_MATCH,
    UPPER_CATEGORIES,
    Category,
    Game,
    Team,
)
from yatzy.ru import ru_count, ru_one
from yatzy.theme import LOSS, WIN, team_color
from yatzy.ui.widgets import body, progress_bar, team_badge


def game_header(game: Game, teams: list[tuple[str, Team]], goal: int) -> ft.Control:
    winner = game.winner_side()
    scores = [
        ft.Container(
            _team_score(team.name, key, game.team_total(key), goal, winner == key, team.color),
            col={"xs": 12, "sm": 6, "md": 4 if len(teams) > 2 else 6},
        )
        for key, team in teams
    ]
    return ft.Column(
        [
            ft.ResponsiveRow(scores, spacing=12, run_spacing=12),
            body(_match_status(game, teams, goal), muted=True),
        ],
        spacing=10,
        tight=True,
    )


def scorecard_width(compact: bool, rounds: int = 3) -> int:
    label_width = 118 if compact else 150
    cell_width = 58 if compact else 72
    return label_width + rounds * cell_width + 4 * rounds + 22


def build_scorecard(
    game: Game,
    team: Team,
    side: str,
    compact: bool,
    on_edit: Callable[[str, int], None],
) -> ft.Control:
    columns = game.columns(side)
    label_width = 118 if compact else 150
    cell_width = 58 if compact else 72
    rows: list[ft.Control] = [
        team_badge(team.name, side, color=team.color),
        _header_row(team, side, columns, label_width, cell_width),
        _stage_row("1 этап", label_width, cell_width, len(columns)),
    ]
    for category in UPPER_CATEGORIES:
        rows.append(_category_row(category, columns, side, label_width, cell_width, on_edit, team.color))
    rows.extend(
        [
            _computed_row("Итого", [item.totals().upper for item in columns], label_width, cell_width),
            _computed_row(
                "До премии",
                [item.totals().to_bonus for item in columns],
                label_width,
                cell_width,
                emphasize=True,
            ),
            _computed_row("Премия 35", [item.totals().bonus for item in columns], label_width, cell_width),
            _computed_row("Сумма 1 этапа", [item.totals().stage1 for item in columns], label_width, cell_width, bold=True),
            _stage_row("2 этап", label_width, cell_width, len(columns)),
        ]
    )
    for category in LOWER_CATEGORIES:
        rows.append(_category_row(category, columns, side, label_width, cell_width, on_edit, team.color))
    rows.extend(
        [
            _computed_row("Сумма 2 этапа", [item.totals().stage2 for item in columns], label_width, cell_width),
            _computed_row("Итого", [item.totals().total for item in columns], label_width, cell_width, bold=True),
            _igogo_row(game.team_total(side), side, label_width, cell_width, len(columns), team.color),
        ]
    )
    return ft.Container(
        content=ft.Column(rows, spacing=4, tight=True),
        expand=True,
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        border=ft.Border.all(1, ft.Colors.with_opacity(0.55, team_color(side, team.color))),
        border_radius=18,
        padding=12,
    )


def _team_score(name: str, side: str, total: int, goal: int, is_winner: bool, tint: str = "") -> ft.Control:
    color = team_color(side, tint)
    return ft.Container(
        content=ft.Column(
            [
                team_badge(name, side, color=tint),
                ft.Text(str(total), size=28, weight=ft.FontWeight.W_800, color=color),
                progress_bar(total / goal if goal else 0, color),
                ft.Text(
                    f"цель {goal}" + (" · лидер" if is_winner else ""),
                    size=12,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            spacing=4,
            tight=True,
        ),
        expand=True,
    )


def _match_status(game: Game, teams: list[tuple[str, Team]], goal: int) -> str:
    if not game.is_started():
        return (
            f"{ru_count(ROUNDS_PER_MATCH, 'раунд', 'раунда', 'раундов')} · "
            f"цель {ru_count(goal, 'очко', 'очка', 'очков')} за матч"
        )
    scores = [(team.name, game.team_total(key)) for key, team in teams]
    winner = game.winner_side()
    leader = next((team.name for key, team in teams if key == winner), None)
    if leader is None:
        lead = "Ничья"
    else:
        best = max(score for _name, score in scores)
        rest = [score for _name, score in scores if score != best]
        gap = best - max(rest) if rest else 0
        lead = f"{leader} впереди на {ru_count(gap, 'очко', 'очка', 'очков')}"
    reached = [name for name, total in scores if total >= goal]
    extra = f" · цель {goal} у {' и '.join(reached)}" if reached else ""
    return lead + extra


def _round_title(label: str) -> str:
    return label


def _score_row(label: ft.Control, cells: list[ft.Control], top: int = 0) -> ft.Control:
    row = ft.Row(
        [
            label,
            ft.Row(cells, spacing=4, alignment=ft.MainAxisAlignment.CENTER, expand=True),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    if top:
        return ft.Container(content=row, padding=ft.Padding.only(top=top))
    return row


def _header_row(team: Team, side: str, columns, label_width: int, cell_width: int) -> ft.Control:
    cells = [_cell(_round_title(column.name), cell_width, muted=True, weight=ft.FontWeight.W_700) for column in columns]
    return _score_row(
        _label_box("Раунд", label_width, weight=ft.FontWeight.W_700, color=team_color(side, team.color)),
        cells,
    )


def _stage_row(title: str, label_width: int, cell_width: int, count: int) -> ft.Control:
    return _score_row(
        _label_box(title, label_width, weight=ft.FontWeight.W_700),
        [_cell("", cell_width) for _ in range(count)],
        top=8,
    )


def _category_row(
    category: Category,
    columns,
    side: str,
    label_width: int,
    cell_width: int,
    on_edit: Callable[[str, int], None],
    tint: str = "",
) -> ft.Control:
    cells = [
        _score_cell(
            column.get(category.key),
            cell_width,
            color=team_color(side, tint),
            on_click=lambda _e, key=category.key, idx=index: on_edit(key, idx),
            caption=column.yatzy_player_name if category.key == "yatzy" and column.get(category.key) == 50 else None,
        )
        for index, column in enumerate(columns)
    ]
    return _score_row(_category_label(category, label_width), cells)


def _computed_row(
    title: str,
    values: list[int],
    label_width: int,
    cell_width: int,
    bold: bool = False,
    emphasize: bool = False,
) -> ft.Control:
    cells = []
    for value in values:
        color = None
        if emphasize:
            color = WIN if value <= 0 else LOSS
        cells.append(
            _cell(
                str(value),
                cell_width,
                weight=ft.FontWeight.W_700 if bold else None,
                color=color,
            )
        )
    return _score_row(
        _label_box(title, label_width, weight=ft.FontWeight.W_600 if bold else None),
        cells,
    )


def _igogo_row(total: int, side: str, label_width: int, cell_width: int, count: int, tint: str = "") -> ft.Control:
    color = team_color(side, tint)
    return _score_row(
        _label_box("ИГОГО", label_width, weight=ft.FontWeight.W_800, color=color),
        [
            ft.Container(
                content=ft.Text(
                    str(total),
                    size=18,
                    weight=ft.FontWeight.W_800,
                    color=color,
                    text_align=ft.TextAlign.CENTER,
                ),
                width=cell_width * count + 4 * (count - 1),
                height=40,
                alignment=ft.Alignment.CENTER,
                bgcolor=ft.Colors.with_opacity(0.12, color),
                border_radius=10,
            )
        ],
        top=4,
    )


def _category_label(category: Category, width: int) -> ft.Control:
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(category.title, size=13, weight=ft.FontWeight.W_600, max_lines=1),
                ft.Text(category.hint, size=10, color=ft.Colors.ON_SURFACE_VARIANT, max_lines=1),
            ],
            spacing=0,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.START,
        ),
        width=width,
        padding=ft.Padding.symmetric(horizontal=4, vertical=2),
        alignment=ft.Alignment.CENTER_LEFT,
    )


def _label_box(
    text: str,
    width: int,
    weight: ft.FontWeight | None = None,
    color: str | None = None,
) -> ft.Control:
    return ft.Container(
        content=ft.Text(text, size=13, weight=weight, color=color, max_lines=1, text_align=ft.TextAlign.LEFT),
        width=width,
        height=36,
        alignment=ft.Alignment.CENTER_LEFT,
        padding=ft.Padding.symmetric(horizontal=4),
    )


def _score_cell(
    value: int | None,
    width: int,
    color: str,
    on_click: Callable,
    caption: str | None = None,
) -> ft.Control:
    empty = value is None
    label = ft.Text(
        "—" if empty else str(value),
        size=15,
        weight=ft.FontWeight.W_700,
        color=ft.Colors.ON_SURFACE_VARIANT if empty else color,
    )
    content: ft.Control = label
    if caption:
        content = ft.Column(
            [
                label,
                ft.Text(
                    caption,
                    size=9,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            spacing=0,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
    return ft.Container(
        content=content,
        width=width,
        height=44 if caption else 40,
        alignment=ft.Alignment.CENTER,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST if empty else ft.Colors.with_opacity(0.12, color),
        border_radius=10,
        ink=True,
        on_click=on_click,
    )


def _cell(
    text: str,
    width: int,
    muted: bool = False,
    weight: ft.FontWeight | None = None,
    color: str | None = None,
) -> ft.Control:
    return ft.Container(
        content=ft.Text(
            text,
            size=13,
            weight=weight,
            color=color or (ft.Colors.ON_SURFACE_VARIANT if muted else None),
            text_align=ft.TextAlign.CENTER,
        ),
        width=width,
        height=36,
        alignment=ft.Alignment.CENTER,
    )


def filled_hint(game: Game) -> str:
    columns = game.all_columns()
    filled = sum(column.totals().filled for column in columns)
    total = len(ALL_CATEGORIES) * len(columns)
    verb = "Заполнена" if ru_one(filled) else "Заполнено"
    return f"{verb} {ru_count(filled, 'клетка', 'клетки', 'клеток')} из {total}"
