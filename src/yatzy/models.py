from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator
from uuid import uuid4

from yatzy.ru import game_title


BONUS_THRESHOLD = 63
BONUS_POINTS = 35
DEFAULT_GOAL = 777
DICE_COUNT = 5
SUM_MIN = DICE_COUNT * 1
SUM_MAX = DICE_COUNT * 6
ROUNDS_PER_MATCH = 3
ROUND_LABELS = ("1", "2", "3")
MIN_PLAYERS = 0
MAX_PLAYERS = 12
MIN_TEAMS = 2
MAX_TEAMS = 6
DEFAULT_PLAYERS: tuple[str, ...] = ()
DEFAULT_TEAM_NAMES: tuple[str, ...] = ("Кресельники", "Диванные войска")


class ScoreKind(str, Enum):
    COUNT = "count"
    SUM = "sum"
    FIXED = "fixed"


@dataclass(frozen=True, slots=True)
class Category:
    key: str
    title: str
    hint: str
    kind: ScoreKind
    stage: int
    face: int | None = None
    fixed_score: int | None = None
    max_score: int = 30

    @property
    def label(self) -> str:
        return self.title


UPPER_CATEGORIES: tuple[Category, ...] = (
    Category("ones", "Единицы", "сумма 1", ScoreKind.COUNT, 1, face=1, max_score=5),
    Category("twos", "Двойки", "сумма 2", ScoreKind.COUNT, 1, face=2, max_score=10),
    Category("threes", "Тройки", "сумма 3", ScoreKind.COUNT, 1, face=3, max_score=15),
    Category("fours", "Четвёрки", "сумма 4", ScoreKind.COUNT, 1, face=4, max_score=20),
    Category("fives", "Пятёрки", "сумма 5", ScoreKind.COUNT, 1, face=5, max_score=25),
    Category("sixes", "Шестерки", "сумма 6", ScoreKind.COUNT, 1, face=6, max_score=30),
)

LOWER_CATEGORIES: tuple[Category, ...] = (
    Category("pair", "Пара", "2 одинаковых · сумма всех", ScoreKind.SUM, 2, max_score=SUM_MAX),
    Category("two_pairs", "Две пары", "2 пары · сумма всех", ScoreKind.SUM, 2, max_score=SUM_MAX),
    Category("three_kind", "Сет", "3 одинаковых · сумма всех", ScoreKind.SUM, 2, max_score=SUM_MAX),
    Category(
        "small_straight",
        "М. стрит",
        "4 подряд · 30",
        ScoreKind.FIXED,
        2,
        fixed_score=30,
        max_score=30,
    ),
    Category(
        "large_straight",
        "Б. стрит",
        "5 подряд · 40",
        ScoreKind.FIXED,
        2,
        fixed_score=40,
        max_score=40,
    ),
    Category(
        "full_house",
        "Фулл-хаус",
        "3+2 · 25",
        ScoreKind.FIXED,
        2,
        fixed_score=25,
        max_score=25,
    ),
    Category("four_kind", "Каре", "4 одинаковых · сумма всех", ScoreKind.SUM, 2, max_score=SUM_MAX),
    Category("chance", "Шанс", "любые · сумма всех", ScoreKind.SUM, 2, max_score=SUM_MAX),
    Category(
        "yatzy",
        "Яцзы",
        "5 одинаковых · 50",
        ScoreKind.FIXED,
        2,
        fixed_score=50,
        max_score=50,
    ),
)

ALL_CATEGORIES: tuple[Category, ...] = UPPER_CATEGORIES + LOWER_CATEGORIES
CATEGORY_BY_KEY: dict[str, Category] = {item.key: item for item in ALL_CATEGORIES}


def new_id() -> str:
    return uuid4().hex


def empty_scores() -> dict[str, int | None]:
    return {item.key: None for item in ALL_CATEGORIES}


@dataclass(slots=True)
class ColumnTotals:
    upper: int
    to_bonus: int
    bonus: int
    stage1: int
    stage2: int
    total: int
    filled: int
    remaining: int


