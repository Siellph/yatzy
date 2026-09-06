import flet as ft

from yatzy.app import _tournaments_from_picked
from yatzy.current import current_tournament
from yatzy.io import dumps_tournament, parse_tournaments


def test_parse_tournament_from_bytes() -> None:
    raw = dumps_tournament(current_tournament()).encode("utf-8")
    tournaments = parse_tournaments(raw)
    assert tournaments[0].name == "Яцзы"


def test_picked_file_uses_bytes_when_path_missing() -> None:
    raw = dumps_tournament(current_tournament()).encode("utf-8")
    picked = ft.FilePickerFile(id=1, name="yatzy.json", size=len(raw), bytes=raw)
    tournaments = _tournaments_from_picked(picked)
    assert len(tournaments) == 1
    assert tournaments[0].team_a.name == "Кресельники"
