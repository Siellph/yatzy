import pytest

from yatzy.io import merge_tournaments
from yatzy.lan_sync import SyncError, exchange, format_token, mask_code_input, new_token, parse_invite, start_host
from yatzy.models import create_tournament
from yatzy.ru import synced_tournaments


def test_parse_invite_code_and_address() -> None:
    invite = parse_invite("ab 23 cd")
    assert invite.token == "AB23CD"
    assert not invite.direct
    direct = parse_invite("192.168.1.10:18881/ab23cd")
    assert direct.host == "192.168.1.10"
    assert direct.port == 18881
    assert direct.token == "AB23CD"


def test_parse_invite_rejects_short_code() -> None:
    with pytest.raises(SyncError):
        parse_invite("AB")


def test_format_token() -> None:
    token = new_token()
    assert len(token) == 6
    assert format_token(token) == f"{token[:2]} {token[2:4]} {token[4:]}"


def test_mask_code_input_groups_like_host() -> None:
    assert mask_code_input("ab") == "AB"
    assert mask_code_input("ab2") == "AB 2"
    assert mask_code_input("ab23cd") == "AB 23 CD"
    assert mask_code_input("ab 23 cd") == "AB 23 CD"
    assert mask_code_input("192.168.1.10:18881/ab23cd") == "192.168.1.10:18881/AB23CD"


def test_http_sync_merges_both_sides() -> None:
    host_list = [create_tournament(name="Хост")]
    guest = create_tournament(name="Гость")

    def on_sync(incoming):
        merged = merge_tournaments(host_list, incoming)
        host_list[:] = merged
        return merged

    session = start_host("AB23CD", on_sync)
    try:
        result = exchange("127.0.0.1", session.port, "ab23cd", [guest])
        names = {item.name for item in result}
        assert names == {"Хост", "Гость"}
        assert {item.name for item in host_list} == names
    finally:
        session.stop()


def test_http_sync_rejects_bad_token() -> None:
    session = start_host("AB23CD", lambda incoming: incoming)
    try:
        with pytest.raises(SyncError, match="Неверный код"):
            exchange("127.0.0.1", session.port, "ZZZZZZ", [])
    finally:
        session.stop()


def test_synced_phrase() -> None:
    assert synced_tournaments(1) == "Синхронизирован 1 турнир"
    assert synced_tournaments(2) == "Синхронизировано 2 турнира"
