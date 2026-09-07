from __future__ import annotations

import json
from pathlib import Path

from yatzy.models import Tournament, new_id

FORMAT_TOURNAMENT = "yatzy.tournament"
FORMAT_PACK = "yatzy.pack"
EXPORT_VERSION = 1


def tournament_payload(tournament: Tournament) -> dict:
    return {
        "format": FORMAT_TOURNAMENT,
        "version": EXPORT_VERSION,
        "tournament": tournament.to_dict(),
    }


def pack_payload(tournaments: list[Tournament]) -> dict:
    return {
        "format": FORMAT_PACK,
        "version": EXPORT_VERSION,
        "tournaments": [item.to_dict() for item in tournaments],
    }


def dumps_tournament(tournament: Tournament) -> str:
    return json.dumps(tournament_payload(tournament), ensure_ascii=False, indent=2)


def dumps_pack(tournaments: list[Tournament]) -> str:
    return json.dumps(pack_payload(tournaments), ensure_ascii=False, indent=2)


def parse_tournaments(raw: str | bytes | dict | list, allow_empty: bool = False) -> list[Tournament]:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw) if isinstance(raw, str) else raw
    items = _extract_dicts(data)
    if not items:
        if allow_empty and isinstance(data, dict) and isinstance(data.get("tournaments"), list):
            return []
        raise ValueError("В файле нет турнира Яцзы.")
    return [Tournament.from_dict(item) for item in items]


def read_tournaments(path: str | Path) -> list[Tournament]:
    return parse_tournaments(Path(path).read_text(encoding="utf-8"))


def write_tournament(path: str | Path, tournament: Tournament) -> None:
    Path(path).write_text(dumps_tournament(tournament), encoding="utf-8")


def suggested_filename(tournament: Tournament) -> str:
    name = "".join(char if char.isalnum() or char in " -_" else "" for char in tournament.name).strip()
    slug = "-".join(name.split()) or "yatzy"
    return f"{slug}.json"


def merge_tournaments(existing: list[Tournament], incoming: list[Tournament]) -> list[Tournament]:
    by_id = {item.id: item for item in existing}
    order = list(existing)
    for item in reversed(incoming):
        if item.id in by_id:
            index = next(i for i, current in enumerate(order) if current.id == item.id)
            order[index] = item
            by_id[item.id] = item
        else:
            if not item.id:
                item.id = new_id()
            order.insert(0, item)
            by_id[item.id] = item
    return order


def _extract_dicts(data: object) -> list[dict]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    if isinstance(data.get("tournament"), dict):
        return [data["tournament"]]
    if isinstance(data.get("tournaments"), list):
        return [item for item in data["tournaments"] if isinstance(item, dict)]
    if "games" in data or "team_a" in data or "extra_teams" in data:
        return [data]
    return []
