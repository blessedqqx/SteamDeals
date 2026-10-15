"""Публикует в Telegram-канал выгодные скидки на хорошие игры: один пост на игру, цены по всем регионам.
Нужны секреты TG_TOKEN и TG_CHANNEL. Уже опубликованное хранится в data/posted.json, поэтому повторов нет.
Настройки (можно менять): MIN_DISC, MIN_PCT, MIN_REV, MAX_POSTS."""
import json, os, sys, html, datetime, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_pages import site_url, money, load

tok, chan = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHANNEL")
if not (tok and chan): print("Telegram не настроен (нет TG_TOKEN / TG_CHANNEL), пропускаю"); raise SystemExit
MIN_DISC = 50     # минимальная скидка хотя бы в одном регионе, %
MIN_PCT = 80      # минимум положительных отзывов, %
MIN_REV = 5000    # минимум отзывов (чтобы игра была известной)
MAX_POSTS = 5     # не больше постов за один запуск
COOLDOWN, JUMP = 14, 15   # не повторять игру 14 дней, если скидка не выросла на 15 п.п.
REG = [("ua", "🇺🇦", "Украина"), ("us", "🇺🇸", "США"), ("kz", "🇰🇿", "Казахстан"), ("ru", "🇷🇺", "Россия")]
TAGS = {"story": "#сюжетные", "coop": "#кооператив", "shooter": "#шутеры", "openworld": "#открытый_мир", "horror": "#хоррор", "indie": "#инди", "racing": "#гонки", "strategy": "#стратегии"}
site = site_url()
games, rev = load("data/games.json", []), load("data/reviews.json", {})
pr = {cc: load(f"data/{cc}/prices.json", {}) for cc, _, _ in REG}
posted = load("data/posted.json", {})
today = datetime.date.today()
kf = lambda n: f"{round(n / 1000)} тыс." if n >= 1000 else str(n)

def caption(g, per, best, r):
    L = [f"🔥 <b>{html.escape(g['name'])}</b>", f"Скидка до <b>−{best}%</b>", ""]
    for cc, flag, name in REG:
        it = per.get(cc)
        if not it: continue
        cur = pr[cc].get("currency") or "USD"
        if it.get("free"): txt = "бесплатно"
        elif it["discount"] > 0: txt = f"<b>{money(it['final'], cur)}</b> (−{it['discount']}%, было {money(it['initial'], cur)})"
        else: txt = money(it["final"], cur)
        L.append(f"{flag} {name}: {txt}")
    L += ["", f"⭐ {r['pct']}% положительных отзывов ({kf(r['total'])})"]
    if any(it.get("low") for it in per.values()): L.append("📉 Исторический минимум цены")
    L += ["", " ".join(["#скидки", "#steam"] + [TAGS[t] for t in g.get("tags", []) if t in TAGS])]
    return "\n".join(L)

def api(method, payload):
    req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/{method}", json.dumps(payload).encode(), {"Content-Type": "application/json"})
    try: return json.load(urllib.request.urlopen(req, timeout=30))
    except urllib.error.HTTPError as e: raise RuntimeError(f"{method}: {e.code} {e.read().decode('utf-8', 'ignore')[:200]}")

def send(i, text):
    kb = {"inline_keyboard": [[{"text": "Открыть в Steam", "url": f"https://store.steampowered.com/app/{i}/"}], [{"text": "Все скидки", "url": site}]]}
    try: return api("sendPhoto", {"chat_id": chan, "photo": f"https://cdn.akamai.steamstatic.com/steam/apps/{i}/header.jpg", "caption": text, "parse_mode": "HTML", "reply_markup": kb})
    except Exception as e:
        print("фото не отправилось, шлю текстом:", e)
        return api("sendMessage", {"chat_id": chan, "text": text, "parse_mode": "HTML", "reply_markup": kb})

cands = []
for g in games:
    i = str(g["id"]); r = rev.get(i)
    if not r or r["pct"] < MIN_PCT or r["total"] < MIN_REV: continue
    per = {cc: (pr[cc].get("items") or {}).get(i) for cc, _, _ in REG}
    per = {cc: it for cc, it in per.items() if it}
    best = max([it["discount"] for it in per.values() if not it.get("free")], default=0)
    if best < MIN_DISC: continue
    last = posted.get(i)
    if last and (today - datetime.date.fromisoformat(last["d"])).days < COOLDOWN and best < last["disc"] + JUMP: continue
    cands.append((r["total"], i, g, per, best, r))
cands.sort(key=lambda c: -c[0])
sent = 0
for _, i, g, per, best, r in cands[:MAX_POSTS]:
    try:
        send(i, caption(g, per, best, r))
        posted[i] = {"d": today.isoformat(), "disc": best}; sent += 1
        json.dump(posted, open("data/posted.json", "w", encoding="utf-8"), ensure_ascii=False)
    except Exception as e: print("не отправлено:", g["name"], e)
print(f"кандидатов: {len(cands)}, опубликовано: {sent}")
