"""Проверки результата сбора данных (запускается после harness2.py, до prepare_site.py)."""
import json, os, re, xml.dom.minidom
bad = 0
def chk(n, c, x=""):
    global bad; print(("OK   " if c else "FAIL ") + n + ("" if c else "  " + str(x))); bad += (not c)
g = json.load(open("data/games.json", encoding="utf-8")); byid = {x["id"]: x for x in g}
chk("Cyberpunk, RDR2, GTA V возвращены в каталог", {1091500, 1174180, 271590} <= set(byid))
chk("Battlefield 2042 и Battlefield 1 в каталоге", {1517290, 1238840} <= set(byid))
chk("Hentai-игра исключена", 900001 not in byid)
chk("очень популярная игра со спорными отзывами (46%, 130 тыс.) в каталоге", 777020 in byid)
chk("малая игра со спорными отзывами (46%, 6,5 тыс.) не попала", 777021 not in byid)
chk("хорошая игра с 74% отзывов попала", 777022 in byid)
chk("игра из топа популярности со смешанной оценкой (33%, 60 тыс.) в каталоге", 777030 in byid)
chk("ей определён жанр по тегам SteamSpy (хоррор из заглушки)", byid.get(777030, {}).get("tags") == ["horror"], byid.get(777030))
chk("игра из топа, но с малым числом отзывов (1,5 тыс.) не попала", 777031 not in byid)
chk("раздача из списка распродаж Steam (скидка 100%) попала в каталог без жанра", 777099 in byid)
chk("бесплатные помечены f (CS2, Free Hit из SteamSpy)", byid[730].get("f") == 1 and byid.get(777011, {}).get("f") == 1)
for cc in ("ua", "us", "kz", "ru"):
    p = json.load(open(f"data/{cc}/prices.json", encoding="utf-8")); it = p["items"]
    chk(f"{cc}: Cyberpunk найден повторным запросом, бесплатные на месте, Witcher без цены", "1091500" in it and "730" in it and it["730"].get("free") and "292030" not in it)
sh = json.load(open("data/shots.json")); chk("скриншоты: 6 штук без ?t=", len(sh["1091500"]) == 6 and all("?" not in u for u in sh["1091500"]))
chk("описания на 3 языках", all(os.path.exists(f"data/details-{l}.json") for l in ("ru", "uk", "en")))
pg = open("data/g/1091500.html", encoding="utf-8").read()
chk("страница игры: canonical, иконка, JSON-LD, цены во всех валютах", 'rel="canonical"' in pg and "favicon.png" in pg and "ld+json" in pg and all(c in pg for c in "₴$₸₽"))
d = xml.dom.minidom.parse("data/sitemap.xml"); chk("sitemap.xml валиден", len(d.getElementsByTagName("url")) >= 50)
chk("в sitemap есть главная страница", "<loc>https://owner.github.io/repo/</loc>" in open("data/sitemap.xml", encoding="utf-8").read())
chk("без токена счётчика его нет на страницах игр", "cloudflareinsights" not in pg)
log = [json.loads(l) for l in open("tg.log")] if os.path.exists("tg.log") else []
chk("Telegram: ровно один пост за запуск", len(log) == 1, len(log))
if log:
    c = log[0]["caption"]; print("\n--- пример поста ---\n" + c + "\n---\n")
    chk("пост: описание игры курсивом, обрезано по слову, с многоточием", "<i>Hi game." in c and "…</i>" in c)
    chk("пост: подпись не длиннее 1024", len(c) <= 1024, len(c))
    chk("пост: 4 региона, скидка, отзывы, хештеги", all(x in c for x in ("🇺🇦 Украина", "🇺🇸 США", "🇰🇿 Казахстан", "🇷🇺 Россия", "−50%", "положительных", "#скидки")))
    chk("пост: фото обложки и две кнопки", log[0]["m"] == "sendPhoto" and len(log[0]["reply_markup"]["inline_keyboard"]) == 2)
print("ВСЕ ПРОВЕРКИ ДАННЫХ ПРОЙДЕНЫ" if not bad else f"ПРОВАЛЕНО: {bad}")
raise SystemExit(1 if bad else 0)
