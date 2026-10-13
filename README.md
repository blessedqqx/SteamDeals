# Steam Deals (UA, US, KZ, RU)

## 1. Сайт и цены (обязательно)
1. Создайте репозиторий на GitHub, загрузите все файлы.
2. Settings → Pages → Deploy from branch → main / root.
3. Actions → update-prices → Run workflow. Дальше запускается каждый день:
   пополняет каталог (discover.py), собирает цены по 4 регионам (collect.py), отзывы (reviews.py), постит в канал (post_telegram.py).

## 2. Профиль, вишлист, подбор, Telegram-бот (по желанию)
Нужен бесплатный Cloudflare Worker (папка worker/).
1. Ключ Steam API: https://steamcommunity.com/dev/apikey
2. Бот в Telegram: напишите @BotFather → /newbot → токен.
3. В папке worker:
   - npm i -g wrangler && wrangler login
   - wrangler kv namespace create SUBS  → вставьте id в wrangler.toml
   - в wrangler.toml впишите SITE_URL (адрес вашего GitHub Pages)
   - wrangler secret put STEAM_API_KEY / TG_TOKEN / TG_SECRET (TG_SECRET придумайте сами, латиница и цифры)
   - wrangler deploy  → получите адрес воркера
4. Подключите бота: откройте в браузере
   https://api.telegram.org/bot<TG_TOKEN>/setWebhook?url=<АДРЕС_ВОРКЕРА>/tg&secret_token=<TG_SECRET>
5. В index.html в CONFIG впишите WORKER (адрес воркера) и TG_BOT (имя бота без @).

## 3. Автопост в Telegram-канал (по желанию)
1. Добавьте бота в канал администратором.
2. GitHub → Settings → Secrets and variables → Actions: секреты TG_TOKEN, TG_CHANNEL (например @mychannel), переменная SITE_URL.

Регионы и пороги цен: REGIONS в scripts/collect.py и REG в index.html.
Локально: python -m http.server, затем http://localhost:8000
