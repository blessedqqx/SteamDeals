"""Пополняет каталог: популярные игры с хорошими отзывами по нашим жанрам (теги SteamSpy)
плюс игры из текущих распродаж Steam. 18+ контент отсеивается по тегам."""
import json, time, datetime, urllib.request, urllib.parse
MAP = {"story": ["Story Rich"], "coop": ["Co-op", "Online Co-Op"], "shooter": ["Shooter", "FPS", "Third-Person Shooter"],
       "openworld": ["Open World"], "horror": ["Horror"], "indie": ["Indie"], "racing": ["Racing"], "strategy": ["Strategy"]}
BAD = ["Sexual Content", "Nudity", "NSFW", "Hentai", "Mature"]
MIN_REV, MIN_PCT = 3000, 0.80   # минимум отзывов и доля положительных
MAX_NEW, MAX_TOTAL = 400, 900   # сколько новых за запуск и размер каталога

def spy(**kw):
    url = "https://steamspy.com/api.php?" + urllib.parse.urlencode(kw)
    for _ in range(2):
        try: return json.load(urllib.request.urlopen(url, timeout=180))
        except Exception as e: print(kw, "ошибка", e); time.sleep(5)
    return {}

games = json.load(open("data/games.json", encoding="utf-8"))
try: rev = json.load(open("data/reviews.json", encoding="utf-8"))
except Exception: rev = {}
today = datetime.date.today().isoformat()

bad = set()
for t in BAD:
    bad |= {int(k) for k in spy(request="tag", tag=t)}
    time.sleep(2)
print("исключено по 18+ тегам:", len(bad))

cand = {}
for key, tags in MAP.items():
    for t in tags:
        for k, v in spy(request="tag", tag=t).items():
            i = int(k); pos, neg = v.get("positive", 0), v.get("negative", 0); tot = pos + neg
            if i in bad or tot < MIN_REV or pos / tot < MIN_PCT or not v.get("name"): continue
            c = cand.setdefault(i, {"name": v["name"], "tags": set(), "tot": tot, "pct": round(100 * pos / tot)})
            c["tags"].add(key)
        time.sleep(2)
print("кандидатов:", len(cand))

games = [g for g in games if g["id"] not in bad]
byid = {g["id"]: g for g in games}
for i, c in cand.items():           # у уже известных игр дополняем жанры и отзывы
    if i in byid: byid[i]["tags"] = sorted(set(byid[i]["tags"]) | c["tags"])
    rev[str(i)] = {"pct": c["pct"], "total": c["tot"], "d": today}
new = sorted((i for i in cand if i not in byid), key=lambda i: -cand[i]["tot"])
added = 0
for i in new:
    if added >= MAX_NEW or len(games) >= MAX_TOTAL: break
    games.append({"id": i, "name": cand[i]["name"], "tags": sorted(cand[i]["tags"])}); added += 1

# игры из текущих распродаж и топа Steam
try:
    fc = json.load(urllib.request.urlopen("https://store.steampowered.com/api/featuredcategories?cc=ua&l=english", timeout=30))
    known = {g["id"] for g in games}; extra = []
    for k in ("specials", "top_sellers"):
        for it in fc.get(k, {}).get("items", []):
            x = it.get("id")
            if x and x not in known and x not in bad and x not in [e[0] for e in extra]: extra.append((x, it.get("name", "")))
    for x, name in extra[:20]:
        d = spy(request="appdetails", appid=x); tags = d.get("tags") or {}
        top = [t for t, _ in sorted(tags.items(), key=lambda kv: -kv[1])[:20]] if isinstance(tags, dict) else []
        mine = [k for k, v in MAP.items() if any(t in top for t in v)]
        if mine and not any(b in top for b in BAD): games.append({"id": x, "name": d.get("name") or name, "tags": mine}); added += 1
        time.sleep(1.2)
except Exception as e: print("распродажи: ошибка", e)

json.dump(games, open("data/games.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
json.dump(rev, open("data/reviews.json", "w", encoding="utf-8"))
print("добавлено игр:", added, "всего:", len(games))
