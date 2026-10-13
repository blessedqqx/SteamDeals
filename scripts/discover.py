
"""Расширяет каталог SteamDeals популярными играми и играми из распродаж Steam."""

import json
import os
import time
import datetime
import urllib.request
import urllib.parse

MAP = {
    "story": ["Story Rich"],
    "coop": ["Co-op", "Online Co-Op"],
    "shooter": ["Shooter", "FPS", "Third-Person Shooter"],
    "openworld": ["Open World"],
    "horror": ["Horror"],
    "indie": ["Indie"],
    "racing": ["Racing"],
    "strategy": ["Strategy"],
}

# Более широкий отбор игр
MIN_REV = 500
MIN_PCT = 0.75
MAX_NEW = 1000
MAX_TOTAL = 5000


def spy(**kw):
    """Запрашивает данные SteamSpy с повторной попыткой."""
    url = "https://steamspy.com/api.php?" + urllib.parse.urlencode(kw)

    for attempt in range(3):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "SteamDeals/1.0"},
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.load(response)

            return data if isinstance(data, dict) else {}

        except Exception as error:
            print("SteamSpy: ошибка", kw, error)
            if attempt < 2:
                time.sleep(5)

    return {}


def save_json(path, data):
    """Сохраняет JSON через временный файл."""
    temp_path = path + ".tmp"

    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, separators=(",", ":"))

    os.replace(temp_path, path)


os.makedirs("data", exist_ok=True)

with open("data/games.json", encoding="utf-8") as file:
    games = json.load(file)

if not isinstance(games, list):
    raise ValueError("data/games.json должен содержать список игр")

try:
    with open("data/reviews.json", encoding="utf-8") as file:
        reviews = json.load(file)
except FileNotFoundError:
    reviews = {}

if not isinstance(reviews, dict):
    reviews = {}

today = datetime.date.today().isoformat()

# Сохраняем все существующие игры, включая игры с тегами 18+.
by_id = {}

for game in games:
    try:
        game_id = int(game["id"])
        game["id"] = game_id
        by_id[game_id] = game
    except (KeyError, TypeError, ValueError):
        print("Пропущена игра с некорректным ID:", game)

candidates = {}

# Ищем популярные игры по жанрам SteamSpy.
for category, tags in MAP.items():
    for tag in tags:
        result = spy(request="tag", tag=tag)

        for app_id, info in result.items():
            try:
                game_id = int(app_id)
                positive = int(info.get("positive", 0))
                negative = int(info.get("negative", 0))
                total = positive + negative

                if total < MIN_REV or total == 0:
                    continue

                percentage = positive / total

                if percentage < MIN_PCT or not info.get("name"):
                    continue

                candidate = candidates.setdefault(
                    game_id,
                    {
                        "name": info["name"],
                        "tags": set(),
                        "total": total,
                        "pct": round(percentage * 100),
                    },
                )

                candidate["tags"].add(category)

                # Если игра встретилась в нескольких источниках,
                # сохраняем наиболее полную статистику.
                if total > candidate["total"]:
                    candidate["total"] = total
                    candidate["pct"] = round(percentage * 100)

            except (AttributeError, TypeError, ValueError):
                continue

        print("Обработан тег:", tag)
        time.sleep(2)

print("Найдено подходящих кандидатов:", len(candidates))

# Обновляем жанры и отзывы уже известных игр.
for game_id, candidate in candidates.items():
    reviews[str(game_id)] = {
        "pct": candidate["pct"],
        "total": candidate["total"],
        "d": today,
    }

    if game_id in by_id:
        existing_tags = set(by_id[game_id].get("tags", []))
        existing_tags.update(candidate["tags"])
        by_id[game_id]["tags"] = sorted(existing_tags)

# Добавляем наиболее популярные из новых кандидатов.
new_ids = sorted(
    (game_id for game_id in candidates if game_id not in by_id),
    key=lambda game_id: -candidates[game_id]["total"],
)

added = 0

for game_id in new_ids:
    if added >= MAX_NEW or len(games) >= MAX_TOTAL:
        break

    candidate = candidates[game_id]

    game = {
        "id": game_id,
        "name": candidate["name"],
        "tags": sorted(candidate["tags"]),
    }

    games.append(game)
    by_id[game_id] = game
    added += 1

print("Добавлено из жанров:", added)

# Дополнительно проверяем текущие предложения и лидеров продаж Steam.
try:
    url = (
        "https://store.steampowered.com/api/featuredcategories"
        "?cc=ua&l=english"
    )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "SteamDeals/1.0"},
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        featured = json.load(response)

    sales_added = 0

    for section in ("specials", "top_sellers"):
        items = featured.get(section, {}).get("items", [])

        for item in items:
            if len(games) >= MAX_TOTAL:
                break

            try:
                game_id = int(item.get("id") or 0)
            except (TypeError, ValueError):
                continue

            if not game_id or game_id in by_id:
                continue

            details = spy(request="appdetails", appid=game_id)
            raw_tags = details.get("tags") or {}

            if not isinstance(raw_tags, dict):
                raw_tags = {}

            top_tags = sorted(
                raw_tags.items(),
                key=lambda pair: -pair[1],
            )[:20]

            top_tag_names = [tag for tag, _ in top_tags]

            matched_categories = [
                category
                for category, tags in MAP.items()
                if any(tag in top_tag_names for tag in tags)
            ]

            # Не фильтруем игры по возрастным тегам.
            if not matched_categories:
                continue

            game = {
                "id": game_id,
                "name": details.get("name") or item.get("name", ""),
                "tags": matched_categories,
            }

            if not game["name"]:
                continue

            games.append(game)
            by_id[game_id] = game
            sales_added += 1

            time.sleep(1.2)

        if len(games) >= MAX_TOTAL:
            break

    print("Добавлено из распродаж и топа:", sales_added)

except Exception as error:
    print("Ошибка получения предложений Steam:", error)

# Сохраняем результаты только после завершения сбора.
save_json("data/games.json", games)
save_json("data/reviews.json", reviews)

print("Добавлено новых игр всего:", added + sales_added if "sales_added" in locals() else added)
print("Всего игр в каталоге:", len(games))
print("Обновление каталога завершено.")
