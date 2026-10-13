"""Публикует в Telegram-канал лучшие скидки дня (Украина). Нужны TG_TOKEN и TG_CHANNEL."""
import json, os, html, urllib.request, urllib.parse
tok, chan, site = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHANNEL"), os.environ.get("SITE_URL", "")
if not (tok and chan): print("Telegram не настроен, пропускаю"); raise SystemExit
p = json.load(open("data/ua/prices.json", encoding="utf-8"))
games = {str(g["id"]): g for g in json.load(open("data/games.json", encoding="utf-8"))}
try: rev = json.load(open("data/reviews.json", encoding="utf-8"))
except Exception: rev = {}
rows = [(i, x) for i, x in p["items"].items() if x["discount"] >= 50 and i in games and rev.get(i, {}).get("pct", 80) >= 75]
rows.sort(key=lambda r: (-int(r[1]["low"]), -r[1]["discount"]))
rows = rows[:10]
if not rows: print("нечего публиковать"); raise SystemExit
lines = ["Лучшие скидки в Steam (Украина):", ""]
for i, x in rows:
    lines.append(f'−{x["discount"]}% <b>{html.escape(games[i]["name"])}</b>: {x["final"]:.0f} ₴ (было {x["initial"]:.0f})'
                 + (" · исторический минимум" if x["low"] else "") + f'\nhttps://store.steampowered.com/app/{i}/?cc=ua')
if site: lines += ["", f"Все скидки: {site}"]
data = urllib.parse.urlencode({"chat_id": chan, "text": "\n".join(lines), "parse_mode": "HTML", "disable_web_page_preview": "true"}).encode()
urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data, timeout=30)
print("опубликовано:", len(rows))
