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
print("ВСЕ ПРОВЕРКИ РАЗДАЧ ПРОЙДЕНЫ" if not bad else f"ПРОВАЛЕНО: {bad}")
raise SystemExit(1 if bad else 0)
