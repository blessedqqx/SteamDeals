// Cloudflare Worker для SteamDeals.
// 1) /api/profile: библиотека и вишлист игрока. Ключ Steam API НЕ обязателен (без него читаются публичные страницы профиля).
// 2) Необязательно: Telegram-бот личных уведомлений о вишлисте (нужны KV-хранилище SUBS и секреты TG_TOKEN, TG_SECRET).
const STEAM = "https://api.steampowered.com", STORE = "https://store.steampowered.com/api/appdetails", COMM = "https://steamcommunity.com";
const cors = env => ({ "access-control-allow-origin": env.ALLOW_ORIGIN || "*", "access-control-allow-headers": "*" });
const J = (o, env, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { "content-type": "application/json", "cache-control": "max-age=300", ...cors(env) } });
const esc = s => String(s).replace(/[&<>]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
const txt = async u => (await fetch(u, { headers: { "user-agent": "Mozilla/5.0" } })).text();

async function resolve(env, q) {
  q = (q || "").trim();
  let m = q.match(/steamcommunity\.com\/profiles\/(\d{17})/);
  if (m) return m[1];
  if (/^\d{17}$/.test(q)) return q;
  m = q.match(/steamcommunity\.com\/id\/([^\/?#]+)/);
  const v = m ? m[1] : q;
  if (!/^[\w-]{2,64}$/.test(v)) return null;
  if (env.STEAM_API_KEY) {
    const r = await (await fetch(`${STEAM}/ISteamUser/ResolveVanityURL/v1/?key=${env.STEAM_API_KEY}&vanityurl=${v}`)).json();
    return r.response?.success === 1 ? r.response.steamid : null;
  }
  m = (await txt(`${COMM}/id/${v}/?xml=1`)).match(/<steamID64>(\d{17})<\/steamID64>/);
  return m ? m[1] : null;
}
async function owned(env, id) {   // null = профиль или список игр закрыт
  if (env.STEAM_API_KEY) {
    const r = await (await fetch(`${STEAM}/IPlayerService/GetOwnedGames/v1/?key=${env.STEAM_API_KEY}&steamid=${id}&include_played_free_games=1`)).json();
    return r.response?.games || null;
  }
  const x = await txt(`${COMM}/profiles/${id}/games?tab=all&xml=1`), out = [];
  for (const g of x.matchAll(/<game>([\s\S]*?)<\/game>/g)) {
    const a = g[1].match(/<appID>(\d+)<\/appID>/); if (!a) continue;
    const h = g[1].match(/<hoursOnRecord>([\d.,]+)<\/hoursOnRecord>/);
    out.push({ appid: +a[1], playtime_forever: h ? Math.round(parseFloat(h[1].replace(/,/g, "")) * 60) : 0 });
  }
  return out.length ? out : null;
}
async function wishlist(env, id) {
  try {
    const r = await (await fetch(`${STEAM}/IWishlistService/GetWishlist/v1/?${env.STEAM_API_KEY ? "key=" + env.STEAM_API_KEY + "&" : ""}steamid=${id}`)).json();
    return (r.response?.items || []).map(i => i.appid).slice(0, 150);
  } catch { return null; }
}
async function prices(ids, cc) {
  const out = {};
  for (let i = 0; i < ids.length; i += 50) {
    const r = await (await fetch(`${STORE}?appids=${ids.slice(i, i + 50).join(",")}&cc=${cc}&filters=price_overview`)).json();
    for (const [id, v] of Object.entries(r)) {
      const p = v.data?.price_overview;
      if (p) out[id] = { initial: p.initial / 100, final: p.final / 100, discount: p.discount_percent, currency: p.currency };
    }
  }
  return out;
}
async function names(ids) {
  const out = {};
  await Promise.all(ids.map(async id => {
    try { out[id] = (await (await fetch(`${STORE}?appids=${id}&filters=basic`)).json())[id]?.data?.name; } catch {}
  }));
  return out;
}

async function profile(u, env) {
  const cc = ["ua", "us", "kz", "ru"].includes(u.searchParams.get("cc")) ? u.searchParams.get("cc") : "ua";
  const id = await resolve(env, u.searchParams.get("q"));
  if (!id) return J({ error: "notfound" }, env, 404);
  const games = await owned(env, id);
  if (!games) return J({ error: "private" }, env, 403);
  const ids = await wishlist(env, id);
  let wl = [];
  if (ids?.length) {
    const p = await prices(ids, cc);
    wl = Object.entries(p).map(([k, v]) => ({ id: +k, ...v })).sort((a, b) => b.discount - a.discount);
    const nm = await names(wl.filter(x => x.discount > 0).slice(0, 30).map(x => x.id));
    wl.forEach(x => { x.name = nm[x.id] || null; });
  }
  return J({ steamid: id, games: games.map(g => ({ appid: g.appid, minutes: g.playtime_forever })), wishlist: wl }, env);
}

const send = (env, chat, text) => fetch(`https://api.telegram.org/bot${env.TG_TOKEN}/sendMessage`, {
  method: "POST", headers: { "content-type": "application/json" },
  body: JSON.stringify({ chat_id: chat, text, parse_mode: "HTML", disable_web_page_preview: true })
});

async function tg(update, env) {
  if (!env.SUBS || !env.TG_TOKEN) return;
  const msg = update.message;
  if (!msg?.text) return;
  const chat = msg.chat.id, [cmd, ...rest] = msg.text.trim().split(/\s+/), arg = rest.join(" ");
  const key = "sub:" + chat;
  let sub = JSON.parse((await env.SUBS.get(key)) || "null");
  if (cmd === "/start") {
    const id = arg && await resolve(env, arg);
    if (!id) return send(env, chat, "Пришлите: /start ссылка_на_профиль_Steam_или_SteamID");
    sub = { steam: id, region: sub?.region || "ua", seen: {} };
    await env.SUBS.put(key, JSON.stringify(sub));
    return send(env, chat, "Готово. Напишу, когда игры из вашего вишлиста подешевеют.\nРегион: /region ua, us, kz или ru. Отключить: /stop");
  }
  if (cmd === "/region" && sub && ["ua", "us", "kz", "ru"].includes(arg)) {
    sub.region = arg; sub.seen = {};
    await env.SUBS.put(key, JSON.stringify(sub));
    return send(env, chat, "Регион: " + arg);
  }
  if (cmd === "/stop") { await env.SUBS.delete(key); return send(env, chat, "Уведомления отключены."); }
  return send(env, chat, "Команды: /start ссылка, /region ua|us|kz|ru, /stop");
}

async function notify(env) {
  if (!env.SUBS || !env.TG_TOKEN) return;
  const { keys } = await env.SUBS.list({ prefix: "sub:" });
  for (const k of keys) {
    const sub = JSON.parse(await env.SUBS.get(k.name)), chat = k.name.slice(4);
    const ids = await wishlist(env, sub.steam);
    if (!ids?.length) continue;
    const p = await prices(ids, sub.region), fresh = [];
    for (const [id, x] of Object.entries(p)) {
      if (x.discount < 20) { delete sub.seen[id]; continue; }
      if (sub.seen[id] !== undefined && x.final >= sub.seen[id]) continue; // уже сообщали
      sub.seen[id] = x.final; fresh.push([id, x]);
    }
    if (fresh.length) {
      fresh.sort((a, b) => b[1].discount - a[1].discount);
      const top = fresh.slice(0, 12), nm = await names(top.map(f => f[0]));
      await send(env, chat, "Из вашего вишлиста подешевело:\n\n" + top.map(([id, x]) =>
        `−${x.discount}% <b>${esc(nm[id] || "Игра " + id)}</b>: ${x.final} ${x.currency}\nhttps://store.steampowered.com/app/${id}/?cc=${sub.region}`).join("\n\n"));
    }
    await env.SUBS.put(k.name, JSON.stringify(sub));
  }
}

export default {
  async fetch(req, env) {
    const u = new URL(req.url);
    if (req.method === "OPTIONS") return new Response(null, { headers: cors(env) });
    if (u.pathname === "/api/profile") return profile(u, env).catch(() => J({ error: "fail" }, env, 500));
    if (u.pathname === "/tg" && req.method === "POST") {
      if (req.headers.get("x-telegram-bot-api-secret-token") !== env.TG_SECRET) return new Response("no", { status: 403 });
      await tg(await req.json(), env);
      return new Response("ok");
    }
    return new Response("steam-deals worker is running");
  },
  async scheduled(_, env, ctx) { ctx.waitUntil(notify(env)); }
};
