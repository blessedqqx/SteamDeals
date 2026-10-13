"""Рейтинг отзывов Steam (обновляется раз в 7 дней, до 60 игр за запуск)."""
import json, time, datetime, urllib.request
games = json.load(open("data/games.json", encoding="utf-8"))
try: rev = json.load(open("data/reviews.json", encoding="utf-8"))
except Exception: rev = {}
today, n = datetime.date.today(), 0
for g in games:
    i = str(g["id"]); r = rev.get(i)
    if r and (today - datetime.date.fromisoformat(r["d"])).days < 7: continue
    if n >= 60: break
    n += 1
    try:
        d = json.load(urllib.request.urlopen(f"https://store.steampowered.com/appreviews/{i}?json=1&language=all&purchase_type=all&num_per_page=0", timeout=30))["query_summary"]
        t = d["total_positive"] + d["total_negative"]
        if t: rev[i] = {"pct": round(100 * d["total_positive"] / t), "total": t, "d": today.isoformat()}
    except Exception as e: print(i, "ошибка", e)
    time.sleep(0.7)
json.dump(rev, open("data/reviews.json", "w", encoding="utf-8"))
print("отзывы:", len(rev))
