"""Статические страницы игр (для поисковиков) и sitemap.xml.
Результат: data/g/<id>.html и data/sitemap.xml. Запускается из reviews.py."""
import json, os, html, datetime
REG = [("ua", "Украина", "UAH"), ("us", "США", "USD"), ("kz", "Казахстан", "KZT"), ("ru", "Россия", "RUB")]
SYM = {"UAH": "₴", "USD": "$", "KZT": "₸", "RUB": "₽"}
FALLBACK_SITE = "https://blessedqqx.github.io/SteamDeals/"

def load(p, d):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d

def site_url():
    s = os.environ.get("SITE_URL")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not s and "/" in repo:
        o, r = repo.split("/", 1); s = f"https://{o.lower()}.github.io/{r}/"
    s = s or FALLBACK_SITE
    return s if s.endswith("/") else s + "/"

def money(v, cur):
    if cur == "USD": return f"${v:,.2f}"
    return f"{v:,.0f}".replace(",", "\u00a0") + "\u00a0" + SYM.get(cur, cur)

CSS = ("body{margin:0;background:#11161d;color:#e8edf3;font-family:Arial,sans-serif;line-height:1.5}main{max-width:760px;margin:0 auto;padding:24px}"
       "a{color:#7be0a4}img{max-width:100%;height:auto;border-radius:12px}table{width:100%;border-collapse:collapse;margin:16px 0}"
       "td,th{padding:10px;border-bottom:1px solid #263040;text-align:left}.btn{display:inline-block;background:#7be0a4;color:#0b1a12;padding:12px 20px;border-radius:10px;font-weight:700;text-decoration:none}")

def main():
    games, rev = load("data/games.json", []), load("data/reviews.json", {})
    det, pr = load("data/details-ru.json", {}), {cc: load(f"data/{cc}/prices.json", {}) for cc, _, _ in REG}
    site, today = site_url(), datetime.date.today().isoformat()
    os.makedirs("data/g", exist_ok=True)
    urls = []
    for g in games:
        i = str(g["id"]); name = g["name"]; rows, offers, free = [], [], False
        for cc, rname, cur0 in REG:
            it = (pr[cc].get("items") or {}).get(i)
            if not it: continue
            cur = pr[cc].get("currency") or cur0
            if it.get("free"):
                free = True; rows.append(f"<tr><td>{rname}</td><td>Бесплатно</td><td>—</td></tr>")
            else:
                disc = f"−{it['discount']}%" if it["discount"] else "нет"
                rows.append(f"<tr><td>{rname}</td><td>{money(it['final'], cur)}</td><td>{disc}</td></tr>")
                offers.append({"@type": "Offer", "price": f"{it['final']:.2f}", "priceCurrency": cur, "availability": "https://schema.org/InStock", "url": f"https://store.steampowered.com/app/{i}/"})
        if not rows: continue
        desc = (det.get(i) or {}).get("d", "")
        r = rev.get(i)
        meta = f"{name}: цена в Steam в Украине, США, Казахстане и России. " + desc
        ld = {"@context": "https://schema.org", "@type": "Product", "name": name, "image": f"https://cdn.akamai.steamstatic.com/steam/apps/{i}/header.jpg", "description": desc or name}
        if offers: ld["offers"] = offers
        if r: ld["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": round(5 * r["pct"] / 100, 1), "bestRating": 5, "ratingCount": r["total"]}
        page = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(name)}: цена и скидки в Steam (Украина, США, Казахстан, Россия)</title>
<meta name="description" content="{html.escape(meta[:300], quote=True)}">
<link rel="canonical" href="{site}data/g/{i}.html">
<link rel="icon" type="image/png" href="{site}favicon.png">
<meta property="og:type" content="website"><meta property="og:title" content="{html.escape(name, quote=True)}: цена и скидки в Steam">
<meta property="og:image" content="https://cdn.akamai.steamstatic.com/steam/apps/{i}/header.jpg"><meta property="og:url" content="{site}data/g/{i}.html">
<style>{CSS}</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script></head><body><main>
<p><a href="{site}">← Все скидки Steam</a></p>
<h1>{html.escape(name)}</h1>
<img src="https://cdn.akamai.steamstatic.com/steam/apps/{i}/header.jpg" alt="{html.escape(name, quote=True)}" width="460" height="215">
{f"<p>{html.escape(desc)}</p>" if desc else ""}
{f'<p>Отзывы в Steam: {r["pct"]}% положительных ({r["total"]:,} отзывов).</p>'.replace(",", chr(160)) if r else ""}
<h2>Цена в Steam по регионам</h2>
<table><tr><th>Регион</th><th>Цена</th><th>Скидка</th></tr>{"".join(rows)}</table>
<p><a class="btn" href="https://store.steampowered.com/app/{i}/">Открыть в Steam</a></p>
<p>Обновлено: {today}. История цены и подсказка, стоит ли покупать сейчас, есть <a href="{site}">на главной странице</a>.</p>
</main></body></html>'''
        open(f"data/g/{i}.html", "w", encoding="utf-8").write(page)
        urls.append(f"{site}data/g/{i}.html")
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
        f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls) + "</urlset>\n"
    open("data/sitemap.xml", "w", encoding="utf-8").write(sm)
    print("страниц для поиска:", len(urls))

if __name__ == "__main__": main()
