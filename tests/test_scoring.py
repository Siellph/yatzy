from yatzy.current import current_tournament
from yatzy.models import (
    BONUS_POINTS,
    BONUS_THRESHOLD,
    CATEGORY_BY_KEY,
    SUM_MAX,
    SUM_MIN,
    DraftPlayer,
    clamp_score,
    create_tournament,
    suggested_score,
)


def test_upper_bonus_and_to_bonus() -> None:
    tournament = create_tournament()
    game = tournament.games[0]
    column = game.team_a[0]
    column.set("ones", 3)
    column.set("twos", 6)
    column.set("threes", 9)
    column.set("fours", 12)
    column.set("fives", 15)
    column.set("sixes", 18)
    totals = column.totals()
    assert totals.upper == 63
    assert totals.to_bonus == 0
    assert totals.bonus == BONUS_POINTS
    assert totals.stage1 == 63 + BONUS_POINTS


def test_to_bonus_does_not_go_below_zero() -> None:
    tournament = create_tournament()
    column = tournament.games[0].team_a[0]
    column.set("ones", 5)
    column.set("twos", 10)
    column.set("threes", 15)
    column.set("fours", 20)
    column.set("fives", 25)
    totals = column.totals()
    assert totals.upper > BONUS_THRESHOLD
    assert totals.to_bonus == 0
    assert totals.bonus == BONUS_POINTS


def test_no_bonus_below_threshold() -> None:
    tournament = create_tournament()
    column = tournament.games[0].team_a[0]
    column.set("sixes", 24)
    totals = column.totals()
    assert totals.upper == 24
    assert totals.to_bonus == BONUS_THRESHOLD - 24
    assert totals.bonus == 0


def test_empty_cells_are_not_zero() -> None:
    tournament = create_tournament()
    column = tournament.games[0].team_a[0]
    assert column.get("pair") is None
    assert column.totals().total == 0
    assert not tournament.games[0].is_started()
    assert tournament.games[0].winner_side() is None


def test_game_three_matches_spreadsheet() -> None:
    tournament = current_tournament()
    game = tournament.games[2]
    assert [column.totals().total for column in game.team_a] == [189, 287, 288]
    assert [column.totals().total for column in game.team_b] == [272, 302, 259]
    assert game.team_total("a") == 764
    assert game.team_total("b") == 833
    assert game.winner_side() == "b"


def test_tournament_table_wins() -> None:
    tournament = current_tournament()
    assert tournament.name == "Яцзы"
    assert tournament.wins("a") == 0
    assert tournament.wins("b") == 3
    assert tournament.points("a") == 520 + 690 + 764
    assert tournament.points("b") == 743 + 717 + 833
    assert tournament.games[3].title == "4-я игра"
    assert not tournament.games[3].is_started()


def test_new_game_copies_empty_template() -> None:
    tournament = create_tournament()
    first = tournament.games[0]
    second = tournament.add_game()
    assert first.title == "1-я игра"
    assert second.title == "2-я игра"
    assert not second.is_started()
    assert second.team_total("a") == 0
    assert second.team_total("b") == 0
    assert second.winner_side() is None
    assert [column.name for column in second.team_a] == ["1", "2", "3"]
    assert all(value is None for column in second.team_a for value in column.scores.values())


def test_roster_does_not_change_rounds() -> None:
    tournament = create_tournament(players_a=["Анна", "Борис"], players_b=["Кира", "Лев", "Мия", "Ника"])
    assert tournament.team_a.player_names == ["Анна", "Борис"]
    assert tournament.team_b.player_names == ["Кира", "Лев", "Мия", "Ника"]
    assert [column.name for column in tournament.games[0].team_a] == ["1", "2", "3"]
    assert [column.name for column in tournament.games[0].team_b] == ["1", "2", "3"]


def test_remove_player_keeps_round_scores() -> None:
    tournament = current_tournament()
    game = tournament.games[2]
    kept = [column.totals().total for column in game.team_a]
    tournament.apply_roster("a", [DraftPlayer("Анна"), DraftPlayer("Борис")])
    assert tournament.team_a.player_names == ["Анна", "Борис"]
    assert [column.name for column in game.team_a] == ["1", "2", "3"]
    assert [column.totals().total for column in game.team_a] == kept


