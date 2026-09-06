from __future__ import annotations

from yatzy.models import Game, PlayerColumn, Tournament, empty_scores


def _column(name: str, values: dict[str, int]) -> PlayerColumn:
    scores = empty_scores()
    scores.update(values)
    return PlayerColumn(name=name, scores=scores)


def current_tournament() -> Tournament:
    """Текущий турнир из таблицы «ЯЦЗЫ»: три сыгранных матча и пустая 4-я игра."""
    tournament = Tournament(name="Яцзы")
    tournament.games = [_game_one(), _game_two(), _game_three()]
    tournament.add_game()
    tournament.sync_rosters()
    return tournament


def _game_one() -> Game:
    return Game(
        title="1-я игра",
        team_a=[
            _column("1", _scores(1, 6, 6, 4, 10, 12, None, None, 27, 30, 0, 25, 28, 23, 0)),
            _column("2", _scores(3, 0, 12, 4, 10, 18, None, None, 20, 30, 0, 25, 27, 16, 0)),
            _column("3", _scores(1, 0, 3, 0, 15, 18, None, None, 25, 30, 40, 25, 0, 26, 0)),
        ],
        team_b=[
            _column("1", _scores(3, 0, 3, 8, 15, 12, None, None, 27, 30, 40, 25, 26, 19, 0)),
            _column("2", _scores(4, 4, 3, 20, 20, 24, None, None, 27, 30, 40, 25, 0, 22, 50)),
            _column("3", _scores(0, 2, 6, 16, 20, 18, None, None, 23, 30, 40, 25, 29, 22, 0)),
        ],
    )


def _game_two() -> Game:
    return Game(
        title="2-я игра",
        team_a=[
            _column("1", _scores(3, 4, 0, 4, 10, 12, None, None, 23, 30, 40, 25, 29, 22, 50)),
            _column("2", _scores(2, 2, 9, 12, 15, 24, None, None, 17, 30, 40, 25, 18, 20, 0)),
            _column("3", _scores(1, 0, 6, 4, 15, 24, None, None, 25, 30, 40, 25, 0, 19, 0)),
        ],
        team_b=[
            _column("1", _scores(1, 6, 9, 16, 10, 24, None, None, 27, 30, 40, 25, 29, 24, 0)),
            _column("2", _scores(3, 4, 3, 8, 15, 24, None, None, 24, 30, 40, 25, 21, 27, 0)),
            _column("3", _scores(4, 8, 9, 8, 15, 6, None, None, 24, 30, 40, 25, 29, 19, 0)),
        ],
    )


def _game_three() -> Game:
    return Game(
        title="3-я игра",
        team_a=[
            _column("1", _scores(1, 2, 3, 12, 15, 12, 17, 20, 18, 30, 40, 0, 0, 19, 0)),
            _column("2", _scores(3, 4, 12, 8, 15, 24, 0, 19, 28, 30, 40, 25, 25, 19, 0)),
            _column("3", _scores(2, 8, 12, 12, 15, 24, 23, 22, 15, 30, 40, 25, 0, 25, 0)),
        ],
        team_b=[
            _column("1", _scores(3, 6, 9, 12, 15, 18, 15, 19, 24, 30, 40, 25, 0, 21, 0)),
            _column("2", _scores(3, 6, 6, 12, 15, 24, 21, 23, 26, 30, 0, 25, 0, 26, 50)),
            _column("3", _scores(4, 2, 6, 8, 15, 24, 19, 11, 24, 30, 40, 25, 29, 22, 0)),
        ],
    )


def _scores(
    ones: int | None,
    twos: int | None,
    threes: int | None,
    fours: int | None,
    fives: int | None,
    sixes: int | None,
    pair: int | None,
    two_pairs: int | None,
    three_kind: int | None,
    small_straight: int | None,
    large_straight: int | None,
    full_house: int | None,
    four_kind: int | None,
    chance: int | None,
    yatzy: int | None,
) -> dict[str, int | None]:
    return {
        "ones": ones,
        "twos": twos,
        "threes": threes,
        "fours": fours,
        "fives": fives,
        "sixes": sixes,
        "pair": pair,
        "two_pairs": two_pairs,
        "three_kind": three_kind,
        "small_straight": small_straight,
        "large_straight": large_straight,
        "full_house": full_house,
        "four_kind": four_kind,
        "chance": chance,
        "yatzy": yatzy,
    }