@dataclass(slots=True)
class PlayerColumn:
    name: str
    scores: dict[str, int | None] = field(default_factory=empty_scores)
    yatzy_player_id: str | None = None
    yatzy_player_name: str | None = None

    def get(self, key: str) -> int | None:
        return self.scores.get(key)

    def set(self, key: str, value: int | None) -> None:
        category = CATEGORY_BY_KEY.get(key)
        self.scores[key] = clamp_score(category, value) if category else value
        if key == "yatzy" and self.scores[key] != 50:
            self.yatzy_player_id = None
            self.yatzy_player_name = None

    def set_yatzy(self, value: int | None, player: TeamPlayer | None = None) -> None:
        self.set("yatzy", value)
        if self.get("yatzy") == 50 and player is not None:
            self.yatzy_player_id = player.id
            self.yatzy_player_name = player.name
        elif self.get("yatzy") != 50:
            self.yatzy_player_id = None
            self.yatzy_player_name = None

    def has_any_score(self) -> bool:
        return any(value is not None for value in self.scores.values())

    def totals(self) -> ColumnTotals:
        upper = sum(_or_zero(self.scores.get(item.key)) for item in UPPER_CATEGORIES)
        stage2 = sum(_or_zero(self.scores.get(item.key)) for item in LOWER_CATEGORIES)
        bonus = BONUS_POINTS if upper >= BONUS_THRESHOLD else 0
        filled = sum(1 for value in self.scores.values() if value is not None)
        return ColumnTotals(
            upper=upper,
            to_bonus=max(0, BONUS_THRESHOLD - upper),
            bonus=bonus,
            stage1=upper + bonus,
            stage2=stage2,
            total=upper + bonus + stage2,
            filled=filled,
            remaining=len(ALL_CATEGORIES) - filled,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "scores": dict(self.scores),
            "yatzy_player_id": self.yatzy_player_id,
            "yatzy_player_name": self.yatzy_player_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PlayerColumn:
        scores = empty_scores()
        raw = data.get("scores") or {}
        for key in scores:
            if key in raw:
                scores[key] = raw[key]
        column = cls(
            name=str(data.get("name") or "1"),
            scores=scores,
            yatzy_player_id=data.get("yatzy_player_id"),
            yatzy_player_name=data.get("yatzy_player_name"),
        )
        for key, value in list(column.scores.items()):
            category = CATEGORY_BY_KEY.get(key)
            if category:
                column.scores[key] = clamp_score(category, value)
        if column.get("yatzy") != 50:
            column.yatzy_player_id = None
            column.yatzy_player_name = None
        return column


@dataclass(slots=True)
class TeamPlayer:
    name: str
    id: str = field(default_factory=new_id)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}

    @classmethod
    def from_dict(cls, data: dict | str) -> TeamPlayer:
        if isinstance(data, str):
            return cls(name=data.strip())
        return cls(
            name=str(data.get("name") or "").strip(),
            id=str(data.get("id") or new_id()),
        )


@dataclass(slots=True)
class DraftPlayer:
    name: str
    source_index: int | None = None
    player_id: str | None = None


@dataclass(slots=True)
class SetupTeam:
    name: str
    color: str
    players: list[DraftPlayer] = field(default_factory=list)
    key: str = ""


@dataclass(slots=True)
class YatzyStat:
    player_id: str
    name: str
    count: int


@dataclass(slots=True)
class Team:
    name: str
    players: list[TeamPlayer] = field(default_factory=list)
    color: str = ""
    id: str = ""

    def __post_init__(self) -> None:
        self.players = _normalize_players(self.players)

    @property
    def player_names(self) -> list[str]:
        return [player.name for player in self.players]

    def player_by_id(self, player_id: str | None) -> TeamPlayer | None:
        if not player_id:
            return None
        for player in self.players:
            if player.id == player_id:
                return player
        return None

    def to_dict(self) -> dict:
        payload = {
            "name": self.name,
            "players": [player.to_dict() for player in self.players],
            "color": self.color,
        }
        if self.id:
            payload["id"] = self.id
        return payload

    @classmethod
    def from_dict(cls, data: dict) -> Team:
        return cls(
            name=str(data.get("name") or "Команда"),
            players=_players_from_raw(data.get("players")),
            color=str(data.get("color") or ""),
            id=str(data.get("id") or ""),
        )


