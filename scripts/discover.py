"""Пополняет каталог: популярные игры с хорошими отзывами по нашим жанрам (теги SteamSpy)
плюс игры из текущих распродаж Steam. Игры с взрослым контентом остаются (Witcher, Cyberpunk и т.д.),
исключены только откровенно порнографические (теги Hentai, NSFW)."""
import json, time, datetime, urllib.request, urllib.parse
MAP = {"story": ["Story Rich"], "coop": ["Co-op", "Online Co-Op"], "shooter": ["Shooter", "FPS", "Third-Person Shooter"],
       "openworld": ["Open World"], "horror": ["Horror"], "indie": ["Indie"], "racing": ["Racing"], "strategy": ["Strategy"]}
BAD = ["Hentai", "NSFW"]
MIN_REV, MIN_PCT, BIG_REV = 3000, 0.70, 15000   # минимум отзывов; доля положительных; а у очень популярных (от BIG_REV отзывов) рейтинг не важен
MAX_NEW, MAX_TOTAL = 400, 900   # сколько новых за запуск и размер каталога
SEED = [{"id":1091500,"name":"Cyberpunk 2077","tags":["story","openworld","shooter"]},{"id":292030,"name":"The Witcher 3: Wild Hunt","tags":["story","openworld"]},{"id":1174180,"name":"Red Dead Redemption 2","tags":["story","openworld"]},{"id":1086940,"name":"Baldur's Gate 3","tags":["story","coop"]},{"id":632470,"name":"Disco Elysium","tags":["story"]},{"id":1245620,"name":"Elden Ring","tags":["openworld","coop"]},{"id":1145360,"name":"Hades","tags":["indie"]},{"id":367520,"name":"Hollow Knight","tags":["indie"]},{"id":413150,"name":"Stardew Valley","tags":["indie","coop"]},{"id":1426210,"name":"It Takes Two","tags":["coop","story"]},{"id":553850,"name":"Helldivers 2","tags":["coop","shooter"]},{"id":550,"name":"Left 4 Dead 2","tags":["coop","shooter"]},{"id":548430,"name":"Deep Rock Galactic","tags":["coop","shooter"]},{"id":782330,"name":"DOOM Eternal","tags":["shooter"]},{"id":397540,"name":"Borderlands 3","tags":["shooter","coop","openworld"]},{"id":892970,"name":"Valheim","tags":["coop","openworld"]},{"id":105600,"name":"Terraria","tags":["coop","indie","openworld"]},{"id":271590,"name":"Grand Theft Auto V","tags":["openworld","story"]},{"id":377160,"name":"Fallout 4","tags":["openworld","story","shooter"]},{"id":489830,"name":"The Elder Scrolls V: Skyrim SE","tags":["openworld","story"]},{"id":990080,"name":"Hogwarts Legacy","tags":["openworld","story"]},{"id":1151640,"name":"Horizon Zero Dawn","tags":["openworld","story"]},{"id":1593500,"name":"God of War","tags":["story"]},{"id":1888930,"name":"The Last of Us Part I","tags":["story","horror"]},{"id":2050650,"name":"Resident Evil 4","tags":["horror","shooter","story"]},{"id":1182900,"name":"A Plague Tale: Requiem","tags":["story","horror"]},{"id":739630,"name":"Phasmophobia","tags":["horror","coop"]},{"id":1966720,"name":"Lethal Company","tags":["horror","coop","indie"]},{"id":1551360,"name":"Forza Horizon 5","tags":["racing","openworld"]},{"id":289070,"name":"Sid Meier's Civilization VI","tags":["strategy"]},{"id":646570,"name":"Slay the Spire","tags":["strategy","indie"]},{"id":1517290,"name":"Battlefield 2042","tags":["shooter","coop"]},{"id":1238840,"name":"Battlefield 1","tags":["shooter"]},{"id":730,"name":"Counter-Strike 2","tags":["shooter", "coop"],"f":1},{"id":570,"name":"Dota 2","tags":["strategy", "coop"],"f":1},{"id":440,"name":"Team Fortress 2","tags":["shooter", "coop"],"f":1},{"id":1172470,"name":"Apex Legends","tags":["shooter", "coop"],"f":1},{"id":230410,"name":"Warframe","tags":["shooter", "coop", "openworld"],"f":1},{"id":238960,"name":"Path of Exile","tags":["coop"],"f":1},{"id":1085660,"name":"Destiny 2","tags":["shooter", "coop", "story"],"f":1},{"id":578080,"name":"PUBG: BATTLEGROUNDS","tags":["shooter", "openworld"],"f":1},{"id":1599340,"name":"Lost Ark","tags":["coop", "openworld"],"f":1},{"id":2073850,"name":"THE FINALS","tags":["shooter", "coop"],"f":1},{"id":2767030,"name":"Marvel Rivals","tags":["shooter", "coop"],"f":1},{"id":1097150,"name":"Fall Guys","tags":["coop"],"f":1},{"id":304930,"name":"Unturned","tags":["coop", "openworld"],"f":1},{"id":444090,"name":"Paladins","tags":["shooter"],"f":1},{"id":236390,"name":"War Thunder","tags":["shooter"],"f":1},{"id":2507950,"name":"Delta Force","tags":["shooter", "coop"],"f":1},{"id":291550,"name":"Brawlhalla","tags":["coop"],"f":1}]  # стартовые игры: возвращаются в каталог, если пропали

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
have = {g["id"] for g in games}
games += [g for g in SEED if g["id"] not in have]   # вернуть стартовые игры

