"""Telegram kanalına paylaşım. pipeline.sh-dakı tg_loop işlədir; sirlər yoxdursa heç işə düşmür.

Kanala hər xəbər getmir:
- son dəqiqə: ən azı MIN_SOURCES mənbədə çıxan təzə xəbər, iki paylaşım arasında ən azı MIN_GAP_S;
- səhər xülasəsi (08:30, Bakı vaxtı): son 12 saatın 5 əsas xəbəri və AMB məzənnəsi;
- axşam xülasəsi (21:00): günün 5 əsas xəbəri.
Gecə (00:00–07:00) yalnız çox mənbəli xəbər səssiz bildirişlə gedir.

İki addım: «plan» göndəriləcək mesajı və yeni vəziyyəti yazır (açar görmür), «send» onu göndərir (yalnız açarı görür).
Vəziyyət telegram-state budağındadır. pipeline.sh əvvəl onu yazır, sonra göndərir: növbə dəyişəndə iki iş eyni xəbəri göndərməsin.

Xəbərlər lentdəki kimi content_policy.enforce-dan yenidən keçir (QIRMIZI XƏTT 2). Mətn yalnız başlıq və keçiddir: xülasə və şəkil
paylaşılmır (müəllif hüququ), önizləmə mənbənin öz səhifəsidir.
"""
import datetime
import hashlib
import html
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import content_policy  # noqa: E402

SITE = "https://8ulduz.az/"
BAKU = datetime.timezone(datetime.timedelta(hours=4))
MIN_SOURCES = 3            # son dəqiqə üçün ən az mənbə (əsas + alts)
NIGHT_SOURCES = 8          # gecə yalnız bundan çox mənbəli xəbər, səssiz
MIN_GAP_S = 20 * 60        # iki son dəqiqə paylaşımı arası: saatda ən çox 3
FRESH_S = 2 * 3600         # xəbərin ən yeni mənbəsi bu qədər təzə olmalıdır
FIRST_S = 6 * 3600         # ilk mənbəsi bundan köhnə olan xəbər «son dəqiqə» deyil
NIGHT = (0, 7)             # Bakı saatı ilə [başlanğıc, son)
DIGESTS = (                # ad, başlanğıc (saat, dəqiqə), gecikmə limiti (dəq), pəncərə (saat), başlıq
    ("morning", (8, 30), 90, 12, "Səhər xülasəsi"),
    ("evening", (21, 0), 90, 15, "Günün yekunu"),
)
KEEP_KEYS = 600
KEEP_TITLES = 40
MONTHS = ("yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr")
RATES = ("USD", "EUR", "RUB100")


def _time(value):
    try:
        t = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)


def url_key(url):
    """updater.py-dakı xəbər nömrəsi ilə eyni: ünvanın sha1-i."""
    return hashlib.sha1(url.encode()).hexdigest()[:16]


def keys_of(article):
    urls = [article.get("sourceUrl")] + [alt.get("sourceUrl") for alt in article.get("alts") or []]
    return {url_key(u) for u in urls if u}


def source_count(article):
    return len({article.get("source")} | {alt.get("source") for alt in article.get("alts") or []})


def words(title):
    return {w for w in re.findall(r"\w+", (title or "").lower()) if len(w) >= 4 and not w.isdigit()}


def similar(a, b):
    common = len(a & b)
    return common >= 4 or (common >= 2 and common / max(1, len(a | b)) >= 0.5)


def story_url(article, ref):
    """Saytdakı xəbər səhifəsi (paylaşım düyməsinin keçidi ilə eyni). ref GoatCounter-də kanal kimi görünür."""
    cat = urllib.parse.quote(article.get("category") or "")
    return f"{SITE}?ref={ref}#/xeber/{urllib.parse.quote(article.get('id') or '')}?b={cat}"


def allowed(articles):
    """Lentdə olsa da yenidən yoxlanır: kanal da açıq yayımdır. Prezident xəbərləri saytdakı kimi «son dəqiqə»yə düşmür."""
    clean, _dropped = content_policy.enforce(articles)
    return [a for a in clean if (a.get("lang") or "az") == "az" and a.get("category") != "prezident" and a.get("title")]


def ranked(articles, since, now, need):
    """Saytdakı heroPick kimi: çox mənbəli xəbər əvvəl, eyni mövzu bir dəfə."""
    pool = [a for a in articles if (t := _time(a.get("publishedAt"))) and since <= t <= now + datetime.timedelta(minutes=5)]
    pool.sort(key=lambda a: (source_count(a), a.get("publishedAt") or ""), reverse=True)
    out, seen = [], []
    for a in pool:
        w = words(a.get("title"))
        if any(similar(w, s) for s in seen):
            continue
        out.append(a)
        seen.append(w)
        if len(out) >= need:
            break
    return out


def due_digest(state, now):
    local = now.astimezone(BAKU)
    for name, (hour, minute), late, window, label in DIGESTS:
        start = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if start <= local < start + datetime.timedelta(minutes=late) and (state.get("digests") or {}).get(name) != local.date().isoformat():
            return name, window, label
    return None


def rates_line(markets):
    items = {i.get("id"): i for i in (markets or {}).get("items") or []}
    rows = [items[k] for k in RATES if k in items and items[k].get("value") is not None]
    if not rows:
        return ""
    src = {r.get("src") for r in rows}
    shown = " · ".join(f'{html.escape(r.get("label") or r["id"])} {float(r["value"]):.4f}' for r in rows)
    return f"{shown} AZN ({html.escape(', '.join(sorted(s for s in src if s)))})"


