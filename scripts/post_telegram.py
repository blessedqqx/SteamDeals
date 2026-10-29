"""Публикует в Telegram-канал выгодные скидки на хорошие игры: один пост на игру, цены по всем регионам.
Нужны секреты TG_TOKEN и TG_CHANNEL. Уже опубликованное хранится в data/posted.json, поэтому повторов нет.
Один запуск = один пост. Запускается отдельным расписанием (.github/workflows/post.yml) несколько раз в день,
поэтому игры выходят в канал в течение дня, а не пачкой. Настройки (можно менять): MIN_DISC, MIN_PCT, MIN_REV, HIT_REV, HIT_PCT, MAX_POSTS, MAX_PER_DAY.
Раздачи (скидка 100%) идут вне очереди и без порога отзывов; очень популярные игры (HIT_REV отзывов) проходят и со смешанной оценкой.
Особые посты (занимают место обычного поста в своём запуске):
  • «Топ-5 скидок недели»: по воскресеньям, в запуске не раньше 16:00 UTC (WEEKLY_DAY, WEEKLY_HOUR);
  • анонсы распродаж из data/announce.json: за N дней до старта, но только если у записи стоит "approved": true."""
import json, math, os, sys, html, datetime, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_pages import site_url, money, load

tok, chan = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHANNEL")
if not (tok and chan): print("Telegram не настроен (нет TG_TOKEN / TG_CHANNEL), пропускаю"); raise SystemExit
if os.environ.get("GITHUB_WORKFLOW") == "update-prices":   # ежедневное обновление данных не публикует, чтобы не было «пачки» постов
    print("посты выходят по расписанию из запуска post-telegram, здесь пропускаю"); raise SystemExit
MIN_DISC = 50     # минимальная скидка хотя бы в одном регионе, %
MIN_PCT = 80      # минимум положительных отзывов, %
MIN_REV = 5000    # минимум отзывов (чтобы игра была известной)
HIT_REV = 50000   # «народные» игры (Battlefield и т.п.): от стольких отзывов оценка может быть ниже MIN_PCT
HIT_PCT = 40      # но не ниже этого процента положительных
MAX_POSTS = 1     # постов за один запуск
MAX_PER_DAY = 5   # потолок постов за сутки
COOLDOWN, JUMP = 14, 15   # не повторять игру 14 дней, если скидка не выросла на 15 п.п.
REG = [("ua", "🇺🇦", "Украина"), ("us", "🇺🇸", "США"), ("kz", "🇰🇿", "Казахстан"), ("ru", "🇷🇺", "Россия")]
TAGS = {"story": "#сюжетные", "coop": "#кооператив", "shooter": "#шутеры", "openworld": "#открытый_мир", "horror": "#хоррор", "indie": "#инди", "racing": "#гонки", "strategy": "#стратегии"}
site = site_url()
games, rev = load("data/games.json", []), load("data/reviews.json", {})
det = load("data/details-ru.json", {})   # краткие описания игр
pr = {cc: load(f"data/{cc}/prices.json", {}) for cc, _, _ in REG}
posted = load("data/posted.json", {})
# время запуска; переменная SD_NOW нужна только для проверок
NOW = datetime.datetime.fromisoformat(os.environ["SD_NOW"]) if os.environ.get("SD_NOW") else datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
today = NOW.date()
WEEKLY_DAY, WEEKLY_HOUR = 6, 16     # воскресенье (0 = понедельник), не раньше 16:00 UTC (вечер в Украине, Казахстане и России)
kf = lambda n: f"{round(n / 1000)} тыс." if n >= 1000 else str(n)

def caption(g, per, best, r, gift=False):
    def build(desc):
        if gift: L = [f"🎁 <b>Раздача: {html.escape(g['name'])}</b>", "Сейчас можно забрать <b>бесплатно</b> (−100%). Успейте добавить в библиотеку, пока идёт акция.", ""]
        else: L = [f"🔥 <b>{html.escape(g['name'])}</b>", f"Скидка до <b>−{best}%</b>", ""]
        if desc: L += [f"<i>{html.escape(desc)}</i>", ""]
        for cc, flag, name in REG:
            it = per.get(cc)
            if not it: continue
            cur = pr[cc].get("currency") or "USD"
            if it.get("free"): txt = "бесплатно"
            elif it["discount"] > 0: txt = f"<b>{money(it['final'], cur)}</b> (−{it['discount']}%, было {money(it['initial'], cur)})"
            else: txt = money(it["final"], cur)
            L.append(f"{flag} {name}: {txt}")
        L += [""] + ([f"⭐ {r['pct']}% положительных отзывов ({kf(r['total'])})"] if r else [])
        if not gift and any(it.get("low") for it in per.values()): L.append("📉 Исторический минимум цены")
        L += ["", " ".join((["#раздача", "#бесплатно", "#steam"] if gift else ["#скидки", "#steam"]) + [TAGS[t] for t in g.get("tags", []) if t in TAGS])]
        return "\n".join(L)
    d = ((det.get(str(g["id"])) or {}).get("d") or "").strip()
    if len(d) > 230: d = d[:230].rsplit(" ", 1)[0].rstrip(",.;:—- ") + "…"
    text = build(d)
    while len(text) > 1000 and d:          # подпись в Telegram не длиннее 1024 знаков
        d = d[:max(0, len(d) - 40)].rsplit(" ", 1)[0] if len(d) > 60 else ""
        text = build(d)
    return text

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

