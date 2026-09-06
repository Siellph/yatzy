from __future__ import annotations

from dataclasses import dataclass

import flet as ft


TEAM_A = "#2BB8A3"
TEAM_B = "#F2A65A"
WIN = "#7DDB8C"
LOSS = "#E57373"
GOAL_GLOW = "#F4C96B"

TEAM_SWATCHES: tuple[str, ...] = (
    "#2BB8A3",
    "#F2A65A",
    "#6C8CFF",
    "#E07A7A",
    "#C086E8",
    "#6FCF97",
    "#4ECDC4",
    "#F27D6B",
    "#8B9BB4",
    "#E8B86D",
)

SWATCH_TITLES: dict[str, str] = {
    "#2BB8A3": "Бирюза",
    "#F2A65A": "Янтарь",
    "#6C8CFF": "Синий",
    "#E07A7A": "Коралл",
    "#C086E8": "Сирень",
    "#6FCF97": "Мята",
    "#4ECDC4": "Аква",
    "#F27D6B": "Персик",
    "#8B9BB4": "Графит",
    "#E8B86D": "Песок",
}


@dataclass(frozen=True, slots=True)
class ThemePalette:
    id: str
    title: str
    seed: str


THEME_PALETTES: tuple[ThemePalette, ...] = (
    ThemePalette("amber", "Янтарь", "#E8B86D"),
    ThemePalette("indigo", "Индиго", "#5B6CDB"),
    ThemePalette("teal", "Бирюза", "#2BB8A3"),
    ThemePalette("rose", "Роза", "#E07A7A"),
    ThemePalette("forest", "Лес", "#6BA368"),
    ThemePalette("violet", "Фиалка", "#9B7EDE"),
    ThemePalette("slate", "Графит", "#8B9BB4"),
)

DEFAULT_THEME_ID = THEME_PALETTES[0].id


def palette_by_id(theme_id: str | None) -> ThemePalette:
    for item in THEME_PALETTES:
        if item.id == theme_id:
            return item
    return THEME_PALETTES[0]


def apply_theme(page: ft.Page, mode: str, theme_id: str | None = None) -> None:
    seed = palette_by_id(theme_id).seed
    page.theme_mode = ft.ThemeMode.DARK if mode == "dark" else ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        color_scheme_seed=seed,
        use_material3=True,
        visual_density=ft.VisualDensity.STANDARD,
    )
    page.dark_theme = ft.Theme(
        color_scheme_seed=seed,
        use_material3=True,
        visual_density=ft.VisualDensity.STANDARD,
    )


def team_color(side: str, color: str | None = None) -> str:
    if color:
        return color
    if side == "a":
        return TEAM_A
    if side == "b":
        return TEAM_B
    return TEAM_SWATCHES[sum(ord(char) for char in side) % len(TEAM_SWATCHES)]