def digest_text(label, stories, markets, now, with_rates):
    local = now.astimezone(BAKU)
    lines = [f"<b>{label} — {local.day} {MONTHS[local.month - 1]}</b>", ""]
    for i, a in enumerate(stories, 1):
        n = source_count(a)
        lines.append(f'{i}. <a href="{html.escape(a["sourceUrl"])}">{html.escape(a["title"], quote=False)}</a>'
                     + (f" · {n} mənbə" if n > 1 else ""))
    rates = rates_line(markets) if with_rates else ""
    if rates:
        lines += ["", rates]
    lines += ["", f'<a href="{SITE}?ref=tg-xulase">8ulduz.az — bütün xəbərlər</a>']
    return "\n".join(lines)


def alert_text(article):
    others = source_count(article) - 1
    src = f'<a href="{html.escape(article["sourceUrl"])}">{html.escape(article.get("source") or "Mənbə", quote=False)}</a>'
    return (f"<b>{html.escape(article['title'], quote=False)}</b>\n\n"
            f"{src}{f' və daha {others} mənbə' if others else ''}\n"
            f'<a href="{html.escape(story_url(article, "tg"))}">Bütün mənbələr — 8ulduz.az</a>')


def remember(state, article, now, alert):
    state["keys"] = (state.get("keys") or []) + sorted(keys_of(article) - set(state.get("keys") or []))
    state["keys"] = state["keys"][-KEEP_KEYS:]
    state["titles"] = ((state.get("titles") or []) + [[now.isoformat(), article.get("title") or ""]])[-KEEP_TITLES:]
    if alert:
        state["lastAlert"] = now.isoformat()


def pick_alert(articles, state, now):
    local = now.astimezone(BAKU)
    night = NIGHT[0] <= local.hour < NIGHT[1]
    last = _time(state.get("lastAlert"))
    if last and (now - last).total_seconds() < MIN_GAP_S:
        return None, False
    posted = set(state.get("keys") or [])
    recent = [words(t) for at, t in state.get("titles") or [] if (x := _time(at)) and (now - x).total_seconds() < 86400]
    need = NIGHT_SOURCES if night else MIN_SOURCES
    best = None
    for a in articles:
        if source_count(a) < need or keys_of(a) & posted:
            continue
        times = [t for t in [_time(a.get("publishedAt"))] + [_time(x.get("publishedAt")) for x in a.get("alts") or []] if t]
        if not times or (now - max(times)).total_seconds() > FRESH_S or (now - min(times)).total_seconds() > FIRST_S:
            continue
        if max(times) > now + datetime.timedelta(minutes=5):
            continue
        w = words(a.get("title"))
        if any(similar(w, r) for r in recent):
            continue
        if best is None or (source_count(a), a.get("publishedAt") or "") > (source_count(best), best.get("publishedAt") or ""):
            best = a
    return best, night


def plan(news, markets, state, now):
    """(mesaj, yeni vəziyyət) və ya (None, None). Mesaj Bot API sendMessage sahələridir, chat_id-siz."""
    state = json.loads(json.dumps(state or {}))
    articles = allowed((news or {}).get("articles") or [])
    due = due_digest(state, now)
    if due:
        name, window, label = due
        stories = ranked(articles, now - datetime.timedelta(hours=window), now, 5)
        state.setdefault("digests", {})[name] = now.astimezone(BAKU).date().isoformat()
        if len(stories) >= 3:
            for a in stories:
                remember(state, a, now, alert=False)
            return {"text": digest_text(label, stories, markets, now, name == "morning"), "parse_mode": "HTML",
                    "link_preview_options": {"is_disabled": True}}, state
        return None, state  # az xəbər: bu gün həmin xülasə keçilir, vəziyyət yenə yazılır
    article, night = pick_alert(articles, state, now)
    if not article:
        return None, None
    remember(state, article, now, alert=True)
    return {"text": alert_text(article), "parse_mode": "HTML", "disable_notification": night,
            "link_preview_options": {"url": article["sourceUrl"], "prefer_small_media": True}}, state


def send(message, token, chat, timeout=15):
    body = json.dumps({**message, "chat_id": chat}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode()).get("ok") is True, ""
    except urllib.error.HTTPError as e:  # açar ünvandadır: xətanın özü yox, yalnız Telegram-ın izahı çap olunur
        try:
            return False, f"HTTP {e.code}: {json.loads(e.read().decode()).get('description', '')}"
        except Exception:
            return False, f"HTTP {e.code}"
    except Exception as e:
        return False, type(e).__name__


def _read(path, default):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def main(argv):
    if len(argv) == 7 and argv[1] == "plan":
        _, _, news, markets, old, new, out = argv
        message, state = plan(_read(news, {}), _read(markets, {}), _read(old, {}), datetime.datetime.now(datetime.timezone.utc))
        if state is None:
            return 1
        pathlib.Path(new).write_text(json.dumps(state, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        pathlib.Path(out).write_text(json.dumps(message, ensure_ascii=False) if message else "", encoding="utf-8")
        return 0
    if len(argv) == 3 and argv[1] == "send":
        token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT", "")
        message = _read(argv[2], None)
        if not (token and chat and message):
            return 0
        ok, why = send(message, token, chat)
        if not ok:
            print("Telegram: göndərilmədi:", why)
        return 0 if ok else 1
    print("istifadə: telegram_post.py plan NEWS MARKETS OLD NEW OUT | send MSG", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
