"""Раз в день: цены Steam по регионам (UA, US, KZ, RU), история цен, бесплатные игры.
Игры, которые не пришли в пакетном ответе, запрашиваются повторно по одной (сначала самые популярные)."""
import json, os, time, datetime, urllib.request
REGIONS = {"ua": "UAH", "us": "USD", "kz": "KZT", "ru": "RUB"}   # регион: валюта по умолчанию
BATCH, RETRY_LIMIT = 50, 60
games = json.load(open("data/games.json", encoding="utf-8"))
today = datetime.date.today().isoformat()
try: rv = json.load(open("data/reviews.json", encoding="utf-8"))
except Exception: rv = {}
name = {str(g["id"]): g["name"] for g in games}
free_flag = {str(g["id"]): bool(g.get("f")) for g in games}

def fetch(cc, ids):
    url = f"https://store.steampowered.com/api/appdetails?appids={','.join(str(x) for x in ids)}&cc={cc}&filters=price_overview"
    for attempt in range(3):
        try: return json.load(urllib.request.urlopen(url, timeout=60))
        except Exception as e: print(cc, "повтор", attempt + 1, e); time.sleep(10)
    return None

def parse(appid, r):
    """Платная игра: есть price_overview. Бесплатная: ответ успешный, цены нет, игра помечена как F2P."""
    if not isinstance(r, dict) or not r.get("success"): return None
    d = r.get("data"); po = d.get("price_overview") if isinstance(d, dict) else None
    if po: return {"initial": po["initial"] / 100, "final": po["final"] / 100, "discount": po["discount_percent"]}, po.get("currency")
    if free_flag.get(appid): return {"initial": 0, "final": 0, "discount": 0, "free": True}, None
    return None

def run(cc):
    os.makedirs(f"data/{cc}", exist_ok=True)
    try: hist = json.load(open(f"data/{cc}/history.json", encoding="utf-8"))
    except Exception: hist = {}
    items, missing, cur = {}, [], [None]

    def take(appid, r):
        res = parse(appid, r)
        if not res: return False
        it, c = res; cur[0] = c or cur[0]
        if it.get("free"): it["low"] = False
        else:
            h = hist.setdefault(appid, []); prev_min = min([p for _, p in h], default=None)
            it["low"] = prev_min is not None and it["final"] <= prev_min and it["final"] < it["initial"]
            if it["final"] > 0 and (not h or h[-1][1] != it["final"]): h.append([today, it["final"]])   # раздачи (цена 0) в историю не пишем, иначе «минимум» навсегда станет нулевым
        items[appid] = it; return True

    for i in range(0, len(games), BATCH):
        ids = [str(g["id"]) for g in games[i:i + BATCH]]
        data = fetch(cc, ids)
        if data is None: missing += ids
        else: missing += [x for x in ids if not take(x, data.get(x))]
        time.sleep(2)
    missing.sort(key=lambda x: -rv.get(x, {}).get("total", 0))
    for appid in missing[:RETRY_LIMIT]:      # повторный запрос по одной игре
        data = fetch(cc, [appid])
        if data and take(appid, data.get(appid)): missing.remove(appid)
        time.sleep(1.5)
    if not items: raise RuntimeError("Steam не вернул цен, старые данные оставлены")
    currency = cur[0] or REGIONS[cc]
    json.dump({"demo": False, "updated": today, "currency": currency, "items": items}, open(f"data/{cc}/prices.json", "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(hist, open(f"data/{cc}/history.json", "w", encoding="utf-8"), ensure_ascii=False)
    nf = sum(1 for v in items.values() if v.get("free"))
    print(cc, "ok:", len(items), "игр,", nf, "бесплатных, без цены в этом регионе:", len(missing), currency)
    if missing: print("  нет цены (самые популярные):", "; ".join(name.get(x, x) for x in missing[:12]))

for cc in REGIONS:
    try: run(cc)
    except Exception as e: print(cc, "ОШИБКА:", e)  # один регион не должен ломать остальные
try:       # даты окончания скидок (для окна игры на сайте); если Steam не ответит, цены всё равно сохранены
    import ends; ends.run(list(REGIONS))
except Exception as e: print("даты окончания скидок: ошибка", e)
