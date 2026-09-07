from __future__ import annotations


def ru_form(count: int, one: str, few: str, many: str) -> str:
    """Русская форма существительного после числительного: 1 матч, 2 матча, 5 матчей."""
    value = abs(int(count))
    if value % 10 == 1 and value % 100 != 11:
        return one
    if value % 10 in {2, 3, 4} and value % 100 not in {12, 13, 14}:
        return few
    return many


def ru_count(count: int, one: str, few: str, many: str) -> str:
    return f"{count} {ru_form(count, one, few, many)}"


def ru_one(count: int) -> bool:
    return ru_form(count, "1", "2", "5") == "1"


def game_title(index: int) -> str:
    """Порядковый заголовок матча: 1-я игра, 2-я игра."""
    return f"{index}-я игра"


def imported_tournaments(count: int) -> str:
    noun = ru_count(count, "турнир", "турнира", "турниров")
    verb = "Загружен" if ru_one(count) else "Загружено"
    return f"{verb} {noun}"


def synced_tournaments(count: int) -> str:
    noun = ru_count(count, "турнир", "турнира", "турниров")
    verb = "Синхронизирован" if ru_one(count) else "Синхронизировано"
    return f"{verb} {noun}"
