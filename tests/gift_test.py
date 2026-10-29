"""Раздачи (скидка 100%) и «народные» игры со смешанной оценкой. Запускается после основного сбора данных."""
import json, os, re, subprocess, sys
bad = 0
def chk(n, c, x=""):
    global bad; print(("OK   " if c else "FAIL ") + n + ("" if c else "  " + str(x))); bad += (not c)
def tg(): return [json.loads(l) for l in open("tg.log")]
def run(*a, **kw):
    env = dict(os.environ, **kw)
    return subprocess.run([sys.executable, "harness2.py", *a], env=env, capture_output=True, text=True).stdout

# 1) Open Hit (777002) становится раздачей во всех регионах
run("collect", GIFT="777002")
h = json.load(open("data/ua/history.json", encoding="utf-8")).get("777002", [])
chk("раздача не попала в историю цен (иначе «минимум» стал бы нулевым)", all(p[1] > 0 for p in h), h)
it = json.load(open("data/ua/prices.json", encoding="utf-8"))["items"]["777002"]
chk("цена раздачи: 0 и скидка 100%", it["final"] == 0 and it["discount"] == 100 and not it.get("free"), it)
n0 = len(tg()); out = run("post_telegram")
log = tg(); chk("раздача опубликована вне очереди, один пост", len(log) == n0 + 1, (n0, len(log)))
c = log[-1].get("caption") or log[-1].get("text", "")
print("\n--- пример поста-раздачи ---\n" + c + "\n---\n")
chk("пост-раздача: заголовок, название, «бесплатно», хештеги", "Раздача: Open Hit" in c and "бесплатно" in c and "#раздача" in c, c[:120])
chk("пост-раздача: нет строки «исторический минимум»", "минимум" not in c)
chk("пост-раздача: подпись не длиннее 1024", len(c) <= 1024, len(c))

# 2) следующий пост: раздача не повторяется, на очереди «народная» игра с оценкой 46% (130 тыс. отзывов)
n1 = len(tg()); run("post_telegram"); log = tg()
chk("ещё один пост ушёл", len(log) == n1 + 1)
c2 = log[-1].get("caption") or log[-1].get("text", "")
chk("раздача второй раз не публикуется", "Раздача" not in c2, c2[:80])
chk("популярная игра со смешанной оценкой (46%) попала в канал", "Divisive Giant" in c2, c2[:80])

# 3) счётчик посетителей на страницах игр появляется, когда токен указан в config.js
cfg = open("config.js", encoding="utf-8").read()
open("config.js", "w", encoding="utf-8").write(re.sub(r'CF_ANALYTICS: ""', 'CF_ANALYTICS: "abcdef1234567890"', cfg))
subprocess.run([sys.executable, "-c", "import sys;sys.path.insert(0,'scripts');import build_pages;build_pages.main()"], capture_output=True)
pg = open("data/g/1091500.html", encoding="utf-8").read()
chk("счётчик Cloudflare на странице игры, когда токен указан", "cloudflareinsights" in pg and "abcdef1234567890" in pg)
open("config.js", "w", encoding="utf-8").write(cfg)

# 4) воскресный «Топ недели»: не раньше 16:00 UTC в воскресенье и один раз за неделю
import datetime
d0 = datetime.date.today(); sun = d0 + datetime.timedelta(days=(6 - d0.weekday()) % 7 or 7)
at = lambda day, hr: f"{day.isoformat()}T{hr:02d}:20:00"
def cap(l): return l.get("caption") or l.get("text") or ""
def last_new(n): log = tg(); return [cap(l) for l in log[n:]]
n = len(tg()); run("post_telegram", SD_NOW=at(sun - datetime.timedelta(days=1), 17))
chk("в субботу «Топ недели» не публикуется", not any("недели" in c for c in last_new(n)))
n = len(tg()); run("post_telegram", SD_NOW=at(sun, 10))
chk("в воскресенье до 16:00 UTC «Топ недели» не публикуется", not any("недели" in c for c in last_new(n)))
n = len(tg()); run("post_telegram", SD_NOW=at(sun, 17)); new = last_new(n); wlog = tg()[-1]
chk("воскресенье вечером: ушёл ровно один пост", len(new) == 1, len(new))
w = new[0] if new else ""
print("\n--- пример «Топ недели» ---\n" + w + "\n---\n")
chk("«Топ недели»: заголовок, нумерация 1–3, флаги регионов, хештеги", ("Топ-5 скидок недели" in w or "Лучшие скидки недели" in w) and all(f"{k}. <b>" in w for k in (1, 2, 3)) and "🇺🇦" in w and "#топнедели" in w, w[:120])
chk("«Топ недели»: подпись не длиннее 1024, фото первой игры и кнопка «Все скидки»", len(w) <= 1024 and wlog["m"] == "sendPhoto" and wlog["reply_markup"]["inline_keyboard"][0][0]["text"] == "Все скидки", (len(w), wlog["m"]))
n = len(tg()); run("post_telegram", SD_NOW=at(sun, 19))
chk("в тот же день повторно «Топ недели» не публикуется", not any("недели" in c for c in last_new(n)))

# 5) анонсы распродаж: только с подтверждением, за N дней до старта, один раз, вместо обычного поста
td = datetime.date.today(); iso = lambda k: (td + datetime.timedelta(days=k)).isoformat()
ann = [{"id": "t1", "date": iso(5), "days_before": 5, "approved": True, "text": "TEST1 через {days} {site}"},
       {"id": "t2", "date": iso(3), "days_before": 5, "approved": False, "text": "TEST2 через {days}"},
       {"id": "t3", "date": iso(9), "days_before": 5, "approved": True, "text": "TEST3 рано"}]
save = lambda: json.dump(ann, open("data/announce.json", "w", encoding="utf-8"), ensure_ascii=False)
save(); n = len(tg()); run("post_telegram"); new = last_new(n)
chk("анонс t1: «через 5 дней» и ссылка на сайт", any("TEST1 через 5 дней" in c and "https://owner.github.io/repo" in c for c in new), new)
chk("анонс t2 без подтверждения не опубликован", not any("TEST2" in c for c in new))
chk("анонс t3 раньше срока не опубликован", not any("TEST3" in c for c in new))
chk("анонс занял место обычного поста: ровно одно сообщение", len(new) == 1, len(new))
n = len(tg()); run("post_telegram")
chk("анонс t1 повторно не публикуется", not any("TEST1" in c for c in last_new(n)))
ann[1]["approved"] = True; save(); n = len(tg()); run("post_telegram")
chk("после подтверждения t2 ушёл («через 3 дня»)", any("TEST2 через 3 дня" in c for c in last_new(n)), last_new(n))
print("ВСЕ ПРОВЕРКИ РАЗДАЧ ПРОЙДЕНЫ" if not bad else f"ПРОВАЛЕНО: {bad}")
raise SystemExit(1 if bad else 0)
