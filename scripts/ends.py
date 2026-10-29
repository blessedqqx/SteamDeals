"""Даты окончания скидок. Берём из официального магазинного запроса Steam IStoreBrowseService/GetItems (ключ не нужен), по 50 игр за раз.
Пишет data/<регион>/ends.json вида {"id игры": время окончания (unix-секунды)} только для игр, у которых скидка ещё действует.
Запускается из collect.py; любая ошибка здесь не мешает сбору цен."""
import json, time, urllib.parse, urllib.request
BATCH = 50

def fetch(cc, ids):
    q = {"ids": [{"appid": int(i)} for i in ids], "context": {"language": "english", "country_code": cc.upper(), "steam_realm": 1},
         "data_request": {"include_all_purchase_options": True}}
    url = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1?input_json=" + urllib.parse.quote(json.dumps(q, separators=(",", ":")))
    for attempt in range(2):
        try: return json.load(urllib.request.urlopen(url, timeout=60))
        except Exception as e: print(cc, "даты скидок, повтор", attempt + 1, e); time.sleep(5)
    return None

def end_of(item):
    """Время окончания действующей скидки у основной покупки игры (или None)."""
    for po in [item.get("best_purchase_option")] + list(item.get("purchase_options") or []):
        if not isinstance(po, dict): continue
        for d in po.get("active_discounts") or []:
            try: e = int(d.get("discount_end_date") or 0)
            except (TypeError, ValueError): continue
            if e: return e
    return None

def run(regions):
    now = time.time()
    for cc in regions:
        try: items = json.load(open(f"data/{cc}/prices.json", encoding="utf-8"))["items"]
        except Exception: continue
        ids = [i for i, it in items.items() if it.get("discount", 0) > 0 and not it.get("free")]
        out, ok = {}, 0
        for k in range(0, len(ids), BATCH):
            data = fetch(cc, ids[k:k + BATCH])
            if not data: continue
            ok += 1
            for it in (data.get("response") or {}).get("store_items") or []:
                e = end_of(it); i = str(it.get("appid") or it.get("id") or "")
                if e and e > now and i in items: out[i] = e
            time.sleep(1.5)
        if ok or not ids:      # если Steam не ответил ни разу, старый файл остаётся
            json.dump(out, open(f"data/{cc}/ends.json", "w", encoding="utf-8"), separators=(",", ":"))
        print(cc, "даты окончания скидок:", len(out), "из", len(ids), "со скидкой")
