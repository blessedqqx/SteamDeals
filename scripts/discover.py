"""Пополняет каталог: берёт игры из распродаж/топа Steam и определяет жанры по тегам SteamSpy."""
import json, time, urllib.request
MAP = {"story": ["Story Rich"], "coop": ["Co-op", "Online Co-Op"], "shooter": ["Shooter", "FPS", "Third-Person Shooter"],
       "openworld": ["Open World"], "horror": ["Horror"], "indie": ["Indie"], "racing": ["Racing"], "strategy": ["Strategy"]}
games = json.load(open("data/games.json", encoding="utf-8"))
known = {g["id"] for g in games}
fc = json.load(urllib.request.urlopen("https://store.steampowered.com/api/featuredcategories?cc=ua&l=english", timeout=30))
cand = []
for k in ("specials", "top_sellers"):
    for it in fc.get(k, {}).get("items", []):
        i = it.get("id")
        if i and i not in known and i not in [c[0] for c in cand]: cand.append((i, it.get("name", "")))
added = 0
for i, name in cand[:30]:  # не больше 30 новых за запуск
    try:
        d = json.load(urllib.request.urlopen(f"https://steamspy.com/api.php?request=appdetails&appid={i}", timeout=30))
        tags = d.get("tags") or {}
        top = [t for t, _ in sorted(tags.items(), key=lambda kv: -kv[1])[:20]] if isinstance(tags, dict) else []
        mine = [k for k, v in MAP.items() if any(x in top for x in v)]
        if mine: games.append({"id": i, "name": d.get("name") or name, "tags": mine}); added += 1
    except Exception as e: print(i, "ошибка", e)
    time.sleep(1.2)
json.dump(games, open("data/games.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("добавлено игр:", added, "всего:", len(games))
