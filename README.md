<p align="center">
  <img src="src/assets/icon.png" alt="Яцзы" width="168" />
</p>

<h1 align="center">Яцзы</h1>

<p align="center">
  Командный турнир на костях — без бумаги и таблиц.<br />
  Один код для Windows, macOS, Linux, Android, iOS и браузера.
</p>

<p align="center">
  <img alt="Python 3.11+" src="https://img.shields.io/badge/Python-3.11+-1A2744?style=flat-square&logo=python&logoColor=E8B86D" />
  <img alt="Flet" src="https://img.shields.io/badge/Flet-0.86-1A2744?style=flat-square&logo=flutter&logoColor=E8B86D" />
  <img alt="License MIT" src="https://img.shields.io/badge/License-MIT-1A2744?style=flat-square&logoColor=E8B86D" />
  <img alt="Platforms" src="https://img.shields.io/badge/Desktop%20·%20Mobile%20·%20Web-1A2744?style=flat-square" />
</p>

---

Вести счёт в Яцзы за столом неудобно: три раунда, две или больше команд, премия за верхний этап, кто выкинул яцзы. Это приложение повторяет логику живой турнирной таблицы — с автосуммами, победами и целью **777**.

Собрано на [Flet](https://flet.dev) и Poetry.

## Возможности

| | |
| --- | --- |
| **Турнир из 2–6 команд** | Свои имена, цвета и состав. Колонки счёта всегда три — раунды не зависят от числа игроков. |
| **Матч как на бумаге** | Единицы–шестёрки, премия 35, пары, стриты, фулл-хаус, каре, шанс и яцзы. |
| **Таблица и цель** | Баллы и победы по сыгранным матчам. Кто набрал 777 — салют. |
| **Статистика яцзы** | В клетке выбираете, кто выкинул пять одинаковых. Счётчик копится по всему турниру. |
| **Темы** | Светлая и тёмная схема, несколько палитр. Интерфейс на русском. |
| **Свои данные** | Создание с нуля или загрузка JSON. Любой турнир можно выгрузить обратно. |

На узком экране — одна команда и нижняя навигация. На широком — таблицы рядом и боковое меню.

## Правила счёта

**1 этап.** Единицы–шестёрки — сумма костей выбранного номинала. Если сумма ≥ 63, команда получает премию 35.

**2 этап.**

| Комбинация | Как считать |
| --- | --- |
| Пара, две пары, сет, каре | Есть комбинация — пишется сумма всех пяти костей (5–30) |
| Малый стрит | 4 подряд → 30 |
| Большой стрит | 5 подряд → 40 |
| Фулл-хаус | 3 + 2 → 25 |
| Яцзы | 5 одинаковых → 50 |
| Шанс | Любая сумма |

**Матч.** ИГОГО команды — сумма трёх раундов. Победа в таблице у того, чьё ИГОГО больше. Пустой матч в зачёт не идёт.

## Запуск

Нужны Python 3.11+ и [Poetry](https://python-poetry.org).

```bash
poetry install
poetry run yatzy
```

Через Flet — то же самое, плюс режим в браузере:

```bash
poetry run flet run src/main.py
poetry run flet run --web src/main.py
```

Тесты:

```bash
poetry run pytest
```

Готовый турнир из исходной таблицы лежит в `data/yatzy.json` — его можно загрузить с домашнего экрана кнопкой **+**.

## Сборка

Нужны Flutter и SDK целевой платформы. Команды из корня репозитория:

```bash
poetry run flet build apk              # Android
poetry run flet build apk --split-per-abi
poetry run flet build windows
poetry run flet build macos
poetry run flet build linux
poetry run flet build ipa              # iOS
```

APK появится в `build/apk/`. Иконка и заставка берутся из `src/assets`.

## Лицензия

[MIT](LICENSE) · Владислав Гордин
