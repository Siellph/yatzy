from yatzy.ru import game_title, imported_tournaments, ru_count, ru_form


def test_ru_count_forms() -> None:
    assert ru_count(0, "матч", "матча", "матчей") == "0 матчей"
    assert ru_count(1, "матч", "матча", "матчей") == "1 матч"
    assert ru_count(2, "матч", "матча", "матчей") == "2 матча"
    assert ru_count(4, "матч", "матча", "матчей") == "4 матча"
    assert ru_count(5, "матч", "матча", "матчей") == "5 матчей"
    assert ru_count(11, "матч", "матча", "матчей") == "11 матчей"
    assert ru_count(12, "матч", "матча", "матчей") == "12 матчей"
    assert ru_count(21, "матч", "матча", "матчей") == "21 матч"
    assert ru_count(22, "матч", "матча", "матчей") == "22 матча"
    assert ru_count(25, "матч", "матча", "матчей") == "25 матчей"


def test_ru_forms_for_scores_and_wins() -> None:
    assert ru_form(1, "победа", "победы", "побед") == "победа"
    assert ru_form(3, "победа", "победы", "побед") == "победы"
    assert ru_form(10, "победа", "победы", "побед") == "побед"
    assert ru_count(1, "балл", "балла", "баллов") == "1 балл"
    assert ru_count(22, "балл", "балла", "баллов") == "22 балла"
    assert ru_count(111, "балл", "балла", "баллов") == "111 баллов"
    assert ru_form(1, "очко", "очка", "очков") == "очко"
    assert ru_form(777, "очко", "очка", "очков") == "очков"


def test_game_title_and_import_toast() -> None:
    assert game_title(1) == "1-я игра"
    assert game_title(2) == "2-я игра"
    assert game_title(21) == "21-я игра"
    assert imported_tournaments(1) == "Загружен 1 турнир"
    assert imported_tournaments(2) == "Загружено 2 турнира"
    assert imported_tournaments(5) == "Загружено 5 турниров"
    assert imported_tournaments(21) == "Загружен 21 турнир"
