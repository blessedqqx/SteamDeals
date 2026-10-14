"""Ежедневные дополнения к данным: рейтинг отзывов, описания игр (ru/uk/en), активность игроков по месяцам.
Каждая часть работает независимо: если одна сломалась, остальные всё равно выполнятся."""
import json, re, html, time, datetime, urllib.request, urllib.error
games = json.load(open("data/games.json", encoding="utf-8"))
today = datetime.date.today()

def jget(url, t=30): return json.load(urllib.request.urlopen(url, timeout=t))
def load(p, d):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d
def save(p, o): json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False)
def clean(s): return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()

def popular():
    rv = load("data/reviews.json", {})
    return sorted(games, key=lambda g: -rv.get(str(g["id"]), {}).get("total", 0))

def reviews():  # рейтинг отзывов Steam, обновление раз в 7 дней, до 150 игр за запуск
    rev, n = load("data/reviews.json", {}), 0
    for g in games:
        i = str(g["id"]); r = rev.get(i)
        if r and (today - datetime.date.fromisoformat(r["d"])).days < 7: continue
        if n >= 150: break
        n += 1
        try:
            d = jget(f"https://store.steampowered.com/appreviews/{i}?json=1&language=all&purchase_type=all&num_per_page=0")["query_summary"]
            t = d["total_positive"] + d["total_negative"]
            if t: rev[i] = {"pct": round(100 * d["total_positive"] / t), "total": t, "d": today.isoformat()}
        except Exception as e: print(i, "отзывы: ошибка", e)
        time.sleep(0.7)
    save("data/reviews.json", rev); print("отзывы:", len(rev))

def details():  # описания: до 100 игр за запуск (по 3 языка)
    L = {"ru": "russian", "uk": "ukrainian", "en": "english"}
    data = {l: load(f"data/details-{l}.json", {}) for l in L}
    todo = [g["id"] for g in popular() if any(str(g["id"]) not in data[l] for l in L)][:100]
    stop = False
    try:
        for i in todo:
            for l, name in L.items():
                if str(i) in data[l]: continue
                try:
                    r = jget(f"https://store.steampowered.com/api/appdetails?appids={i}&l={name}&cc=us&filters=basic,genres,release_date")[str(i)]
                    d = r.get("data") if r.get("success") else None
                    data[l][str(i)] = {} if not d else {"d": clean(d.get("short_description")), "dev": (d.get("developers") or [])[:2],
                        "rel": (d.get("release_date") or {}).get("date", ""), "g": [x["description"] for x in d.get("genres", [])][:4]}
                except urllib.error.HTTPError as e:
                    if e.code in (429, 403): stop = True; break   # Steam просит притормозить: продолжим завтра
                    data[l][str(i)] = {}
                except Exception as e: print(i, l, "описание: ошибка", e)
                time.sleep(1.6)
            if stop: break
    finally:
        for l in L: save(f"data/details-{l}.json", data[l])
    print("описания:", len(data["en"]), "игр, обработано сейчас:", len(todo))

def activity():  # число отзывов по месяцам (Steam не отдаёт продажи; отзывы растут вместе с числом покупателей)
    act, n = load("data/activity.json", {}), 0
    cur = today.strftime("%Y-%m")
    for g in popular():
        i = str(g["id"]); a = act.get(i)
        if a and (today - datetime.date.fromisoformat(a["d"])).days < 30: continue
        if n >= 150: break
        n += 1
        try:
            r = jget(f"https://store.steampowered.com/appreviewhistogram/{i}?l=english&review_score_preference=0")["results"]
            by = {}
            for x in r.get("rollups", []):
                k = datetime.datetime.fromtimestamp(x["date"], datetime.timezone.utc).strftime("%Y-%m")
                if k != cur: by[k] = by.get(k, 0) + x.get("recommendations_up", 0) + x.get("recommendations_down", 0)  # текущий месяц неполный
            act[i] = {"d": today.isoformat(), "m": sorted(by.items())[-36:]}
        except Exception as e: print(i, "активность: ошибка", e)
        time.sleep(1)
    save("data/activity.json", act); print("активность:", len(act))

for f in (reviews, details, activity):
    try: f()
    except Exception as e: print(f.__name__, "ОШИБКА:", e)

