import flet as ft

from yatzy.current import current_tournament
from yatzy.models import AppState, SetupTeam, create_tournament
from yatzy.ui.screens import game_screen, home_screen, rules_screen, setup_screen, tournament_screen


class FakeApp:
    def __init__(self) -> None:
        self.state = AppState()
        self.game_side = "a"
        self.setup_name = "Яцзы"
        self.setup_goal = "777"
        self.setup_teams: list[SetupTeam] = []
        self.setup_ready = False
        self.game_view = None

    def compact(self) -> bool:
        return False

    def open_setup(self, edit: bool = False, tournament_id: str | None = None) -> None:
        return None

    def open_add_tournament_menu(self, _e: object = None) -> None:
        return None

    def setup_add_player(self, team_index: int) -> None:
        return None

    def setup_remove_player(self, team_index: int, index: int) -> None:
        return None

    def setup_add_team(self) -> None:
        return None

    def setup_remove_team(self, index: int) -> None:
        return None

    def setup_set_team_color(self, team: SetupTeam, color: str) -> None:
        team.color = color

    def confirm_delete(self, tournament_id: str) -> None:
        return None

    def open_tournament(self, tournament_id: str | None = None) -> None:
        return None

    def add_game(self) -> None:
        return None

    def remove_game(self, game_id: str) -> None:
        return None

    def open_game(self, game_id: str | None = None) -> None:
        return None

    def edit_score(self, side: str, index: int, key: str) -> None:
        return None

    def set_game_side(self, side: str) -> None:
        self.game_side = side

    def persist(self) -> None:
        return None

    async def import_tournaments(self, _e: object = None) -> None:
        return None

    async def export_tournament(self, tournament_id: str | None = None) -> None:
        return None


def test_home_and_rules_build() -> None:
    app = FakeApp()
    assert isinstance(home_screen(app), ft.Control)
    assert isinstance(rules_screen(), ft.Control)
    assert isinstance(setup_screen(app), ft.Control)


def test_home_tournament_card_opens_on_card_click() -> None:
    from yatzy.ui.screens import _tournament_card

    app = FakeApp()
    tournament = current_tournament()
    app.state.add_tournament(tournament)
    assert isinstance(home_screen(app), ft.Control)
    card = _tournament_card(app, tournament)
    assert card.on_click is not None


def test_tournament_and_game_screens_build() -> None:
    from yatzy.ui.scorecard import scorecard_width

    app = FakeApp()
    app.state.add_tournament(current_tournament())
    assert isinstance(tournament_screen(app), ft.Control)
    assert isinstance(game_screen(app, compact=True), ft.Control)
    assert isinstance(game_screen(app, compact=False), ft.Control)
    assert scorecard_width(False) * 2 + 16 < 1368


def test_setup_edit_builds() -> None:
    app = FakeApp()
    tournament = create_tournament()
    app.state.add_tournament(tournament)
    assert isinstance(setup_screen(app, tournament), ft.Control)


def test_standings_highlights_scores_above_goal() -> None:
    from yatzy.ui.screens import _standings_points, _standings_table

    tournament = current_tournament()
    assert tournament.games[2].team_total("b") > tournament.goal
    assert isinstance(_standings_table(tournament), ft.Control)
    glow = _standings_points("833", False, True)
    plain = _standings_points("764", False, False)
    assert isinstance(glow, ft.Container)
    assert isinstance(plain, ft.Text)