@dataclass(slots=True)
class Game:
    id: str = field(default_factory=new_id)
    title: str = "Игра"
    team_a: list[PlayerColumn] = field(default_factory=list)
    team_b: list[PlayerColumn] = field(default_factory=list)
    extra_sheets: dict[str, list[PlayerColumn]] = field(default_factory=dict)
    celebrated: list[str] = field(default_factory=list)

    @classmethod
    def from_template(cls, title: str, left: Team | None = None, right: Team | None = None) -> Game:
        game = cls(title=title)
        game.ensure_rounds()
        return game

    def ensure_columns(self, left: Team | None = None, right: Team | None = None) -> None:
        self.ensure_rounds()

    def ensure_sides(self, extra_ids: list[str]) -> None:
        wanted = [key for key in extra_ids if key and key not in {"a", "b"}]
        for key in wanted:
            if key not in self.extra_sheets:
                self.extra_sheets[key] = []
        self.extra_sheets = {key: self.extra_sheets[key] for key in wanted}
        self.ensure_rounds()

    def ensure_rounds(self) -> None:
        self.team_a = _align_columns(self.team_a, list(ROUND_LABELS))
        self.team_b = _align_columns(self.team_b, list(ROUND_LABELS))
        self.extra_sheets = {
            key: _align_columns(columns, list(ROUND_LABELS)) for key, columns in self.extra_sheets.items()
        }

    def sides(self) -> list[str]:
        return ["a", "b", *self.extra_sheets.keys()]

    def columns(self, side: str) -> list[PlayerColumn]:
        if side == "a":
            return self.team_a
        if side == "b":
            return self.team_b
        if side not in self.extra_sheets:
            self.extra_sheets[side] = _align_columns([], list(ROUND_LABELS))
        return self.extra_sheets[side]

    def all_columns(self) -> list[PlayerColumn]:
        columns = [*self.team_a, *self.team_b]
        for sheet in self.extra_sheets.values():
            columns.extend(sheet)
        return columns

    def team_total(self, side: str) -> int:
        return sum(column.totals().total for column in self.columns(side))

    def is_started(self) -> bool:
        return any(column.has_any_score() for column in self.all_columns())

    def is_complete(self) -> bool:
        return all(column.totals().remaining == 0 for column in self.all_columns())

    def claim_goal(self, side: str, total: int, goal: int) -> bool:
        if total < goal or side in self.celebrated:
            return False
        self.celebrated.append(side)
        return True

    def winner_side(self) -> str | None:
        if not self.is_started():
            return None
        scores = {side: self.team_total(side) for side in self.sides()}
        best = max(scores.values())
        winners = [side for side, total in scores.items() if total == best]
        return winners[0] if len(winners) == 1 else None

    def to_dict(self) -> dict:
        payload = {
            "id": self.id,
            "title": self.title,
            "team_a": [column.to_dict() for column in self.team_a],
            "team_b": [column.to_dict() for column in self.team_b],
            "celebrated": list(self.celebrated),
        }
        if self.extra_sheets:
            payload["extra_sheets"] = {
                key: [column.to_dict() for column in columns] for key, columns in self.extra_sheets.items()
            }
        return payload

    @classmethod
    def from_dict(cls, data: dict) -> Game:
        extra_raw = data.get("extra_sheets") or {}
        extra_sheets = {
            str(key): [PlayerColumn.from_dict(item) for item in columns or []]
            for key, columns in extra_raw.items()
            if str(key) not in {"a", "b"}
        }
        allowed = {"a", "b", *extra_sheets}
        celebrated = [str(item) for item in data.get("celebrated") or [] if str(item) in allowed]
        return cls(
            id=str(data.get("id") or new_id()),
            title=str(data.get("title") or "Игра"),
            team_a=[PlayerColumn.from_dict(item) for item in data.get("team_a") or []],
            team_b=[PlayerColumn.from_dict(item) for item in data.get("team_b") or []],
            extra_sheets=extra_sheets,
            celebrated=celebrated,
        )


