from __future__ import annotations

import asyncio
import json
import threading

import flet as ft

from yatzy.io import dumps_tournament, merge_tournaments, parse_tournaments, read_tournaments, suggested_filename, write_tournament
from yatzy.models import (
    CATEGORY_BY_KEY,
    DEFAULT_GOAL,
    DraftPlayer,
    MAX_PLAYERS,
    MAX_TEAMS,
    MIN_PLAYERS,
    MIN_TEAMS,
    SetupTeam,
    TeamPlayer,
    Tournament,
    new_id,
)
from yatzy.lan_sync import LanHost, SyncError, join_session, new_token, start_host
from yatzy.ru import imported_tournaments, synced_tournaments
from yatzy.storage import load_state, save_state
from yatzy.theme import TEAM_SWATCHES, THEME_PALETTES, apply_theme, team_color
from yatzy.ui.salute import show_goal_salute
from yatzy.ui.score_dialog import open_score_dialog
from yatzy.ui.screens import (
    game_screen,
    home_screen,
    rules_screen,
    setup_screen,
    tournament_screen,
)

COMPACT_WIDTH = 840
WINDOW_MIN_WIDTH = 960
WINDOW_MIN_HEIGHT = 720
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800


class YatzyApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.state = load_state()
        self.screen = "home"
        self.nav_index = 0
        self.game_side = "a"
        self.editing_existing = False
        self.setup_name = "Яцзы"
        self.setup_goal = str(DEFAULT_GOAL)
        self.setup_teams: list[SetupTeam] = [
            SetupTeam("", TEAM_SWATCHES[0], [], "a"),
            SetupTeam("", TEAM_SWATCHES[1], [], "b"),
        ]
        self.setup_ready = False
        self.setup_view = None
        self._lan_host: LanHost | None = None
        self._lan_lock = threading.Lock()
        self._shell = ft.Container(expand=True, padding=ft.Padding.symmetric(horizontal=16, vertical=10))
        self._scroll_offset = 0.0
        self._scroll_screen: str | None = None
        self._scroll_view: ft.Column | None = None
        self._last_compact: bool | None = None
        self.game_view = None

    def start(self) -> None:
        page = self.page
        page.title = "Яцзы"
        page.adaptive = True
        page.padding = 0
        apply_theme(page, self.state.theme_mode, self.state.theme_id)
        page.window.min_width = WINDOW_MIN_WIDTH
        page.window.min_height = WINDOW_MIN_HEIGHT
        page.window.width = WINDOW_WIDTH
        page.window.height = WINDOW_HEIGHT
        page.window.icon = "icon.png"
        page.on_resize = self._on_resize
        page.theme_mode = ft.ThemeMode.DARK if self.state.theme_mode == "dark" else ft.ThemeMode.LIGHT
        page.add(ft.SafeArea(expand=True, content=self._shell))
        self._last_compact = self.compact()
        self.refresh()

    def _on_resize(self, _e: ft.PageResizeEvent) -> None:
        compact = self.compact()
        if compact == self._last_compact:
            return
        self._last_compact = compact
        self.refresh()

    def persist(self) -> None:
        save_state(self.state)

    def compact(self) -> bool:
        width = self.page.width or 0
        if width <= 0:
            return False
        return width < COMPACT_WIDTH

    def open_home(self) -> None:
        self.screen = "home"
        self.nav_index = 0
        self.refresh()

    def open_setup(self, edit: bool = False, tournament_id: str | None = None) -> None:
        if tournament_id:
            self.state.active_tournament_id = tournament_id
            edit = True
        self.editing_existing = edit
        tournament = self.state.active_tournament if edit else None
        self.setup_name = tournament.name if tournament else "Яцзы"
        self.setup_goal = str(tournament.goal if tournament else DEFAULT_GOAL)
        if tournament:
            self.setup_teams = [
                SetupTeam(
                    team.name,
                    team.color or TEAM_SWATCHES[index % len(TEAM_SWATCHES)],
                    _drafts_from(team.players),
                    key,
                )
                for index, (key, team) in enumerate(tournament.iter_teams())
            ]
        else:
            self.setup_teams = [
                SetupTeam("", TEAM_SWATCHES[0], [], "a"),
                SetupTeam("", TEAM_SWATCHES[1], [], "b"),
            ]
        self.setup_ready = True
        self.setup_view = None
        self.screen = "setup"
        self.refresh()

    def setup_add_player(self, team: SetupTeam) -> None:
        if team not in self.setup_teams or len(team.players) >= MAX_PLAYERS:
            return
        team.players.append(DraftPlayer(""))
        self._patch_setup("players", team)

    def setup_remove_player(self, team: SetupTeam, index: int) -> None:
        if team not in self.setup_teams or index < 0 or index >= len(team.players):
            return
        if len(team.players) <= MIN_PLAYERS:
            return
        team.players.pop(index)
        self._patch_setup("players", team)

    def setup_add_team(self) -> None:
        if len(self.setup_teams) >= MAX_TEAMS:
            return
        index = len(self.setup_teams)
        self.setup_teams.append(SetupTeam("", TEAM_SWATCHES[index % len(TEAM_SWATCHES)], [], new_id()))
        self._patch_setup("add")

    def setup_remove_team(self, team: SetupTeam) -> None:
        if len(self.setup_teams) <= MIN_TEAMS or team not in self.setup_teams:
            return
        self.setup_teams.remove(team)
        self._patch_setup("drop", team)

    def setup_set_team_color(self, team: SetupTeam, color: str) -> None:
        team.color = color
        self._patch_setup("color", team)

    def _patch_setup(self, action: str, team: SetupTeam | None = None) -> None:
        view = self.setup_view
        if view is None or self.screen != "setup":
            self.refresh()
            return
        if action == "add":
            view.add_team_card()
        elif action == "drop" and team is not None:
            view.drop_team_card(team)
        elif action == "players" and team is not None:
            view.sync_players(team)
        elif action == "color" and team is not None:
            view.sync_color(team)
        else:
            view.rebuild_teams()
        self.page.update()

    def open_add_tournament_menu(self, _e: ft.Event | None = None) -> None:
        def choose_manual(_event: ft.Event) -> None:
            self.page.pop_dialog()
            self.open_setup()

        def choose_file(_event: ft.Event) -> None:
            self.page.pop_dialog()
            self.page.run_task(self.import_tournaments)

        self.page.show_dialog(
            ft.AlertDialog(
                title=ft.Text("Добавить турнир"),
                content=ft.Column(
                    [
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.EDIT_OUTLINED),
                            title=ft.Text("Создать вручную"),
                            subtitle=ft.Text("Название, команды и состав"),
                            on_click=choose_manual,
                        ),
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.UPLOAD_FILE),
                            title=ft.Text("Загрузить из JSON"),
                            subtitle=ft.Text("Импорт сохранённого турнира"),
                            on_click=choose_file,
                        ),
                    ],
                    tight=True,
                    spacing=0,
                ),
                actions=[ft.TextButton("Закрыть", on_click=lambda _event: self.page.pop_dialog())],
            )
        )

    def open_sync_menu(self, _e: ft.Event | None = None) -> None:
        from yatzy.ui.sync_dialog import open_sync_menu

        open_sync_menu(self)

    def start_lan_host(self) -> LanHost | None:
        self.stop_lan_host(close_dialog=False)
        try:
            self._lan_host = start_host(new_token(), self._merge_from_peer)
        except OSError:
            self._toast("Не удалось открыть сеть. Проверьте Wi‑Fi.")
            return None
        return self._lan_host

    def stop_lan_host(self, close_dialog: bool = True) -> None:
        host = self._lan_host
        self._lan_host = None
        if host is not None:
            host.stop()
        if close_dialog:
            self.page.pop_dialog()
            self.refresh()

    def _merge_from_peer(self, incoming: list[Tournament]) -> list[Tournament]:
        with self._lan_lock:
            self.state.tournaments = merge_tournaments(self.state.tournaments, incoming)
            self.persist()
            return list(self.state.tournaments)

    async def join_lan_sync(self, raw: str) -> None:
        try:
            merged = await asyncio.to_thread(join_session, raw, list(self.state.tournaments))
        except SyncError as error:
            self._toast(str(error))
            return
        self.state.tournaments = merged
        if self.state.active_tournament is None and merged:
            self.state.active_tournament_id = merged[0].id
            self.state.active_game_id = merged[0].games[0].id if merged[0].games else None
        self.persist()
        self.page.pop_dialog()
        self.screen = "home"
        self.nav_index = 0
        self.refresh()
        self._toast(synced_tournaments(len(merged)))

    def open_tournament(self, tournament_id: str | None = None) -> None:
        if tournament_id:
            self.state.active_tournament_id = tournament_id
            tournament = self.state.active_tournament
            if tournament and tournament.games:
                self.state.active_game_id = tournament.games[-1].id
            self.persist()
        self.screen = "tournament"
        self.nav_index = 0
        self.refresh()

    def open_game(self, game_id: str | None = None) -> None:
        if game_id:
            self.state.active_game_id = game_id
            self.persist()
        self.screen = "game"
        self.nav_index = 1
        self.refresh()

    def open_rules(self) -> None:
        self.screen = "rules"
        self.nav_index = 2
        self.refresh()

    def set_game_side(self, side: str) -> None:
        self.game_side = side
        if self.screen == "game" and self.game_view is not None:
            self.game_view.sync()
            self.page.update()
            return
        self.refresh()

    def add_game(self) -> None:
        tournament = self.state.active_tournament
        if tournament is None:
            return
        game = tournament.add_game()
        self.state.active_game_id = game.id
        self.persist()
        self.open_game(game.id)

    def remove_game(self, game_id: str) -> None:
        tournament = self.state.active_tournament
        if tournament is None:
            return
        tournament.remove_game(game_id)
        if self.state.active_game_id == game_id:
            self.state.active_game_id = tournament.games[-1].id if tournament.games else None
        self.persist()
        self.refresh()

    def toggle_theme(self) -> None:
        self.state.theme_mode = "light" if self.state.theme_mode == "dark" else "dark"
        apply_theme(self.page, self.state.theme_mode, self.state.theme_id)
        self.persist()
        self.refresh()

    def set_theme_id(self, theme_id: str) -> None:
        self.state.theme_id = theme_id
        apply_theme(self.page, self.state.theme_mode, theme_id)
        self.persist()
        self.refresh()

    def maybe_celebrate_goal(self) -> None:
        tournament = self.state.active_tournament
        game = self.state.active_game
        if tournament is None or game is None or self.screen != "game":
            return
        hits: list[tuple[str, int, str]] = []
        for side, team in tournament.iter_teams():
            total = game.team_total(side)
            if game.claim_goal(side, total, tournament.goal):
                hits.append((team.name, total, team_color(side, team.color)))
        if not hits:
            return
        self.persist()
        show_goal_salute(self.page, hits)

    def confirm_delete(self, tournament_id: str) -> None:
        def delete(_e: ft.Event[ft.Button]) -> None:
            self.page.pop_dialog()
            self.state.delete_tournament(tournament_id)
            self.persist()
            self.screen = "home"
            self.nav_index = 0
            self.refresh()

        self.page.show_dialog(
            ft.AlertDialog(
                title=ft.Text("Удалить турнир?"),
                content=ft.Text("Счёт матчей будет потерян."),
                actions=[
                    ft.TextButton("Отмена", on_click=lambda _e: self.page.pop_dialog()),
                    ft.Button("Удалить", on_click=delete),
                ],
            )
        )

    async def import_tournaments(self, _e: ft.Event | None = None) -> None:
        files = await ft.FilePicker().pick_files(
            dialog_title="Загрузить турнир",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["json"],
            allow_multiple=True,
            with_data=True,
        )
        if not files:
            return
        imported = []
        errors: list[str] = []
        for item in files:
            try:
                imported.extend(_tournaments_from_picked(item))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                errors.append(item.name)
        if imported:
            count = self.state.import_tournaments(imported)
            self.persist()
            self.screen = "home"
            self.nav_index = 0
            self.refresh()
            self._toast(imported_tournaments(count))
        if errors and not imported:
            self._toast("Не удалось прочитать JSON.")
        elif errors:
            self._toast(f"Часть файлов не прочитана: {', '.join(errors)}")

    def export_tournament(self, tournament_id: str | None = None) -> None:
        self.page.run_task(self._export_tournament, tournament_id)

    async def _export_tournament(self, tournament_id: str | None = None) -> None:
        tournament = self.state.tournament_by_id(tournament_id) or self.state.active_tournament
        if tournament is None:
            self._toast("Нет турнира для выгрузки.")
            return
        payload = dumps_tournament(tournament)
        path = await ft.FilePicker().save_file(
            dialog_title="Сохранить турнир",
            file_name=suggested_filename(tournament),
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["json"],
            src_bytes=payload.encode("utf-8"),
        )
        if path:
            write_tournament(path, tournament)
        if path or self.page.web or self.page.platform.is_mobile():
            self._toast("Турнир сохранён в JSON.")

    def _toast(self, message: str) -> None:
        self.page.show_dialog(ft.SnackBar(ft.Text(message)))

    def edit_score(self, side: str, index: int, key: str) -> None:
        game = self.state.active_game
        category = CATEGORY_BY_KEY[key]
        if game is None:
            return
        column = game.columns(side)[index]
        tournament = self.state.active_tournament
        players = tournament.team(side).players if tournament else []

        def save(value: int | None, player: TeamPlayer | None = None) -> None:
            if key == "yatzy":
                column.set_yatzy(value, player)
            else:
                column.set(key, value)
            self.persist()
            if self.game_view is not None:
                self.game_view.sync()
                self.page.update()
                return
            self.refresh()

        open_score_dialog(
            self.page,
            category,
            column.name,
            column.get(key),
            save,
            players=players,
            yatzy_player_id=column.yatzy_player_id,
        )

    def refresh(self) -> None:
        page = self.page
        keep_scroll = self.screen == self._scroll_screen
        if not keep_scroll:
            self._scroll_offset = 0.0
        self._scroll_screen = self.screen
        compact = self.compact()
        page.appbar = self._appbar(compact)
        page.navigation_bar = self._nav_bar() if compact and self._show_nav() else None
        page.drawer = self._drawer() if self._show_nav() else None
        page.floating_action_button = self._fab()
        self._shell.content = self._body(compact)
        page.update()
        if keep_scroll and self._scroll_offset > 0 and self._scroll_view is not None:
            page.run_task(self._restore_scroll)

    def _on_scroll(self, event: ft.OnScrollEvent) -> None:
        if event.event_type in {ft.ScrollType.UPDATE, ft.ScrollType.END}:
            self._scroll_offset = max(0.0, event.pixels)

    async def _restore_scroll(self) -> None:
        view = self._scroll_view
        offset = self._scroll_offset
        if view is None or offset <= 0:
            return
        await view.scroll_to(offset=offset, duration=0)

    def _track_scroll(self, view: ft.Control) -> ft.Control:
        if isinstance(view, ft.Column) and view.scroll is not None:
            view.on_scroll = self._on_scroll
            self._scroll_view = view
        else:
            self._scroll_view = None
        return view

    def _show_nav(self) -> bool:
        return self.screen in {"tournament", "game", "rules"} and self.state.active_tournament is not None

    def _body(self, compact: bool) -> ft.Control:
        if self.screen == "home":
            view = home_screen(self)
        elif self.screen == "setup":
            view = setup_screen(self, self.state.active_tournament if self.editing_existing else None)
        elif self.screen == "game":
            view = game_screen(self, compact)
        elif self.screen == "rules":
            view = rules_screen()
        else:
            view = tournament_screen(self)
        return ft.Container(content=self._track_scroll(view), expand=True)

    def _appbar(self, compact: bool) -> ft.AppBar:
        if self.screen == "home":
            leading = None
        elif self._show_nav() and not compact:
            leading = ft.IconButton(
                ft.Icons.MENU,
                tooltip="Меню",
                on_click=self._open_drawer,
            )
        else:
            leading = ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _e: self._go_back())
        title = {
            "home": "Яцзы",
            "setup": "Редактирование" if self.editing_existing else "Новый турнир",
            "tournament": "Турнир",
            "game": self.state.active_game.title if self.state.active_game else "Матч",
            "rules": "Правила",
        }.get(self.screen, "Яцзы")
        return ft.AppBar(
            leading=leading,
            title=ft.Text(title),
            center_title=compact,
            bgcolor=ft.Colors.SURFACE,
            actions=[
                *(
                    [
                        ft.IconButton(
                            ft.Icons.SYNC,
                            tooltip="Синхронизация по Wi‑Fi",
                            on_click=self.open_sync_menu,
                        )
                    ]
                    if self.screen == "home"
                    else []
                ),
                *(
                    [
                        ft.IconButton(
                            ft.Icons.EDIT_OUTLINED,
                            tooltip="Редактировать турнир",
                            on_click=lambda _e: self.open_setup(edit=True),
                        )
                    ]
                    if self.screen == "tournament" and self.state.active_tournament
                    else []
                ),
                ft.PopupMenuButton(
                    icon=ft.Icons.PALETTE_OUTLINED,
                    tooltip="Палитра",
                    items=[
                        ft.PopupMenuItem(
                            content=("• " if self.state.theme_id == item.id else "") + item.title,
                            on_click=lambda _e, theme_id=item.id: self.set_theme_id(theme_id),
                        )
                        for item in THEME_PALETTES
                    ],
                ),
                ft.IconButton(
                    ft.Icons.LIGHT_MODE if self.state.theme_mode == "dark" else ft.Icons.DARK_MODE,
                    tooltip="Светлая / тёмная",
                    on_click=lambda _e: self.toggle_theme(),
                ),
                ft.IconButton(ft.Icons.HOME_OUTLINED, tooltip="Все турниры", on_click=lambda _e: self.open_home()),
            ],
        )

    def _go_back(self) -> None:
        if self.screen == "setup":
            self.screen = "tournament" if self.state.active_tournament else "home"
        elif self.screen == "game":
            self.screen = "tournament"
            self.nav_index = 0
        else:
            self.screen = "home"
        self.refresh()

    def _nav_bar(self) -> ft.NavigationBar:
        return ft.NavigationBar(
            selected_index=self.nav_index,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.EMOJI_EVENTS_OUTLINED, selected_icon=ft.Icons.EMOJI_EVENTS, label="Турнир"),
                ft.NavigationBarDestination(icon=ft.Icons.SCOREBOARD_OUTLINED, selected_icon=ft.Icons.SCOREBOARD, label="Матч"),
                ft.NavigationBarDestination(icon=ft.Icons.MENU_BOOK_OUTLINED, selected_icon=ft.Icons.MENU_BOOK, label="Правила"),
            ],
            on_change=self._on_nav,
        )

    def _drawer(self) -> ft.NavigationDrawer:
        tournament = self.state.active_tournament
        title = tournament.name if tournament else "Яцзы"
        return ft.NavigationDrawer(
            selected_index=self.nav_index,
            on_change=self._on_drawer_nav,
            controls=[
                ft.Container(
                    padding=ft.Padding.only(left=28, top=20, right=16, bottom=12),
                    content=ft.Text(title, theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                ),
                ft.NavigationDrawerDestination(
                    icon=ft.Icons.EMOJI_EVENTS_OUTLINED,
                    selected_icon=ft.Icons.EMOJI_EVENTS,
                    label="Турнир",
                ),
                ft.NavigationDrawerDestination(
                    icon=ft.Icons.SCOREBOARD_OUTLINED,
                    selected_icon=ft.Icons.SCOREBOARD,
                    label="Матч",
                ),
                ft.NavigationDrawerDestination(
                    icon=ft.Icons.MENU_BOOK_OUTLINED,
                    selected_icon=ft.Icons.MENU_BOOK,
                    label="Правила",
                ),
                ft.Divider(),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.HOME_OUTLINED),
                    title=ft.Text("Все турниры"),
                    on_click=self._drawer_home,
                ),
            ],
        )

    async def _open_drawer(self, _e: ft.Event[ft.IconButton]) -> None:
        await self.page.show_drawer()

    async def _on_drawer_nav(self, event: ft.Event[ft.NavigationDrawer]) -> None:
        index = int(event.control.selected_index)
        await self.page.close_drawer()
        self._go_nav(index)

    async def _drawer_home(self, _e: ft.Event[ft.ListTile]) -> None:
        await self.page.close_drawer()
        self.open_home()

    def _on_nav(self, event: ft.Event[ft.NavigationBar]) -> None:
        self._go_nav(int(event.control.selected_index))

    def _go_nav(self, index: int) -> None:
        self.nav_index = index
        if index == 0:
            self.screen = "tournament"
        elif index == 1:
            if self.state.active_game is None and self.state.active_tournament:
                self.add_game()
                return
            self.screen = "game"
        else:
            self.screen = "rules"
        self.refresh()

    def _fab(self) -> ft.FloatingActionButton | None:
        if self.screen == "home":
            return ft.FloatingActionButton(
                icon=ft.Icons.ADD,
                tooltip="Добавить турнир",
                on_click=self.open_add_tournament_menu,
            )
        if self.screen == "tournament" and self.state.active_tournament:
            return ft.FloatingActionButton(icon=ft.Icons.ADD, tooltip="Новая игра", on_click=lambda _e: self.add_game())
        return None


def _tournaments_from_picked(item: ft.FilePickerFile) -> list[Tournament]:
    if item.path:
        return read_tournaments(item.path)
    if item.bytes:
        return parse_tournaments(item.bytes)
    raise ValueError(item.name)


def _drafts_from(players: list[TeamPlayer] | list[str] | tuple[str, ...]) -> list[DraftPlayer]:
    drafts: list[DraftPlayer] = []
    for index, item in enumerate(players):
        if isinstance(item, TeamPlayer):
            drafts.append(DraftPlayer(name=item.name, source_index=index, player_id=item.id))
        else:
            drafts.append(DraftPlayer(name=str(item), source_index=index))
    return drafts
