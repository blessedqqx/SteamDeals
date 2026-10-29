#!/bin/bash
# Все проверки одной командой. Запуск из папки проекта:  bash tests/run.sh
# Нужны python3 и node. Интернет НЕ нужен: ответы Steam, SteamSpy и Telegram подменяются заглушками.
set -eo pipefail
T=$(mktemp -d)
cp -r index.html config.js scripts "$T"/; mkdir "$T/data"; cp data/games.json "$T/data/"; [ -f data/announce.json ] && cp data/announce.json "$T/data/"; echo '{}' > "$T/data/reviews.json"
cp tests/* "$T"/; cp worker/index.js "$T/worker.mjs"; cd "$T"
export GITHUB_REPOSITORY=owner/repo TG_TOKEN=T TG_CHANNEL=@chan
python3 -c "import json;g=json.load(open('data/games.json',encoding='utf-8'));json.dump([x for x in g if x['id'] not in (1091500,1174180,271590)],open('data/games.json','w',encoding='utf-8'),ensure_ascii=False)"
echo "== сбор данных (discover, collect, reviews, post_telegram) на заглушках"; python3 harness2.py discover collect reviews post_telegram | grep -v "нет цены"
python3 check_data.py
echo "== раздачи и популярные игры со смешанной оценкой"; python3 gift_test.py
python3 prepare_site.py
echo "== сайт: основные сценарии";   node fe_test3.js | tail -1
echo "== сайт: сортировка, вердикты, профиль"; node fe_test.js | tail -1
echo "== сайт: избранное, «Лучшее сегодня», раздачи"; node fe_test4.js | tail -40
python3 make150.py; (cd site150 && echo "== сайт: 150 игр и «Показать ещё»" && node ../fe_test2.js | tail -1)
echo "== воркер Cloudflare"; node worker_test.mjs | tail -1
echo "Готово. Рабочая папка тестов: $T"