def test_score_limits_five_dice() -> None:
    ones = CATEGORY_BY_KEY["ones"]
    chance = CATEGORY_BY_KEY["chance"]
    yatzy = CATEGORY_BY_KEY["yatzy"]
    assert clamp_score(ones, 6) == 5
    assert clamp_score(ones, 4) == 4
    assert clamp_score(chance, 31) == SUM_MAX
    assert clamp_score(chance, 3) == SUM_MIN
    assert clamp_score(chance, 0) == 0
    assert clamp_score(yatzy, 50) == 50
    assert clamp_score(yatzy, 1) == 50
    column = create_tournament().games[0].team_a[0]
    column.set("chance", 40)
    assert column.get("chance") == SUM_MAX


def test_yatzy_stats_by_player() -> None:
    tournament = create_tournament(players_a=["Анна", "Борис"])
    anna, boris = tournament.team_a.players
    game = tournament.games[0]
    game.team_a[0].set_yatzy(50, anna)
    game.team_a[1].set_yatzy(50, anna)
    game.team_a[2].set_yatzy(50, boris)
    stats = {item.name: item.count for item in tournament.yatzy_stats("a")}
    assert stats == {"Анна": 2, "Борис": 1}
    game.team_a[2].set_yatzy(0)
    assert game.team_a[2].yatzy_player_id is None
    assert {item.name: item.count for item in tournament.yatzy_stats("a")} == {"Анна": 2}


def test_json_export_import_roundtrip() -> None:
    from yatzy.io import dumps_tournament, merge_tournaments, parse_tournaments
    from yatzy.models import AppState

    original = current_tournament()
    loaded = parse_tournaments(dumps_tournament(original))
    assert len(loaded) == 1
    clone = loaded[0]
    assert clone.name == "Яцзы"
    assert clone.games[2].team_total("a") == 764
    assert clone.games[2].team_total("b") == 833
    state = AppState()
    state.import_tournaments(loaded)
    assert state.active_tournament is not None
    state.import_tournaments(loaded)
    assert len(state.tournaments) == 1
    other = current_tournament()
    other.id = "other"
    assert len(merge_tournaments(state.tournaments, [other])) == 2


def test_count_suggestions() -> None:
    ones = CATEGORY_BY_KEY["ones"]
    sixes = CATEGORY_BY_KEY["sixes"]
    assert [suggested_score(ones, count) for count in range(6)] == [0, 1, 2, 3, 4, 5]
    assert suggested_score(sixes, 4) == 24


def test_team_color_and_theme_persist() -> None:
    from yatzy.models import AppState, Game, Tournament

    tournament = create_tournament(color_a="#6C8CFF", color_b="#E07A7A")
    assert tournament.team_a.color == "#6C8CFF"
    assert tournament.team_b.color == "#E07A7A"
    loaded = Tournament.from_dict(tournament.to_dict())
    assert loaded.team_a.color == "#6C8CFF"
    assert loaded.team_b.color == "#E07A7A"
    state = AppState(theme_id="indigo", theme_mode="light")
    restored = AppState.from_dict(state.to_dict())
    assert restored.theme_id == "indigo"
    assert restored.theme_mode == "light"
    game = Game.from_dict({"title": "1 игра", "celebrated": ["b", "x"]})
    assert game.celebrated == ["b"]


def test_claim_goal_once() -> None:
    from yatzy.models import Game

    tournament = create_tournament()
    game = tournament.games[0]
    assert not game.claim_goal("a", 776, tournament.goal)
    assert game.claim_goal("a", 777, tournament.goal)
    assert game.celebrated == ["a"]
    assert not game.claim_goal("a", 900, tournament.goal)
    assert game.claim_goal("b", 800, tournament.goal)
    clone = Game.from_dict(game.to_dict())
    assert clone.celebrated == ["a", "b"]
    assert not clone.claim_goal("b", 800, tournament.goal)


def test_three_teams_roundtrip() -> None:
    from yatzy.models import Team, Tournament

    extra = Team("Третьи", [], "#6C8CFF", "team-c")
    tournament = create_tournament(extra_teams=[extra])
    assert [key for key, _team in tournament.iter_teams()] == ["a", "b", "team-c"]
    game = tournament.games[0]
    assert game.sides() == ["a", "b", "team-c"]
    game.columns("team-c")[0].set("chance", 18)
    assert game.team_total("team-c") == 18
    loaded = Tournament.from_dict(tournament.to_dict())
    assert loaded.extra_teams[0].name == "Третьи"
    assert loaded.games[0].team_total("team-c") == 18
