from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from yatzy.models import (
    DEFAULT_GOAL,
    DraftPlayer,
    MAX_PLAYERS,
    MAX_TEAMS,
    MIN_PLAYERS,
    MIN_TEAMS,
    ROUNDS_PER_MATCH,
    SetupTeam,
    Team,
    TeamPlayer,
    Tournament,
    create_tournament,
    new_id,
)
from yatzy.ru import ru_count
from yatzy.theme import GOAL_GLOW, SWATCH_TITLES, TEAM_SWATCHES, team_color
from yatzy.ui.scorecard import build_scorecard, filled_hint, game_header
from yatzy.ui.widgets import body, empty_state, heading, progress_bar, section_label, team_badge

if TYPE_CHECKING:
    from yatzy.app import YatzyApp


def home_screen(app: YatzyApp) -> ft.Control:
    if not app.state.tournaments:
        return ft.Column(
            [
                heading("Яцзы"),
                body("Создайте турнир кнопкой + или загрузите его из JSON.", muted=True),
                ft.Button("Добавить турнир", icon=ft.Icons.ADD, on_click=app.open_add_tournament_menu),
                ft.OutlinedButton("Синхронизация по Wi‑Fi", icon=ft.Icons.SYNC, on_click=app.open_sync_menu),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        )

    cards = [
        heading("Турниры"),
        body("Нажмите карточку, чтобы открыть турнир. Новый — кнопкой +.", muted=True),
    ]
    for tournament in app.state.tournaments:
        cards.append(_tournament_card(app, tournament))
    return ft.Column(cards, spacing=12, scroll=ft.ScrollMode.AUTO)


class SetupScreen:
    """Форма турнира: команды дописываются в ряд, без полной перерисовки экрана."""

    def __init__(self, app: YatzyApp, existing: Tournament | None) -> None:
        self.app = app
        self.existing = existing
        self._delete_buttons: list[ft.IconButton] = []
        _ensure_setup_draft(app, existing)
        self.teams_row = ft.ResponsiveRow(spacing=12, run_spacing=12)
        self.add_button = ft.OutlinedButton(
            "Добавить команду",
            icon=ft.Icons.GROUP_ADD,
            on_click=lambda _e: app.setup_add_team(),
        )
        self.control = ft.Column(
            [
                card(
                    heading("Новый турнир" if existing is None else "Редактирование турнира"),
                    body(
                        f"В матче {ru_count(ROUNDS_PER_MATCH, 'раунд', 'раунда', 'раундов')}. Имена игроков нужны для статистики яцзы.",
                        muted=True,
                    ),
                    ft.ResponsiveRow(
                        [
                            ft.Container(
                                ft.TextField(
                                    label="Название турнира",
                                    value=app.setup_name,
                                    on_change=lambda e: setattr(app, "setup_name", e.control.value or ""),
                                ),
                                col={"xs": 12, "md": 8},
                            ),
                            ft.Container(
                                ft.TextField(
                                    label="Цель, очки",
                                    value=app.setup_goal,
                                    keyboard_type=ft.KeyboardType.NUMBER,
                                    on_change=lambda e: setattr(app, "setup_goal", e.control.value or ""),
                                ),
                                col={"xs": 12, "md": 4},
                            ),
                        ],
                        spacing=12,
                        run_spacing=12,
                    ),
                ),
                section_label("Команды"),
                self.teams_row,
                self.add_button,
                ft.Button("Сохранить", icon=ft.Icons.CHECK, on_click=self._save),
            ],
            spacing=14,
            scroll=ft.ScrollMode.AUTO,
        )
        self.rebuild_teams()

    def rebuild_teams(self) -> None:
        self._delete_buttons.clear()
        self.teams_row.controls = [
            self._team_wrap(index, team) for index, team in enumerate(self.app.setup_teams)
        ]
        self._sync_chrome()

    def add_team_card(self) -> None:
        index = len(self.app.setup_teams) - 1
        self.teams_row.controls.append(self._team_wrap(index, self.app.setup_teams[index]))
        self._sync_chrome()

    def drop_team_card(self, team: SetupTeam) -> None:
        for index, wrap in enumerate(list(self.teams_row.controls)):
            if wrap.data is team:
                self.teams_row.controls.pop(index)
                self._delete_buttons.pop(index)
                break
        self._sync_chrome()

    def sync_players(self, team: SetupTeam) -> None:
        wrap = self._wrap_for(team)
        if wrap is None:
            return
        wrap.content.players_slot.content = _player_editor(self.app, team)

    def sync_color(self, team: SetupTeam) -> None:
        wrap = self._wrap_for(team)
        if wrap is None:
            return
        index = self.app.setup_teams.index(team)
        position = self.teams_row.controls.index(wrap)
        self.teams_row.controls[position] = self._team_wrap(index, team, replace_at=position)

    def _save(self, _e: ft.Event[ft.Button]) -> None:
        try:
            goal_value = int((self.app.setup_goal or str(DEFAULT_GOAL)).strip() or DEFAULT_GOAL)
        except ValueError:
            goal_value = DEFAULT_GOAL
        drafts = list(self.app.setup_teams)
        if len(drafts) < MIN_TEAMS:
            return
        if self.existing is None:
            self.app.state.add_tournament(_tournament_from_setup(self.app.setup_name, goal_value, drafts))
        else:
            self.existing.name = (self.app.setup_name or "Яцзы").strip()
            self.existing.goal = max(1, goal_value)
            _apply_setup_teams(self.existing, drafts)
        self.app.persist()
        self.app.open_tournament()

    def _team_wrap(self, index: int, team: SetupTeam, replace_at: int | None = None) -> ft.Container:
        card, delete_btn = _setup_team_card(self.app, index, team)
        if replace_at is None:
            self._delete_buttons.append(delete_btn)
        else:
            self._delete_buttons[replace_at] = delete_btn
        return ft.Container(card, col={"xs": 12, "sm": 6, "lg": 4}, data=team)

    def _wrap_for(self, team: SetupTeam) -> ft.Container | None:
        for wrap in self.teams_row.controls:
            if wrap.data is team:
                return wrap
        return None

    def _sync_chrome(self) -> None:
        enabled = len(self.app.setup_teams) > MIN_TEAMS
        for button in self._delete_buttons:
            button.disabled = not enabled
        self.add_button.disabled = len(self.app.setup_teams) >= MAX_TEAMS


def setup_screen(app: YatzyApp, existing: Tournament | None = None) -> ft.Control:
    view = getattr(app, "setup_view", None)
    if view is None or view.existing is not existing:
        view = SetupScreen(app, existing)
        app.setup_view = view
    return view.control


def tournament_screen(app: YatzyApp) -> ft.Control:
    tournament = app.state.active_tournament
    if tournament is None:
        return empty_state(ft.Icons.EMOJI_EVENTS_OUTLINED, "Нет турнира", "Создайте турнир, чтобы вести счёт.")

    games = []
    for game in tournament.games:
        games.append(_game_tile(app, game))

    return ft.Column(
        [
            heading(tournament.name),
            body(
                f"Цель матча — {ru_count(tournament.goal, 'очко', 'очка', 'очков')}. Победа в таблице — у кого больше ИГОГО.",
                muted=True,
            ),
            ft.ResponsiveRow(
                [
                    ft.Container(
                        _team_summary(tournament, key),
                        col={"xs": 12, "md": 6 if len(tournament.iter_teams()) <= 2 else 4},
                    )
                    for key, _team in tournament.iter_teams()
                ],
                spacing=12,
                run_spacing=12,
            ),
            card(
                section_label("Турнирная таблица"),
                _standings_table(tournament),
                spacing=False,
            ),
            card(
                section_label("Яцзы"),
                _yatzy_stats(tournament),
                spacing=False,
            ),
            ft.Row(
                [
                    section_label("Матчи"),
                    ft.TextButton("Новая игра", icon=ft.Icons.ADD, on_click=lambda _e: app.add_game()),
                    ft.TextButton("Редактировать", icon=ft.Icons.EDIT_OUTLINED, on_click=lambda _e: app.open_setup(edit=True)),
                ],
                wrap=True,
            ),
            *(games or [body("Пока нет игр.", muted=True)]),
        ],
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
    )


class GameScreen:
    def __init__(self, app: YatzyApp, compact: bool) -> None:
        self.app = app
        self.compact = compact
        self.game_id = app.state.active_game_id
        self.header = ft.Container()
        self.selector = ft.Row(spacing=8, wrap=True, run_spacing=8)
        self.hint = body("", muted=True)
        self.cards = ft.Container()
        self.control = ft.Column(
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self.sync()

    def matches(self, compact: bool) -> bool:
        return self.compact == compact and self.game_id == self.app.state.active_game_id

    def sync(self) -> None:
        tournament = self.app.state.active_tournament
        game = self.app.state.active_game
        if tournament is None or game is None:
            return
        self.game_id = game.id

        def edit(side: str):
            def handler(key: str, index: int) -> None:
                self.app.edit_score(side, index, key)

            return handler

        teams = tournament.iter_teams()
        if self.app.game_side not in {key for key, _team in teams}:
            self.app.game_side = teams[0][0]
        roster = []
        for _key, team in teams:
            names = team.player_names
            roster.append(f"{team.name}: {', '.join(names) if names else 'состав не указан'}")
        self.header.content = game_header(game, teams, tournament.goal)
        self.hint.value = f"{filled_hint(game)} · {' · '.join(roster)}"
        self.selector.controls = [
            _side_chip(self.app, key, team.name, self.app.game_side == key, team.color)
            for key, team in teams
        ]
        if self.compact:
            key = self.app.game_side
            self.cards.content = build_scorecard(game, tournament.team(key), key, True, edit(key))
            layout = [self.header, self.selector, self.hint, self.cards]
        else:
            self.cards.content = ft.ResponsiveRow(
                [
                    ft.Container(
                        build_scorecard(game, team, key, False, edit(key)),
                        col={"xs": 12, "md": 6},
                    )
                    for key, team in teams
                ],
                spacing=12,
                run_spacing=12,
            )
            layout = [self.header, self.hint, self.cards]
        if list(self.control.controls) != layout:
            self.control.controls = layout
        celebrate = getattr(self.app, "maybe_celebrate_goal", None)
        if callable(celebrate):
            celebrate()


def game_screen(app: YatzyApp, compact: bool) -> ft.Control:
    if app.state.active_tournament is None or app.state.active_game is None:
        app.game_view = None
        return empty_state(ft.Icons.SCOREBOARD_OUTLINED, "Нет матча", "Откройте турнир и выберите игру.")

    view = getattr(app, "game_view", None)
    if view is None or not view.matches(compact):
        view = GameScreen(app, compact)
        app.game_view = view
    else:
        view.sync()
    return view.control


def rules_screen() -> ft.Control:
    return ft.Column(
        [
            heading("Как считать"),
            card(
                section_label("Турнир"),
                body("Две команды играют серию матчей. В каждом матче ровно 3 раунда. ИГОГО команды — сумма трёх раундов."),
                body("Состав команды — отдельные имена. Они не меняют колонки счёта, а нужны, чтобы отметить, кто выкинул яцзы."),
                body("В таблице: баллы — ИГОГО матча, победа — 1 у команды с большим ИГОГО. Пустой матч в зачёт не идёт."),
            ),
            card(
                section_label("1 этап"),
                body("Единицы–шестёрки: сумма выпавших костей этой номинации. В игре 5 кубиков, поэтому максимум 5, 10, 15, 20, 25 и 30."),
                body("Если сумма этапа ≥ 63, команда получает премию 35. «До премии» — сколько не хватает до 63, но не ниже нуля: 0 значит премия уже взята."),
            ),
            card(
                section_label("2 этап"),
                body("Пара — 2 одинаковых, две пары, сет — 3, каре — 4: если комбинация есть, пишется сумма всех пяти костей (5–30) или 0."),
                body("Малый стрит — 4 подряд, 30. Большой — 5 подряд, 40. Фулл-хаус — 3+2, 25. Яцзы — 5 одинаковых, 50. Шанс — любая сумма."),
                body("Когда засчитываете яцзы, выберите игрока из состава — по ним собирается статистика турнира."),
            ),
            card(
                section_label("Цель 777"),
                body("Ориентир на матч: сумма трёх раундов команды. Удобно видеть по ходу игры, кто ближе к цели."),
            ),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
    )


def _ensure_setup_draft(app: YatzyApp, existing: Tournament | None) -> None:
    if getattr(app, "setup_ready", False):
        return
    app.setup_name = getattr(app, "setup_name", None) or (existing.name if existing else "Яцзы")
    app.setup_goal = getattr(app, "setup_goal", None) or str(existing.goal if existing else DEFAULT_GOAL)
    if not getattr(app, "setup_teams", None):
        if existing:
            app.setup_teams = [
                SetupTeam(team.name, team.color or TEAM_SWATCHES[index % len(TEAM_SWATCHES)], _player_drafts(team.players), key)
                for index, (key, team) in enumerate(existing.iter_teams())
            ]
        else:
            app.setup_teams = _default_setup_teams()
    app.setup_ready = True


def _default_setup_teams() -> list[SetupTeam]:
    return [
        SetupTeam("", TEAM_SWATCHES[0], [], "a"),
        SetupTeam("", TEAM_SWATCHES[1], [], "b"),
    ]


def _draft_team_name(draft: SetupTeam, index: int) -> str:
    return (draft.name or "").strip() or f"Команда {index + 1}"


def _player_drafts(players) -> list[DraftPlayer]:
    drafts: list[DraftPlayer] = []
    for index, item in enumerate(players):
        name = item.name if hasattr(item, "name") else str(item)
        player_id = item.id if hasattr(item, "id") else None
        drafts.append(DraftPlayer(name=name, source_index=index, player_id=player_id))
    return drafts


def _setup_team_card(app: YatzyApp, index: int, team: SetupTeam) -> tuple[ft.Container, ft.IconButton]:
    color = team.color or TEAM_SWATCHES[index % len(TEAM_SWATCHES)]
    delete_btn = ft.IconButton(
        ft.Icons.DELETE_OUTLINE,
        tooltip="Удалить команду",
        disabled=len(app.setup_teams) <= MIN_TEAMS,
        on_click=lambda _e, item=team: app.setup_remove_team(item),
    )
    players_slot = ft.Container(content=_player_editor(app, team))
    card = ft.Container(
        content=ft.Column(
            [
                ft.TextField(
                    label=f"Команда {index + 1}",
                    value=team.name,
                    on_change=lambda e, item=team: setattr(item, "name", e.control.value or ""),
                ),
                ft.Row(
                    [_color_picker_button(app, team), delete_btn],
                    spacing=8,
                    wrap=True,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                body("Игроки", muted=True),
                players_slot,
            ],
            spacing=10,
            tight=True,
        ),
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        border_radius=18,
        padding=16,
        border=ft.Border.only(
            left=ft.BorderSide(4, color),
            top=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            right=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
            bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT),
        ),
    )
    card.players_slot = players_slot
    return card, delete_btn


def _color_picker_button(app: YatzyApp, team: SetupTeam) -> ft.Control:
    selected = team.color if team.color in TEAM_SWATCHES else TEAM_SWATCHES[0]
    return ft.PopupMenuButton(
        tooltip="Цвет команды",
        menu_position=ft.PopupMenuPosition.UNDER,
        content=ft.Container(
            content=ft.Row(
                [
                    ft.Container(width=16, height=16, border_radius=999, bgcolor=selected),
                    ft.Text(SWATCH_TITLES.get(selected, "Цвет"), size=13),
                    ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=18),
                ],
                spacing=8,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            border_radius=10,
        ),
        items=[
            ft.PopupMenuItem(
                content=ft.Row(
                    [
                        ft.Container(width=16, height=16, border_radius=999, bgcolor=swatch),
                        ft.Text(SWATCH_TITLES.get(swatch, swatch)),
                    ],
                    spacing=10,
                    tight=True,
                ),
                on_click=lambda _e, item=team, value=swatch: app.setup_set_team_color(item, value),
            )
            for swatch in TEAM_SWATCHES
        ],
    )


def _player_editor(app: YatzyApp, team: SetupTeam) -> ft.Control:
    drafts = team.players
    can_remove = len(drafts) > MIN_PLAYERS
    chips = [
        ft.Container(
            content=ft.Row(
                [
                    ft.TextField(
                        label=f"Игрок {index + 1}",
                        value=draft.name,
                        width=168,
                        on_change=lambda e, item=draft: setattr(item, "name", e.control.value or ""),
                    ),
                    ft.IconButton(
                        ft.Icons.CLOSE,
                        tooltip="Удалить",
                        icon_size=18,
                        disabled=not can_remove,
                        on_click=lambda _e, item=team, idx=index: app.setup_remove_player(item, idx),
                    ),
                ],
                spacing=0,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
        for index, draft in enumerate(drafts)
    ]
    add_label = (
        "Игрок"
        if len(drafts) < MAX_PLAYERS
        else f"Максимум {ru_count(MAX_PLAYERS, 'игрок', 'игрока', 'игроков')}"
    )
    chips.append(
        ft.TextButton(
            add_label,
            icon=ft.Icons.PERSON_ADD_ALT,
            disabled=len(drafts) >= MAX_PLAYERS,
            on_click=lambda _e, item=team: app.setup_add_player(item),
        )
    )
    return ft.Row(chips, wrap=True, spacing=8, run_spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def _tournament_from_setup(name: str, goal: int, drafts: list[SetupTeam]) -> Tournament:
    first, second, *rest = drafts
    extras = []
    for index, draft in enumerate(rest, start=2):
        extras.append(
            Team(
                _draft_team_name(draft, index),
                [TeamPlayer(item.name) for item in draft.players if item.name.strip()],
                draft.color,
                draft.key if draft.key not in {"", "a", "b"} else new_id(),
            )
        )
    return create_tournament(
        name=name or "Яцзы",
        team_a=_draft_team_name(first, 0),
        team_b=_draft_team_name(second, 1),
        players_a=[item.name for item in first.players],
        players_b=[item.name for item in second.players],
        goal=goal,
        color_a=first.color,
        color_b=second.color,
        extra_teams=extras,
    )


def _apply_setup_teams(tournament: Tournament, drafts: list[SetupTeam]) -> None:
    first, second, *rest = drafts
    tournament.team_a.name = _draft_team_name(first, 0)
    tournament.team_a.color = first.color
    tournament.apply_roster("a", first.players)
    tournament.team_b.name = _draft_team_name(second, 1)
    tournament.team_b.color = second.color
    tournament.apply_roster("b", second.players)
    extras: list[Team] = []
    for index, draft in enumerate(rest, start=2):
        team_id = draft.key if draft.key not in {"", "a", "b"} else new_id()
        extras.append(
            Team(
                _draft_team_name(draft, index),
                [],
                draft.color,
                team_id,
            )
        )
    tournament.extra_teams = extras
    for draft, team in zip(rest, extras, strict=True):
        tournament.apply_roster(team.id, draft.players)
    tournament.sync_rosters()


def _matches_label(count: int) -> str:
    return ru_count(count, "матч", "матча", "матчей")


def _home_scoreboard(tournament: Tournament, games: int) -> ft.Control:
    teams = tournament.iter_teams()
    if len(teams) <= 2:
        items: list[ft.Control] = []
        for index, (key, team) in enumerate(teams):
            if index:
                items.append(ft.Text(":", size=28, weight=ft.FontWeight.W_700, color=ft.Colors.ON_SURFACE_VARIANT))
            items.append(_card_team_column(team.name, key, tournament, games, expand=True))
        return ft.Row(
            items,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )
    wide = max(1, 12 // len(teams))
    return ft.ResponsiveRow(
        [
            ft.Container(
                _card_team_column(team.name, key, tournament, games, expand=False),
                col={"xs": 6, "sm": 4, "lg": wide},
            )
            for key, team in teams
        ],
        spacing=8,
        run_spacing=12,
    )


def _card_team_column(name: str, side: str, tournament: Tournament, games: int, expand: bool) -> ft.Control:
    color = team_color(side, tournament.team(side).color)
    points = tournament.points(side)
    progress = min(1.0, points / max(tournament.goal, 1) / max(games, 1))
    return ft.Column(
        [
            ft.Text(
                name,
                size=13,
                weight=ft.FontWeight.W_700,
                color=color,
                text_align=ft.TextAlign.CENTER,
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            ),
            ft.Text(str(tournament.wins(side)), size=34, weight=ft.FontWeight.W_800, color=color, text_align=ft.TextAlign.CENTER),
            progress_bar(progress, color),
        ],
        spacing=4,
        tight=True,
        expand=expand,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _tournament_menu(app: YatzyApp, tournament: Tournament) -> ft.Control:
    return ft.PopupMenuButton(
        icon=ft.Icons.MORE_VERT,
        tooltip="Действия с турниром",
        menu_position=ft.PopupMenuPosition.UNDER,
        items=[
            ft.PopupMenuItem(
                content="Выгрузить JSON",
                icon=ft.Icons.DOWNLOAD,
                on_click=lambda _e, item=tournament: app.export_tournament(item.id),
            ),
            ft.PopupMenuItem(
                content="Редактировать",
                icon=ft.Icons.EDIT_OUTLINED,
                on_click=lambda _e, item=tournament: app.open_setup(edit=True, tournament_id=item.id),
            ),
            ft.PopupMenuItem(
                content="Удалить",
                icon=ft.Icons.DELETE_OUTLINE,
                on_click=lambda _e, item=tournament: app.confirm_delete(item.id),
            ),
        ],
    )


def _tournament_card(app: YatzyApp, tournament: Tournament) -> ft.Control:
    games = len(tournament.games)
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        heading(tournament.name, 20),
                        _tournament_menu(app, tournament),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                _home_scoreboard(tournament, games),
                ft.Row(
                    [
                        body(f"{_matches_label(games)} · цель {tournament.goal}", muted=True),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.ON_SURFACE_VARIANT),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=12,
            tight=True,
        ),
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        border_radius=18,
        padding=16,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        ink=True,
        on_click=lambda _e, item=tournament: app.open_tournament(item.id),
    )


def _team_summary(tournament: Tournament, side: str) -> ft.Control:
    team = tournament.team(side)
    color = team_color(side, team.color)
    points = tournament.points(side)
    return card(
        team_badge(team.name, side, large=True, color=team.color),
        ft.Text(
            ru_count(tournament.wins(side), "победа", "победы", "побед"),
            size=22,
            weight=ft.FontWeight.W_800,
            color=color,
        ),
        body(f"{ru_count(points, 'балл', 'балла', 'баллов')} за сыгранные матчи", muted=True),
        progress_bar(min(1.0, points / max(tournament.goal, 1) / max(len(tournament.games), 1)), color),
        body(" · ".join(team.player_names) if team.player_names else "Состав ещё не указан", muted=True),
    )


def _yatzy_stats(tournament: Tournament) -> ft.Control:
    teams = tournament.iter_teams()
    caption = ft.Row(
        [
            ft.Container(width=90),
            *[
                ft.Container(team_badge(team.name, key, color=team.color), expand=True)
                for key, team in teams
            ],
        ]
    )
    cells: list[ft.Control] = [ft.Text("Яцзы", width=90, size=13)]
    totals: list[ft.Control] = [ft.Text("Итого", width=90, size=13, weight=ft.FontWeight.W_700)]
    for key, _team in teams:
        stats = tournament.yatzy_stats(key)
        text = "—" if not stats else " • ".join(f"{item.name} {item.count}" for item in stats)
        cells.append(
            ft.Text(
                text,
                expand=True,
                size=13,
                text_align=ft.TextAlign.CENTER,
                color=ft.Colors.ON_SURFACE_VARIANT,
            )
        )
        totals.append(
            ft.Text(
                str(sum(item.count for item in stats)),
                expand=True,
                text_align=ft.TextAlign.CENTER,
                size=13,
                weight=ft.FontWeight.W_700,
            )
        )
    return ft.Column(
        [
            caption,
            ft.Row(cells, vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Row(totals, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ],
        spacing=6,
        tight=True,
    )


def _standings_table(tournament: Tournament) -> ft.Control:
    teams = tournament.iter_teams()
    if len(teams) == 2:
        return _standings_two(tournament)
    return _standings_many(tournament)


def _standings_two(tournament: Tournament) -> ft.Control:
    header = _standings_pair_row("Матч", "Баллы", "Победа", "Баллы", "Победа", header=True)
    rows = [header]
    for game in tournament.games:
        if not game.is_started():
            rows.append(_standings_pair_row(game.title, "0", "", "0", ""))
            continue
        winner = game.winner_side()
        left = game.team_total("a")
        right = game.team_total("b")
        rows.append(
            _standings_pair_row(
                game.title,
                str(left),
                "1" if winner == "a" else "0",
                str(right),
                "1" if winner == "b" else "0",
                glow_left=left > tournament.goal,
                glow_right=right > tournament.goal,
            )
        )
    rows.append(
        _standings_pair_row(
            "Итого",
            str(tournament.points("a")),
            str(tournament.wins("a")),
            str(tournament.points("b")),
            str(tournament.wins("b")),
            header=True,
        )
    )
    caption = ft.Row(
        [
            ft.Container(width=90),
            ft.Container(team_badge(tournament.team_a.name, "a", color=tournament.team_a.color), expand=True),
            ft.Container(team_badge(tournament.team_b.name, "b", color=tournament.team_b.color), expand=True),
        ]
    )
    return ft.Column([caption, *rows], spacing=6, tight=True)


def _standings_many(tournament: Tournament) -> ft.Control:
    teams = tournament.iter_teams()
    caption = ft.Row(
        [
            ft.Container(width=90),
            *[ft.Container(team_badge(team.name, key, color=team.color), expand=True) for key, team in teams],
        ]
    )
    rows = [caption]
    for game in tournament.games:
        winner = game.winner_side() if game.is_started() else None
        cells: list[ft.Control] = [ft.Text(game.title, width=90, size=13)]
        for key, _team in teams:
            total = game.team_total(key) if game.is_started() else 0
            cells.append(
                _standings_points(
                    str(total),
                    winner == key,
                    game.is_started() and total > tournament.goal,
                )
            )
        rows.append(ft.Row(cells, vertical_alignment=ft.CrossAxisAlignment.CENTER))
    totals: list[ft.Control] = [ft.Text("Итого", width=90, size=13, weight=ft.FontWeight.W_700)]
    for key, _team in teams:
        totals.append(_standings_points(str(tournament.points(key)), True, False))
    rows.append(ft.Row(totals, vertical_alignment=ft.CrossAxisAlignment.CENTER))
    return ft.Column(rows, spacing=6, tight=True)


def _standings_pair_row(
    match: str,
    left_points: str,
    left_win: str,
    right_points: str,
    right_win: str,
    header: bool = False,
    glow_left: bool = False,
    glow_right: bool = False,
) -> ft.Control:
    weight = ft.FontWeight.W_700 if header else None
    return ft.Row(
        [
            ft.Text(match, width=90, weight=weight, size=13),
            _standings_points(left_points, header, glow_left),
            ft.Text(left_win, expand=True, text_align=ft.TextAlign.CENTER, weight=weight, size=13),
            _standings_points(right_points, header, glow_right),
            ft.Text(right_win, expand=True, text_align=ft.TextAlign.CENTER, weight=weight, size=13),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _standings_points(text: str, emphasize: bool, glow: bool) -> ft.Control:
    weight = ft.FontWeight.W_700 if emphasize or glow else None
    if not glow:
        return ft.Text(text, expand=True, text_align=ft.TextAlign.CENTER, weight=weight, size=13)
    return ft.Container(
        expand=True,
        alignment=ft.Alignment.CENTER,
        content=ft.Row(
            [
                ft.Icon(ft.Icons.AUTO_AWESOME, size=14, color=GOAL_GLOW),
                ft.Text(text, size=13, weight=ft.FontWeight.W_800, color=GOAL_GLOW),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=4,
            tight=True,
        ),
        bgcolor=ft.Colors.with_opacity(0.16, GOAL_GLOW),
        border=ft.Border.all(1, GOAL_GLOW),
        border_radius=999,
        padding=ft.Padding.symmetric(horizontal=8, vertical=4),
    )


def _game_tile(app: YatzyApp, game) -> ft.Control:
    tournament = app.state.active_tournament
    if tournament is None or not game.is_started():
        status = "не начата"
    else:
        status = " — ".join(str(game.team_total(key)) for key, _team in tournament.iter_teams())
    return ft.Container(
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(game.title, weight=ft.FontWeight.W_700),
                        body(status, muted=True),
                    ],
                    spacing=2,
                    tight=True,
                    expand=True,
                ),
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE,
                    tooltip="Удалить матч",
                    on_click=lambda _e, item=game: app.remove_game(item.id),
                ),
                ft.Icon(ft.Icons.CHEVRON_RIGHT),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        border_radius=16,
        padding=14,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        ink=True,
        on_click=lambda _e, item=game: app.open_game(item.id),
    )


def _side_chip(app: YatzyApp, side: str, name: str, selected: bool, tint: str = "") -> ft.Control:
    color = team_color(side, tint)
    return ft.Container(
        content=ft.Text(name, weight=ft.FontWeight.W_700, color=color),
        padding=ft.Padding.symmetric(horizontal=14, vertical=10),
        border_radius=999,
        bgcolor=ft.Colors.with_opacity(0.18 if selected else 0.08, color),
        border=ft.Border.all(2 if selected else 1, color if selected else ft.Colors.OUTLINE_VARIANT),
        ink=True,
        alignment=ft.Alignment.CENTER,
        on_click=lambda _e: app.set_game_side(side),
    )


def card(*controls: ft.Control, spacing: bool = True) -> ft.Control:
    return ft.Container(
        content=ft.Column(list(controls), spacing=8 if spacing else 10, tight=True),
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        border_radius=18,
        padding=16,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
    )