@dataclass(slots=True)
class Tournament:
    id: str = field(default_factory=new_id)
    name: str = "Яцзы"
    goal: int = DEFAULT_GOAL
    team_a: Team = field(default_factory=lambda: Team("Кресельники"))
    team_b: Team = field(default_factory=lambda: Team("Диванные войска"))
    extra_teams: list[Team] = field(default_factory=list)
    games: list[Game] = field(default_factory=list)

    def iter_teams(self) -> list[tuple[str, Team]]:
        items = [("a", self.team_a), ("b", self.team_b)]
        for team in self.extra_teams:
            if not team.id:
                team.id = new_id()
            items.append((team.id, team))
        return items

    def team_keys(self) -> list[str]:
        return [key for key, _team in self.iter_teams()]

    def team(self, side: str) -> Team:
        for key, team in self.iter_teams():
            if key == side:
                return team
        return self.team_b if side == "b" else self.team_a

    def game_by_id(self, game_id: str) -> Game | None:
        for game in self.games:
            if game.id == game_id:
                return game
        return None

    def sync_rosters(self) -> None:
        extra_ids = [team.id for _key, team in self.iter_teams() if _key not in {"a", "b"}]
        for game in self.games:
            game.ensure_sides(extra_ids)

    def apply_roster(self, side: str, drafts: list[DraftPlayer]) -> None:
        old = self.team(side).players
        players: list[TeamPlayer] = []
        for index, draft in enumerate(drafts[:MAX_PLAYERS]):
            name = draft.name.strip()
            if not name:
                continue
            player_id = draft.player_id
            if not player_id and draft.source_index is not None and 0 <= draft.source_index < len(old):
                player_id = old[draft.source_index].id
            players.append(TeamPlayer(name=name, id=player_id or new_id()))
        self.team(side).players = players

    def yatzy_stats(self, side: str) -> list[YatzyStat]:
        roster = {player.id: player for player in self.team(side).players}
        stats: dict[str, YatzyStat] = {}
        for game in self.games:
            for column in game.columns(side):
                if column.get("yatzy") != 50:
                    continue
                player_id = column.yatzy_player_id or ""
                if player_id and player_id in roster:
                    name = roster[player_id].name
                elif column.yatzy_player_name:
                    name = column.yatzy_player_name
                    player_id = player_id or column.yatzy_player_name
                else:
                    player_id = "_unassigned"
                    name = "Не указано"
                item = stats.get(player_id)
                if item is None:
                    stats[player_id] = YatzyStat(player_id=player_id, name=name, count=1)
                else:
                    item.count += 1
                    item.name = name
        return sorted(stats.values(), key=lambda item: (-item.count, item.name))

    def add_game(self) -> Game:
        """Новый матч как копия листа «Шаблон»: пустые клетки и строка в таблице."""
        game = Game.from_template(game_title(len(self.games) + 1), self.team_a, self.team_b)
        game.ensure_sides([team.id for team in self.extra_teams if team.id])
        self.games.append(game)
        return game

    def remove_game(self, game_id: str) -> None:
        self.games = [game for game in self.games if game.id != game_id]
        for index, game in enumerate(self.games, start=1):
            if game.title.endswith(" игра") or game.title[:1].isdigit():
                game.title = game_title(index)

    def points(self, side: str) -> int:
        return sum(game.team_total(side) for game in self.games if game.is_started())

    def wins(self, side: str) -> int:
        return sum(1 for game in self.games if game.winner_side() == side)

    def progress(self, side: str) -> float:
        if self.goal <= 0:
            return 0.0
        return min(1.0, self.points(side) / self.goal)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "goal": self.goal,
            "team_a": self.team_a.to_dict(),
            "team_b": self.team_b.to_dict(),
            "extra_teams": [team.to_dict() for team in self.extra_teams],
            "games": [game.to_dict() for game in self.games],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Tournament:
        extra = [Team.from_dict(item) for item in data.get("extra_teams") or [] if isinstance(item, dict)]
        for team in extra:
            if not team.id:
                team.id = new_id()
        tournament = cls(
            id=str(data.get("id") or new_id()),
            name=str(data.get("name") or "Яцзы"),
            goal=int(data.get("goal") or DEFAULT_GOAL),
            team_a=Team.from_dict(data.get("team_a") or {"name": "Кресельники"}),
            team_b=Team.from_dict(data.get("team_b") or {"name": "Диванные войска"}),
            extra_teams=extra,
            games=[Game.from_dict(item) for item in data.get("games") or []],
        )
        tournament.sync_rosters()
        return tournament


