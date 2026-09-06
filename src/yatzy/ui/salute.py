from __future__ import annotations

import asyncio

import flet as ft

from yatzy.ru import ru_form
from yatzy.theme import GOAL_GLOW


def show_goal_salute(page: ft.Page, teams: list[tuple[str, int, str]]) -> None:
    if not teams:
        return
    sparks_top = _sparks()
    sparks_bottom = _sparks()
    cards = [
        ft.Column(
            [
                ft.Text(name, size=28, weight=ft.FontWeight.W_800, color=color, text_align=ft.TextAlign.CENTER),
                ft.Text(f"{score}", size=42, weight=ft.FontWeight.W_800, color=GOAL_GLOW, text_align=ft.TextAlign.CENTER),
                ft.Text(
                    f"{ru_form(score, 'очко', 'очка', 'очков')} · цель взята",
                    size=14,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2,
            tight=True,
        )
        for name, score, color in teams
    ]
    layer = ft.Container(
        expand=True,
        bgcolor=ft.Colors.with_opacity(0.72, ft.Colors.BLACK),
        alignment=ft.Alignment.CENTER,
        on_click=lambda _e: _dismiss(page, layer),
        content=ft.Column(
            [
                ft.Row(sparks_top, alignment=ft.MainAxisAlignment.CENTER, wrap=True, spacing=10, run_spacing=10),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.Icons.AUTO_AWESOME, size=36, color=GOAL_GLOW),
                            ft.Text("Салют!", size=18, weight=ft.FontWeight.W_700, color=GOAL_GLOW),
                            *cards,
                            ft.Text("Нажмите, чтобы закрыть", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                        tight=True,
                    ),
                    padding=ft.Padding.symmetric(horizontal=28, vertical=24),
                    border_radius=24,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                    border=ft.Border.all(1, GOAL_GLOW),
                ),
                ft.Row(sparks_bottom, alignment=ft.MainAxisAlignment.CENTER, wrap=True, spacing=10, run_spacing=10),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=18,
            tight=True,
        ),
    )
    page.overlay.append(layer)
    page.update()
    page.run_task(_auto_dismiss, page, layer)


def _sparks() -> list[ft.Control]:
    dots = (
        (10, "#F4C96B"),
        (8, "#E07A7A"),
        (12, "#6C8CFF"),
        (9, "#2BB8A3"),
        (7, "#C086E8"),
        (8, "#F2A65A"),
        (11, "#6FCF97"),
        (8, "#E8B86D"),
        (10, "#4ECDC4"),
        (7, "#9B7EDE"),
    )
    icons = (
        ft.Icon(ft.Icons.AUTO_AWESOME, size=18, color="#F4C96B"),
        ft.Icon(ft.Icons.STAR, size=16, color="#E8B86D"),
        ft.Icon(ft.Icons.CELEBRATION, size=18, color="#E07A7A"),
    )
    chips = [ft.Container(width=size, height=size, border_radius=999, bgcolor=color) for size, color in dots]
    return [*icons, *chips]


def _dismiss(page: ft.Page, layer: ft.Control) -> None:
    if layer in page.overlay:
        page.overlay.remove(layer)
        page.update()


async def _auto_dismiss(page: ft.Page, layer: ft.Control) -> None:
    await asyncio.sleep(3.4)
    _dismiss(page, layer)
