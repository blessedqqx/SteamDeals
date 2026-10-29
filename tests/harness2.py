import json, runpy, sys, os, time, urllib.request, urllib.parse, io
time.sleep = lambda *_: None
sys.path.insert(0, os.path.abspath("scripts"))
R = lambda o: io.BytesIO(json.dumps(o).encode())
def big(n, p, ng, own="1,000,000 .. 2,000,000", price="1999", ini="1999"): return {"name": n, "positive": p, "negative": ng, "owners": own, "price": price, "initialprice": ini}
def tagdata(tag):
    if tag == "Hentai": return {"900001": big("Bad Game", 9000, 100)}
    if tag == "Story Rich": return {"1091500": big("Cyberpunk 2077", 500000, 100000, "5,000,000 .. 10,000,000"), "777001": big("Some Hit", 80000, 5000)}
    if tag == "Shooter": return {"777020": big("Divisive Giant", 60000, 70000), "777021": big("Divisive Small", 3000, 3500), "777022": big("Good Enough", 7000, 2500)}
    if tag == "Co-op": return {"777011": big("Free Hit", 300000, 20000, "20,000,000 .. 50,000,000", "0", "0")}
    if tag == "Open World": return {"1091500": big("Cyberpunk 2077", 500000, 100000), "777002": big("Open Hit", 60000, 4000)}
    return {}
def fake(req, timeout=None):
    url = req if isinstance(req, str) else req.full_url
    u = urllib.parse.urlparse(url); q = urllib.parse.parse_qs(u.query)
    if "api.telegram.org" in u.netloc:
        body = json.loads(req.data.decode()); open("tg.log", "a").write(json.dumps({"m": u.path.split("/")[-1], **body}, ensure_ascii=False) + "\n"); return R({"ok": True})
    if "steamspy" in u.netloc:
        if q["request"][0] == "tag": return R(tagdata(q["tag"][0]))
        if q["request"][0] == "top100forever": return R({"777030": big("Popular Meh", 20000, 40000), "777031": big("Tiny Top", 1000, 500)})
        if q["request"][0] in ("top100in2weeks", "top100owned"): return R({"777030": big("Popular Meh", 20000, 40000)})
        return R({"name": "Deal Game", "tags": {"Horror": 100}})
    if "IStoreBrowseService" in u.path:       # даты окончания скидок
        ids = [x["appid"] for x in json.loads(q["input_json"][0])["ids"]]
        past, fut = int(time.time()) - 86400, int(time.time()) + 3 * 86400
        return R({"response": {"store_items": [{"appid": i, "best_purchase_option": {"active_discounts": [{"discount_end_date": past if i == 1174180 else fut}]}} for i in ids if i != 777002]}})
    if u.path.endswith("featuredcategories"): return R({"specials": {"items": [{"id": 777099, "name": "Free Gift", "discount_percent": 100}]}, "top_sellers": {"items": []}})
    if u.path.endswith("appdetails"):
        ids = q["appids"][0].split(",")
        if "price_overview" in q.get("filters", [""])[0]:
            out = {}
            for i in ids:
                if i in ("730", "777011"): out[i] = {"success": True, "data": []}              # бесплатные
                elif i == os.environ.get("GIFT"): out[i] = {"success": True, "data": {"price_overview": {"initial": 100000, "final": 0, "discount_percent": 100, "currency": {"ua":"UAH","us":"USD","kz":"KZT","ru":"RUB"}[q["cc"][0]]}}}   # раздача
                elif i == "292030": out[i] = {"success": False}                                  # нет в регионе
                elif i == "1091500" and len(ids) > 1: continue                                    # потерян в пакетном ответе
                else: out[i] = {"success": True, "data": {"price_overview": {"initial": 100000, "final": 50000, "discount_percent": 50, "currency": {"ua":"UAH","us":"USD","kz":"KZT","ru":"RUB"}[q["cc"][0]]}}}
            return R(out)
        i = ids[0]
        return R({i: {"success": True, "data": {"short_description": ("Hi game. " + "Длинное описание игры. " * 60) if i == "1091500" else "<b>Hi</b> &quot;game&quot; " + i, "developers": ["Dev"], "release_date": {"date": "2020"}, "genres": [{"description": "RPG"}],
            "screenshots": [{"path_thumbnail": f"https://x/{i}/ss_{n}.600x338.jpg?t=1", "path_full": f"https://x/{i}/ss_{n}.1920x1080.jpg?t=1"} for n in range(8)]}}})
    if "appreviewhistogram" in u.path: return R({"results": {"rollups": [{"date": 1735689600, "recommendations_up": 10, "recommendations_down": 2}]}})
    if "appreviews" in u.path: return R({"query_summary": {"total_positive": 90, "total_negative": 10}})
    raise Exception("unexpected url " + url)
urllib.request.urlopen = fake
for s in sys.argv[1:]:
    print("==", s); runpy.run_path(f"scripts/{s}.py", run_name="__main__")