@dataclass(slots=True)
class AppState:
    tournaments: list[Tournament] = field(default_factory=list)
    active_tournament_id: str | None = None
    active_game_id: str | None = None
    theme_mode: str = "dark"
    theme_id: str = "amber"

    def iter_tournaments(self) -> Iterator[Tournament]:
        return iter(self.tournaments)

    def tournament_by_id(self, tournament_id: str | None) -> Tournament | None:
        if not tournament_id:
            return None
        for tournament in self.tournaments:
            if tournament.id == tournament_id:
                return tournament
        return None

    @property
    def active_tournament(self) -> Tournament | None:
        return self.tournament_by_id(self.active_tournament_id)

    @property
    def active_game(self) -> Game | None:
        tournament = self.active_tournament
        if tournament is None or not self.active_game_id:
            return None
        return tournament.game_by_id(self.active_game_id)

    def add_tournament(self, tournament: Tournament) -> None:
        self.tournaments.insert(0, tournament)
        self.active_tournament_id = tournament.id
        self.active_game_id = tournament.games[0].id if tournament.games else None

    def import_tournaments(self, incoming: list[Tournament]) -> int:
        from yatzy.io import merge_tournaments

        if not incoming:
            return 0
        self.tournaments = merge_tournaments(self.tournaments, incoming)
        self.active_tournament_id = incoming[0].id
        current = self.active_tournament
        self.active_game_id = current.games[0].id if current and current.games else None
        return len(incoming)

    def delete_tournament(self, tournament_id: str) -> None:
        self.tournaments = [item for item in self.tournaments if item.id != tournament_id]
        if self.active_tournament_id == tournament_id:
            current = self.tournaments[0] if self.tournaments else None
            self.active_tournament_id = current.id if current else None
            self.active_game_id = current.games[0].id if current and current.games else None

    def to_dict(self) -> dict:
        return {
            "tournaments": [item.to_dict() for item in self.tournaments],
            "active_tournament_id": self.active_tournament_id,
            "active_game_id": self.active_game_id,
            "theme_mode": self.theme_mode,
            "theme_id": self.theme_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AppState:
        return cls(
            tournaments=[Tournament.from_dict(item) for item in data.get("tournaments") or []],
            active_tournament_id=data.get("active_tournament_id"),
            active_game_id=data.get("active_game_id"),
            theme_mode=str(data.get("theme_mode") or "dark"),
            theme_id=str(data.get("theme_id") or "amber"),
        )


def create_tournament(
    name: str = "Яцзы",
    team_a: str = "Кресельники",
    team_b: str = "Диванные войска",
    players_a: list[str] | None = None,
    players_b: list[str] | None = None,
    goal: int = DEFAULT_GOAL,
    color_a: str = "",
    color_b: str = "",
    extra_teams: list[Team] | None = None,
) -> Tournament:
    tournament = Tournament(
        name=name.strip() or "Яцзы",
        goal=max(1, goal),
        team_a=Team(team_a.strip() or "Команда A", _players_from_raw(players_a), color_a),
        team_b=Team(team_b.strip() or "Команда B", _players_from_raw(players_b), color_b),
        extra_teams=list(extra_teams or []),
    )
    tournament.add_game()
    return tournament


def suggested_score(category: Category, count: int) -> int:
    if category.kind == ScoreKind.COUNT and category.face is not None:
        return max(0, min(DICE_COUNT, count)) * category.face
    if category.kind == ScoreKind.FIXED and category.fixed_score is not None:
        return category.fixed_score if count else 0
    return count


def clamp_score(category: Category, value: int | None) -> int | None:
    if value is None:
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if category.kind == ScoreKind.COUNT and category.face:
        count = max(0, min(DICE_COUNT, round(number / category.face))) if number else 0
        if number and number % category.face == 0:
            count = max(0, min(DICE_COUNT, number // category.face))
        return count * category.face
    if category.kind == ScoreKind.FIXED and category.fixed_score is not None:
        if number <= 0:
            return 0
        return category.fixed_score
    if number <= 0:
        return 0
    return max(SUM_MIN, min(SUM_MAX, number))


def _align_columns(columns: list[PlayerColumn], names: list[str]) -> list[PlayerColumn]:
    aligned: list[PlayerColumn] = []
    for index, name in enumerate(names):
        if index < len(columns):
            columns[index].name = name
            aligned.append(columns[index])
        else:
            aligned.append(PlayerColumn(name=name))
    return aligned


def _players_from_raw(raw: list | tuple | None) -> list[TeamPlayer]:
    if not raw:
        return []
    if list(raw) == list(ROUND_LABELS):
        return []
    players: list[TeamPlayer] = []
    for item in raw:
        player = item if isinstance(item, TeamPlayer) else TeamPlayer.from_dict(item)
        if player.name:
            players.append(player)
    return players[:MAX_PLAYERS]


def _normalize_players(players: list[TeamPlayer] | list[str]) -> list[TeamPlayer]:
    return _players_from_raw(players)


def _or_zero(value: int | None) -> int:
    return 0 if value is None else value
