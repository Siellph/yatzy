from __future__ import annotations

from collections.abc import Callable

import flet as ft

from yatzy.theme import team_color


def card(*controls: ft.Control, padding: int = 16, expand: bool = False) -> ft.Container:
    return ft.Container(
        content=ft.Column(list(controls), spacing=10, tight=True),
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        border_radius=18,
        padding=padding,
        expand=expand,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
    )


def section_label(text: str) -> ft.Text:
    return ft.Text(
        text.upper(),
        size=12,
        weight=ft.FontWeight.W_600,
        color=ft.Colors.ON_SURFACE_VARIANT,
    )


def heading(text: str, size: int = 26) -> ft.Text:
    return ft.Text(text, size=size, weight=ft.FontWeight.W_700)


def body(text: str, muted: bool = False) -> ft.Text:
    return ft.Text(
        text,
        size=14,
        color=ft.Colors.ON_SURFACE_VARIANT if muted else ft.Colors.ON_SURFACE,
    )


def team_badge(name: str, side: str, large: bool = False, color: str | None = None) -> ft.Container:
    color = team_color(side, color)
    return ft.Container(
        content=ft.Text(
            name,
            size=16 if large else 13,
            weight=ft.FontWeight.W_700,
            color=color,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        ),
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        border_radius=999,
        bgcolor=ft.Colors.with_opacity(0.14, color),
    )


def progress_bar(value: float, color: str) -> ft.Control:
    return ft.Container(
        content=ft.ProgressBar(
            value=max(0.0, min(1.0, value)),
            color=color,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border_radius=8,
            bar_height=8,
        ),
        height=8,
        border_radius=8,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )


def icon_action(icon: ft.IconData, tooltip: str, on_click: Callable) -> ft.IconButton:
    return ft.IconButton(icon=icon, tooltip=tooltip, on_click=on_click)


def empty_state(icon: ft.IconData, title: str, text: str) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(icon, size=42, color=ft.Colors.ON_SURFACE_VARIANT),
                heading(title, 20),
                body(text, muted=True),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        ),
        padding=28,
        alignment=ft.Alignment.CENTER,
    )