bad = set()
for t in BAD:
    bad |= {int(k) for k in spy(request="tag", tag=t)}
    time.sleep(2)
print("исключено откровенно порнографических игр:", len(bad))

cand = {}
for key, tags in MAP.items():
    for t in tags:
        for k, v in spy(request="tag", tag=t).items():
            i = int(k); pos, neg = v.get("positive", 0), v.get("negative", 0); tot = pos + neg
            if i in bad or tot < MIN_REV or not v.get("name") or (pos / tot < MIN_PCT and tot < BIG_REV): continue
            c = cand.setdefault(i, {"name": v["name"], "tags": set(), "tot": tot, "pct": round(100 * pos / tot), "o": v.get("owners", ""), "f": v.get("price") == "0" and v.get("initialprice") == "0"})
            c["tags"].add(key)
        time.sleep(2)
# Самые популярные игры по числу игроков (топы SteamSpy): берём независимо от жанра и оценки.
# Так в каталог попадают Battlefield, Call of Duty и другие «народные» игры, у которых отзывы смешанные.
hits = set()
for req in ("top100in2weeks", "top100forever", "top100owned"):
    for k, v in spy(request=req).items():
        try: i = int(k)
        except ValueError: continue
        if not isinstance(v, dict): continue
        pos, neg = v.get("positive", 0), v.get("negative", 0); tot = pos + neg
        if i in bad or tot < MIN_REV or not v.get("name"): continue
        cand.setdefault(i, {"name": v["name"], "tags": set(), "tot": tot, "pct": round(100 * pos / tot), "o": v.get("owners", ""), "f": v.get("price") == "0" and v.get("initialprice") == "0"})
        hits.add(i)
    time.sleep(2)
print("кандидатов:", len(cand), "из них из топов популярности:", len(hits))

seed_ids = {x["id"] for x in SEED}
games = [g for g in games if g["id"] not in bad or g["id"] in seed_ids]
byid = {g["id"]: g for g in games}
for x in SEED:                      # бесплатные стартовые игры помечаем флагом f
    if x.get("f") and x["id"] in byid: byid[x["id"]]["f"] = 1
for i, c in cand.items():           # у уже известных игр дополняем жанры и отзывы
    if i in byid:
        byid[i]["tags"] = sorted(set(byid[i]["tags"]) | c["tags"])
        if c["o"]: byid[i]["o"] = c["o"]
        if c["f"]: byid[i]["f"] = 1
    rev[str(i)] = {"pct": c["pct"], "total": c["tot"], "d": today}
new = sorted((i for i in cand if i not in byid), key=lambda i: (i not in hits, -cand[i]["tot"]))   # сначала самые популярные
added = 0
for i in new:
    if i not in hits and (added >= MAX_NEW or len(games) >= MAX_TOTAL): break   # топы популярности лимит не режет
    games.append({"id": i, "name": cand[i]["name"], "tags": sorted(cand[i]["tags"]), "o": cand[i]["o"], **({"f": 1} if cand[i]["f"] else {})}); added += 1

def tagmap(d):
    """Жанры игры по тегам SteamSpy: (наши жанры, топ-теги)."""
    tags = d.get("tags") or {}
    top = [t for t, _ in sorted(tags.items(), key=lambda kv: -kv[1])[:20]] if isinstance(tags, dict) else []
    return [k for k, v in MAP.items() if any(t in top for t in v)], top

# игры из текущих распродаж и топа продаж Steam; раздачи (скидка 100%) берём всегда
try:
    fc = json.load(urllib.request.urlopen("https://store.steampowered.com/api/featuredcategories?cc=ua&l=english", timeout=30))
    known = {g["id"] for g in games}; extra, gifts, tops = [], set(), set()
    for k in ("specials", "top_sellers"):
        for it in fc.get(k, {}).get("items", []):
            x = it.get("id")
            if not x or x in known or x in bad or x in [e[0] for e in extra]: continue
            extra.append((x, it.get("name", "")))
            if it.get("discount_percent") == 100: gifts.add(x)
            if k == "top_sellers": tops.add(x)
    extra.sort(key=lambda e: e[0] not in gifts)      # раздачи первыми
    for x, name in extra[:40]:
        d = spy(request="appdetails", appid=x); mine, top = tagmap(d)
        if not any(b in top for b in BAD) and (mine or x in gifts or x in tops):
            games.append({"id": x, "name": d.get("name") or name, "tags": mine}); added += 1
            if x in gifts: print("раздача:", d.get("name") or name)
        time.sleep(1.2)
except Exception as e: print("распродажи: ошибка", e)

# у популярных игр без жанра (пришли из топов) определяем жанр по тегам SteamSpy: до 60 игр за запуск
n, drop = 0, set()
for g in games:
    if g.get("tags") or g.get("nt") or n >= 60: continue
    d = spy(request="appdetails", appid=g["id"]); n += 1
    mine, top = tagmap(d)
    if any(b in top for b in BAD): drop.add(g["id"])
    elif mine: g["tags"] = mine
    elif d.get("name"): g["nt"] = 1                 # жанров нет: больше не проверяем
    time.sleep(1.2)
games = [g for g in games if g["id"] not in drop]

json.dump(games, open("data/games.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
json.dump(rev, open("data/reviews.json", "w", encoding="utf-8"))
print("добавлено игр:", added, "всего:", len(games))
