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

Нужны Flutter и SDK целевой платформы. Команды из корня репозитория. `--artifact Yatzy` нужен, чтобы на диске не оказалось имени «Яцзы». Иконка и заставка — из `src/assets`.

Общие флаги:

```text
--yes --no-rich-output --cleanup-app --exclude .flet --artifact Yatzy --build-version 0.1.0 --build-number 1
```

| Цель | Где собирать | Куда кладёт |
| --- | --- | --- |
| `apk` / `aab` | Windows, macOS, Linux | `build/apk/`, `build/aab/` |
| `windows` | Windows | `build/windows/` |
| `macos` | macOS | `build/macos/` |
| `linux` | Linux или WSL | `build/linux/` |
| `ipa` / `ios-simulator` | macOS | `build/ipa/`, `build/ios-simulator/` |
| `web` | любая ОС | `build/web/` |

### Android

```bash
poetry run flet build apk --split-per-abi --yes --no-rich-output --cleanup-app --exclude .flet --artifact Yatzy --build-version 0.1.0 --build-number 1
```

Для Google Play — `aab` вместо `apk`, без `--split-per-abi`.

### Windows

Нужны Visual Studio с workload **Desktop development with C++** и включённый режим разработчика (симлинки).

```bash
poetry run flet build windows --yes --no-rich-output --cleanup-app --exclude .flet --artifact Yatzy --build-version 0.1.0 --build-number 1
```

Результат — папка, не один exe: `Yatzy.exe`, DLL и `data/`. Для установщика берите содержимое `build/flutter/build/windows/x64/runner/Release/` целиком (Inno: главный файл `Yatzy.exe`, остальные `Release\*`, с подпапками).

### macOS

Только на Mac: Xcode 15+, CocoaPods 1.16+, на Apple Silicon — Rosetta 2. По умолчанию универсальный бандл `arm64` + `x86_64`.

```bash
poetry run flet build macos --yes --no-rich-output --cleanup-app --exclude .flet --artifact Yatzy --build-version 0.1.0 --build-number 1
```

Только своя архитектура: добавьте `--arch arm64`. Результат — `build/macos/Yatzy.app`. Подпись и нотаризация — отдельно (`--macos-distribution developer-id`).

### Linux

Только Linux или WSL. Нужны GTK 3, clang, cmake, ninja и **lld**. На Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y binutils clang cmake ninja-build pkg-config lld llvm libgtk-3-dev libsecret-1-0 libsecret-1-dev
```

```bash
poetry run flet build linux --linux-categories Game --yes --no-rich-output --cleanup-app --exclude .flet --artifact Yatzy --build-version 0.1.0 --build-number 1
```

В `build/linux/` — исполняемый файл плюс `data/`, `lib/` и Python рядом. Папку не разбрасывать. Для раздачи оберните в AppImage, deb или rpm.

### iOS

Только на Mac. Симулятор, без подписи:

```bash
poetry run flet build ios-simulator --yes --no-rich-output --cleanup-app --exclude .flet --artifact Yatzy --build-version 0.1.0 --build-number 1
```

IPA на устройство или TestFlight — Apple Developer, App ID `com.yatzy.app` и Team ID:

```bash
poetry run flet build ipa --ios-team-id ВАШ_TEAM_ID --yes --no-rich-output --cleanup-app --exclude .flet --artifact Yatzy --build-version 0.1.0 --build-number 1
```

При необходимости: `--ios-provisioning-profile "имя или UUID"` и `--ios-signing-certificate "Apple Distribution"` (или `"Apple Development"`). Без этого Flet соберёт archive без подписи — на телефон не поставить.

### Web

Статический сайт: Python в браузере (Pyodide).

```bash
poetry run flet build web --yes --no-rich-output --cleanup-app --exclude .flet --artifact Yatzy --build-version 0.1.0 --build-number 1
```

Офлайн, без CDN (пакет больше): добавьте `--no-cdn`. Если не в корне сайта: `--base-url /подкаталог/`. Проверка: `poetry run flet serve`. Хостинг — любой статический.

## Лицензия

[MIT](LICENSE) · Владислав Гордин
