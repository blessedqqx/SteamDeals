"""Раз в день: цены Steam по регионам (UA, US, KZ, RU) и история."""
import json, os, time, datetime, urllib.request
REGIONS = ["ua", "us", "kz", "ru"]
BATCH = 50
games = json.load(open("data/games.json", encoding="utf-8"))
today = datetime.date.today().isoformat()

def run(cc):
    os.makedirs(f"data/{cc}", exist_ok=True)
    try: hist = json.load(open(f"data/{cc}/history.json", encoding="utf-8"))
    except Exception: hist = {}
    items, cur = {}, None
    for i in range(0, len(games), BATCH):
        ids = ",".join(str(g["id"]) for g in games[i:i+BATCH])
        url = f"https://store.steampowered.com/api/appdetails?appids={ids}&cc={cc}&filters=price_overview"
        data = json.load(urllib.request.urlopen(url, timeout=30))
        for appid, r in data.items():
            d = r.get("data")
            po = d.get("price_overview") if isinstance(d, dict) else None
            if not po: continue  # игры нет в регионе или нет цены
            cur = po.get("currency", cur)
            initial, final = po["initial"] / 100, po["final"] / 100
            h = hist.setdefault(appid, [])
            prev_min = min([p for _, p in h], default=None)
            low = prev_min is not None and final <= prev_min and final < initial
            if not h or h[-1][1] != final: h.append([today, final])
            items[appid] = {"initial": initial, "final": final, "discount": po["discount_percent"], "low": low}
        time.sleep(2)
    json.dump({"demo": False, "updated": today, "currency": cur, "items": items}, open(f"data/{cc}/prices.json", "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(hist, open(f"data/{cc}/history.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(cc, "ok:", len(items), "игр", cur)

for cc in REGIONS:
    try: run(cc)
    except Exception as e: print(cc, "ОШИБКА:", e)  # один регион не должен ломать остальные