def qualify(g):
    """Подходит ли игра для публикации: (id, цены по регионам, макс. скидка, отзывы, раздача) или None."""
    i = str(g["id"]); r = rev.get(i)
    per = {cc: (pr[cc].get("items") or {}).get(i) for cc, _, _ in REG}
    per = {cc: it for cc, it in per.items() if it}
    best = max([it["discount"] for it in per.values() if not it.get("free")], default=0)
    gift = any(it.get("discount") == 100 and not it.get("free") for it in per.values())
    if not gift:
        if not r or best < MIN_DISC: return None
        if not ((r["pct"] >= MIN_PCT and r["total"] >= MIN_REV) or (r["total"] >= HIT_REV and r["pct"] >= HIT_PCT)): return None
    return i, per, best, r, gift

def ru_days(n):
    return f"{n} " + ("день" if n % 10 == 1 and n % 100 != 11 else "дня" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else "дней")

def special_send(text, photo=None):
    kb = {"inline_keyboard": [[{"text": "Все скидки", "url": site}]]}
    if photo:
        try: return api("sendPhoto", {"chat_id": chan, "photo": photo, "caption": text, "parse_mode": "HTML", "reply_markup": kb})
        except Exception as e: print("фото не отправилось, шлю текстом:", e)
    return api("sendMessage", {"chat_id": chan, "text": text, "parse_mode": "HTML", "reply_markup": kb, "disable_web_page_preview": True})

def mark(key):
    posted[key] = {"d": today.isoformat()}
    json.dump(posted, open("data/posted.json", "w", encoding="utf-8"), ensure_ascii=False)

def announce_due():
    """Анонс распродажи: за days_before дней до старта (и позже, но до старта), только если approved = true."""
    for a in load("data/announce.json", []):
        key = "_ann:" + str(a.get("id") or a.get("date"))
        if a.get("approved") is not True or key in posted: continue
        try: left = (datetime.date.fromisoformat(a["date"]) - today).days
        except Exception: continue
        if 0 < left <= int(a.get("days_before", 5)): return key, a, left
    return None

def weekly_text():
    rows = []
    for g in games:
        q = qualify(g)
        if not q: continue
        i, per, best, r, gift = q
        low = any(it.get("low") for it in per.values())
        rows.append(((1000 if gift else 0) + best * math.log10((r["total"] if r else 0) + 10) * (1.15 if low else 1), i, g, per, best, gift))
    rows.sort(key=lambda x: -x[0]); rows = rows[:5]
    if len(rows) < 3: return None, None
    title = "🏆 <b>Топ-5 скидок недели</b>" if len(rows) == 5 else "🏆 <b>Лучшие скидки недели</b>"
    for nreg in (4, 2, 1):
        L = [title, ""]
        for k, (_, i, g, per, best, gift) in enumerate(rows, 1):
            L.append(f"{k}. <b>{html.escape(g['name'])}</b> — " + ("🎁 бесплатно" if gift else f"−{best}%"))
            pz = [f"{flag} {money(per[cc]['final'], pr[cc].get('currency') or 'USD')}" for cc, flag, _ in REG[:nreg] if per.get(cc) and not per[cc].get("free")]
            if pz: L.append("   " + " · ".join(pz))
        L += ["", "Все скидки, фильтры по жанрам и история цен на сайте 👇", "", "#топнедели #скидки #steam"]
        text = "\n".join(L)
        if len(text) <= 1000: break
    return text, f"https://cdn.akamai.steamstatic.com/steam/apps/{rows[0][1]}/header.jpg"

# особые посты занимают место обычного поста в этом запуске
try:
    due = announce_due()
    if due:
        key, a, left = due
        special_send(a["text"].replace("{days}", ru_days(left)).replace("{site}", site), a.get("photo") or None)
        mark(key); print("опубликован анонс:", key, "(осталось дней:", left, ")"); raise SystemExit
    wk = posted.get("_weekly", {}).get("d")
    if NOW.weekday() == WEEKLY_DAY and NOW.hour >= WEEKLY_HOUR and not (wk and abs((today - datetime.date.fromisoformat(wk)).days) < 6):
        text, photo = weekly_text()
        if text:
            special_send(text, photo); mark("_weekly"); print("опубликован «Топ недели»"); raise SystemExit
except SystemExit: raise
except Exception as e: print("особый пост не отправлен:", e)

cands = []
for g in games:
    q = qualify(g)
    if not q: continue
    i, per, best, r, gift = q
    last = posted.get(i)
    if last and (today - datetime.date.fromisoformat(last["d"])).days < COOLDOWN and best < last["disc"] + JUMP: continue
    cands.append((gift, r["total"] if r else 0, i, g, per, best, r))
cands.sort(key=lambda c: (not c[0], -c[1]))     # раздачи первыми, дальше по популярности
sent = 0
done_today = sum(1 for v in posted.values() if v.get("d") == today.isoformat())
budget = max(0, min(MAX_POSTS, MAX_PER_DAY - done_today))
if cands and cands[0][0]: budget = MAX_POSTS      # раздача важнее суточного потолка
for gift, _, i, g, per, best, r in cands[:budget]:
    try:
        send(i, caption(g, per, best, r, gift))
        posted[i] = {"d": today.isoformat(), "disc": best}; sent += 1
        json.dump(posted, open("data/posted.json", "w", encoding="utf-8"), ensure_ascii=False)
    except Exception as e: print("не отправлено:", g["name"], e)
print(f"кандидатов: {len(cands)}, опубликовано: {sent} (сегодня уже: {done_today})")
