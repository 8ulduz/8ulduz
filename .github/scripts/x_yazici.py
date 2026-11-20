"""X xəbərlərinin yazıcısı, GitHub Actions-da (sahib, 2026-11-18: «bunu avtomatlaşdır. claude nin açıq bağlı olmasına
bağlama»). İş axını: .github/workflows/x-yazici.yml. Təlimat və qaydalar: docs/x-yazici.md.

1. oz_x.HESABLAR-ın hər hesabının son paylaşımları: api.fxtwitter.com (açarsız, API-siz).
2. Namizəd: son 6 saat, videolu, repost və cavab deyil, növbədə yoxdur, mətnində Azərbaycan mövzusu yoxdur
   (oz_x.about_azerbaijan: qırmızı xətt 2), bitrate-i ≤ 1 Mbit/s olan mp4 variantı var.
3. Gemini (GEMINI_API_KEY, pulsuz səviyyə; Claude açarı varsa və Gemini-ninki yoxdursa Claude) namizədlərdən ən çoxu PER_RUN xəbər seçib Azərbaycan dilində yazır: yalnız id, kind, title, lead,
   body. Ünvanlar, ölçü, tarix, slot və mənbə mətni (src) modeldən yox, X-in cavabından götürülür.
4. Hər sətir oz_x.check-dən keçir; keçməyən yazılmır. MAX_AGE_DAYS gündən köhnə sətirlər silinir.
5. Yalnız oz_x.json dəyişir; commit və push iş axınındadır (sahibin icazəsi, 2026-11-18: yalnız bu fayl, birbaşa main).

Açar yoxdursa: X-dən oxuyur, namizədləri sayır, heç nə yazmır (FxTwitter-in GitHub-dan işlədiyinin yoxlaması).
"""
import datetime
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import oz_x as xm  # noqa: E402
import oz_xeber as ox  # noqa: E402

BAKU = ox.BAKU
FX = "https://api.fxtwitter.com/2/profile/{}/statuses"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
WINDOW = datetime.timedelta(hours=6)
MAX_BITRATE = 1_000_000
MAX_CANDIDATES = 25
PER_RUN = 3
REELS_PER_RUN = 12  # qısa videolar gecə-gündüz 20 dəqiqədən bir (iş xəbər axınından başladılır, pipeline.sh xyazici_loop): 72 iş × 12 ≈ gündə 300–800 (sahib, 2026-11-20: «ən önəmli olan videoların daima yenilənməsidir», «çox sayda olmasıdır»)
REELS_ASK = 90     # Gemini-yə seçim üçün göstərilən ən çox namizəd
# Gemini işləməyəndə qısa videoya yalnız bu hesablar düşür: müharibə və qəza görüntüsü vermirlər
REELS_SAFE = {"TamirveTadilat", "TUBITAK", "avionot", "TFF_Org", "MilliTakimlar", "GalatasaraySK", "Fenerbahce", "Besiktas", "Trabzonspor", "trtspor", "aa_spor", "ntvspor", "beINSPORTS_TR", "Rainmaker1973", "buitengebieden", "wonderofscience", "Yoda4ever", "IGN", "GameSpot", "LaLiga", "premierleague", "ChampionsLeague", "EuropaLeague", "NBA", "ESPNNBA", "F1", "atptour", "Olympics", "Discovery", "LFC", "MLS", "Ballislife", "overtime"}
MAX_AGE_DAYS = 4
LAST_SLOT = "22:00"   # daha gec yazılan xəbər gün bitənədək dərc olunmağa çatmır və «gecikdi» deyə düşür (2026-11-18 gecəsi 4 xəbər)
GEMINI = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL") or ""   # boşdursa: açarın siyahısındakı ən yeni «flash» (2.5 artıq 404 verir)

PROMPT = """Sən 8ulduz.az xəbər saytının redaktorusan. Aşağıda türk və ingilis dilli X hesablarının videolu paylaşımları var.
Onlardan oxucunun ən çox izləmək istəyəcəyi ən çox {n} paylaşımı seç (idman, dünya, elm, maraqlı). Reklam, sponsor, bilet, mağaza,
mərc, qəza və zorakılıq görüntüsü olanları SEÇMƏ. Qan, meyit, yaralı, edam, işgəncə, hücum anı və ya zərbə nəticəsində insan
görünə biləcək müharibə və terror videolarını SEÇMƏ; müharibə mövzusunda yalnız texnika, sərgi, sınaq, görüş və bəyanat videoları
olar. Şərh, söz atışması, təhqir və siyasi təbliğat olan paylaşımları SEÇMƏ. Uyğun paylaşım yoxdursa boş siyahı qaytar.

Hər seçilən üçün Azərbaycan ədəbi dilində qısa xəbər yaz:
- Türkcə söz və şəkilçi işlətmə («yapıldı» yox, «edildi»; «maç» yox, «oyun»; «antrenman» yox, «məşq»).
- title: 25–110 hərf, sonunda nöqtə, sual, nida yoxdur.
- lead: 60–420 hərf. Mənbəni adı ilə de: məsələn «Qalatasaray klubunun paylaşdığı videoda…».
- body: 1–3 abzas, hər biri 40–800 hərf.
- Nida işarəsi, keçid, kiril hərfi YOXDUR. «bu gün», «dünən», «sabah», «bu axşam», «bu gecə» kimi sözlər YOXDUR.
- Mətndəki hər rəqəm paylaşımın mətnində olmalıdır. Paylaşımda olmayan fakt əlavə etmə, videonu təxmin edib təsvir etmə.
- Rəsmi qurum olmayan hesabın (Clash Report, Conflict, Pars Plus, Derin Kuvvetler, Voice of Levant, Gusholder Haber, GDH,
  Özet Geç, Avionot) xəbərini fakt kimi yox, onun məlumatı kimi yaz: «Clash Report-un yaydığı məlumata görə…», «…bildirilir».
  Tərəf tutma, qiymət vermə.
- Prezident və dövlət rəhbərlərinin adlarını yazma.
- kind: x-idman, x-dunya, x-elm və ya x-maraqli.

Yalnız JSON siyahısı qaytar, başqa heç nə:
[{{"id": "<paylaşımın id-si>", "kind": "...", "title": "...", "lead": "...", "body": ["..."]}}]

Paylaşımlar:
{items}"""


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def best_mp4(video):
    """Bitrate-i MAX_BITRATE-dən çox olmayan ən yaxşı mp4 (telefonda tez açılsın)."""
    best = None
    for f in video.get("formats") or []:
        url, rate = str(f.get("url") or ""), f.get("bitrate")
        if f.get("container") == "mp4" and isinstance(rate, int) and 0 < rate <= MAX_BITRATE and url.startswith("https://video.twimg.com/"):
            if best is None or rate > best[0]:
                best = (rate, url)
    return best[1] if best else None


def candidate(handle, post, known, now, window=WINDOW):
    """X-in paylaşımından növbə sətrinin X hissəsi (mətnsiz) və ya None."""
    pid = str(post.get("id") or "")
    if not re.fullmatch(r"[1-9]\d{5,24}", pid) or pid in known or post.get("reposted_by") or post.get("replying_to"):
        return None
    ts = post.get("created_timestamp")
    if not isinstance(ts, (int, float)) or now - datetime.datetime.fromtimestamp(ts, datetime.timezone.utc) > window:
        return None
    author = str((post.get("author") or {}).get("screen_name") or "")
    if author.lower() != handle.lower():
        return None
    videos = ((post.get("media") or {}).get("videos")) or []
    if not videos:
        return None
    v = videos[0]
    url, poster = best_mp4(v), str(v.get("thumbnail_url") or "")
    w, h = v.get("width"), v.get("height")
    text = " ".join(str(post.get("text") or "").split())
    if not url or not poster.startswith("https://pbs.twimg.com/") or not isinstance(w, int) or not isinstance(h, int):
        return None
    if len(text) < xm.SRC_LEN[0] or xm.about_azerbaijan(text):
        return None
    return {"id": pid, "handle": handle, "post": f"https://x.com/{handle}/status/{pid}", "video": url, "poster": poster,
            "w": w, "h": h, "src": [text[:xm.SRC_LEN[1]]], "at": datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat(timespec="seconds"), "_score": int(post.get("likes") or 0) + int(post.get("reposts") or 0) * 3}


# Transfer xəbərləri (sahib 2026-11-19: «x da olan transfer xəbərləri fabrisio və matteo dan və digər x transfer xəbərləri bizim
# transfer xəbərlərinə düşsün»): oz_x.TRANSFER_HESABLAR-ın mətn/şəkil paylaşımları, video tələb olunmur. collect() onları TRANSFERS-ə yığır.
TRANSFER_RX = re.compile(r"here we go|transfer|agreement|\bdeal\b|medical|\bbid\b|\bloan\b|\bsign(?:s|ed|ing)?\b|contract|release clause|"
                         r"anlaşma|imza|teklif|kiral|bonservis|fichaje|acuerdo|cesi[oó]n|oferta", re.I)
TRANSFER_PER_RUN = 3
TRANSFERS = []


def transfer_candidate(handle, post, known, now):
    """Transfer hesabının paylaşımından namizəd (mətnsiz) və ya None. Şəkil varsa (pbs.twimg.com) poster olur."""
    if handle not in xm.TRANSFER_HESABLAR:
        return None
    pid = str(post.get("id") or "")
    if not re.fullmatch(r"[1-9]\d{5,24}", pid) or pid in known or post.get("reposted_by") or post.get("replying_to"):
        return None
    ts = post.get("created_timestamp")
    if not isinstance(ts, (int, float)) or now - datetime.datetime.fromtimestamp(ts, datetime.timezone.utc) > WINDOW:
        return None
    if str((post.get("author") or {}).get("screen_name") or "").lower() != handle.lower():
        return None
    text = " ".join(str(post.get("text") or "").split())
    if len(text) < xm.SRC_LEN[0] or not TRANSFER_RX.search(text) or xm.about_azerbaijan(text):
        return None
    photo = str((((post.get("media") or {}).get("photos") or [{}])[0] or {}).get("url") or "")
    out = {"id": pid, "handle": handle, "post": f"https://x.com/{handle}/status/{pid}", "src": [text[:xm.SRC_LEN[1]]],
           "_score": int(post.get("likes") or 0) + int(post.get("reposts") or 0) * 3}
    if photo.startswith("https://pbs.twimg.com/"):
        out["poster"] = photo
    return out


VL_PER_RUN = 70   # Videolent hesablarından hər işdə bu qədəri (hər mövzudan ~8, növbə ilə): kiçik mövzular ~4 saatda, idman ~12 saatda dövr edir; video 24 saatadək götürülür
REEL_WINDOW = datetime.timedelta(hours=24)   # Videolent hesabı bir neçə saatdan bir yoxlanır: videosu 24 saatadək götürülür


def videolent_slice(now):
    """Bu işdə yoxlanacaq Videolent hesabları: siyahı 20 dəqiqəlik növbələrlə dövr edir (hər hesab bir neçə saatdan bir)."""
    groups = [list(q) for q in xm.VIDEOLENT_QRUPLAR.values() if q]   # hər mövzunun öz növbəsi: hər iş bütün mövzulardan bərabər
    if not groups:
        return []
    per, run, out = max(1, VL_PER_RUN // len(groups)), int(now.timestamp()) // 1200, []
    for g in groups:
        start = (run * per) % len(g)
        out += (g + g)[start:start + min(per, len(g))]
    return out


RETRY_PAUSE = 45   # saniyə: keçidin sonunda sorğu həddi açılsın deyə gözləmə
RETRY_GAP = 5      # saniyə: təkrar keçiddə sorğular arası (ilk keçiddə 2)
RETRY_BUDGET = 9 * 60   # saniyə: təkrar keçid yalnız toplama bu vaxtdan az çəkibsə (iş 20 dəqiqəyə sığsın, Gemini-yə vaxt qalsın)


def collect(known, now):
    out, failed, later = [], [], []
    TRANSFERS.clear()
    began = time.monotonic()

    def take(handle, doc):
        reel_only = handle not in xm.HESABLAR   # yalnız Videolent: xəbər yazılmır
        for post in doc.get("results") or []:
            c = candidate(handle, post, known, now, REEL_WINDOW if reel_only else WINDOW)
            if c:
                c["reel_only"] = reel_only
                out.append(c)
            t = transfer_candidate(handle, post, known, now)
            if t:
                TRANSFERS.append(t)

    for handle in [*xm.HESABLAR, *videolent_slice(now)]:
        doc, err = None, ""
        for attempt in range(2 if handle in xm.HESABLAR else 1):   # FxTwitter ara-sıra 429/5xx verir: xəbər hesabında bir dəfə gözləyib təkrar
            try:
                doc = fetch_json(FX.format(handle))
                break
            except Exception as e:  # bir hesab düşsə digərləri işləyir
                err = f"{handle}: {getattr(e, 'code', '') or type(e).__name__}"
                time.sleep(4 + attempt * 6)
        time.sleep(2)   # tez-tez soruşanda FxTwitter 404 qaytarır
        if doc is None:
            (later if handle not in xm.HESABLAR else failed).append((handle, err))
            continue
        take(handle, doc)
    # Sahib 2026-11-20 («videolentin yenilənməsini elə et ki, tiktokdan geri qalmasın»): 03:57 işində 80 hesabdan 46-sı sorğu
    # həddinə düşdü. Həddə hörmət edərək: düşən Videolent hesabları fasilədən sonra, yavaş tempdə bir dəfə də soruşulur.
    if later and time.monotonic() - began < RETRY_BUDGET:
        time.sleep(RETRY_PAUSE)
        retry, later = later, []
        for handle, err in retry:
            if time.monotonic() - began >= RETRY_BUDGET:
                later.append((handle, err))
                continue
            try:
                take(handle, fetch_json(FX.format(handle)))
            except Exception as e:
                later.append((handle, f"{handle}: {getattr(e, 'code', '') or type(e).__name__}"))
            time.sleep(RETRY_GAP)
    failed = [e for _, e in failed + later]
    out.sort(key=lambda c: -c["_score"])
    TRANSFERS.sort(key=lambda c: -c["_score"])
    return out, failed   # hamısı: xəbərə ilk MAX_CANDIDATES, qısa videolara qalanı da


def _gemini_models(key):
    """Açarın görə bildiyi, generateContent edən «flash» modelləri, ən yenisi birinci (ad dəyişəndə iş dayanmasın)."""
    req = urllib.request.Request(GEMINI + "?pageSize=200", headers={"x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=30) as r:
        models = json.loads(r.read().decode("utf-8")).get("models") or []
    names = [m["name"].split("/", 1)[-1] for m in models if "generateContent" in (m.get("supportedGenerationMethods") or [])
             and "flash" in m.get("name", "") and not re.search(r"lite|image|tts|audio|live|exp|preview|thinking", m.get("name", ""))]
    return sorted(names, key=lambda s: [int(x) if x.isdigit() else 0 for x in re.findall(r"\d+", s)], reverse=True)


def ask_gemini(prompt, key):
    """Gemini API (pulsuz səviyyə, açar başlıqda; ünvanda yox). Model: GEMINI_MODEL, alınmasa siyahıdakı ən yeni flash."""
    body = json.dumps({"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                       "generationConfig": {"temperature": 0.4, "maxOutputTokens": 4000, "responseMimeType": "application/json"}}).encode("utf-8")
    tried, listed = [], _safe_models(key)
    order = ([GEMINI_MODEL] if GEMINI_MODEL else []) + [m for m in listed if m != GEMINI_MODEL]
    for model in order[:4]:
        doc = None
        for attempt in range(3):   # 503 (yüklüdür) və 429 keçicidir: gözləyib təkrar; 404 (model yoxdur) — növbəti model
            req = urllib.request.Request(f"{GEMINI}/{model}:generateContent", data=body, method="POST",
                                         headers={"x-goog-api-key": key, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=150) as r:
                    doc = json.loads(r.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                tried.append(f"{model}: {e.code}")
                if e.code not in (429, 500, 503):
                    break
                time.sleep(15 * (attempt + 1))
            except (TimeoutError, OSError, ValueError) as e:   # cavab gecikdi, bağlantı qırıldı, JSON pozuq: növbəti model
                tried.append(f"{model}: {type(e).__name__}")
                break
        if doc is None:
            continue
        parts = ((doc.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        print(f"Model: {model}", flush=True)
        return "".join(p.get("text", "") for p in parts)
    print("Gemini cavab vermədi: " + ", ".join(tried), flush=True)
    return ""


def _safe_models(key):
    try:
        return _gemini_models(key)
    except Exception as e:
        print(f"Model siyahısı alınmadı: {type(e).__name__}", flush=True)
        return []


def write(cands, n, template=None):
    items = "\n".join(f"- id {c['id']}, hesab {xm.ADLAR[c['handle']]} (@{c['handle']}): {c['src'][0]}" for c in cands)
    prompt = (template or PROMPT).format(n=n, items=items)
    if os.environ.get("GEMINI_API_KEY"):
        text = ask_gemini(prompt, os.environ["GEMINI_API_KEY"])
    else:
        import anthropic  # yalnız açar olanda quraşdırılır
        client = anthropic.Anthropic(max_retries=2, timeout=90.0)
        msg = client.messages.create(model=ox.MODEL, max_tokens=4000, messages=[{"role": "user", "content": prompt}])
        text = "".join(getattr(b, "text", "") for b in msg.content)
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        return []
    try:
        rows = json.loads(text[start:end + 1])
    except ValueError:
        return []
    return [r for r in rows if isinstance(r, dict)]


TRANSFER_PROMPT = """Sən 8ulduz.az xəbər saytının idman redaktorusan. Aşağıda futbol transfer jurnalistlərinin X paylaşımları var.
Onlardan ən vacib ən çox {n} transfer xəbərini seç: tanınmış klublar və oyunçular, türk klubları üstün. Eyni transferi bir dəfə yaz.
Konkret məlumatı olanları seç (razılaşma, müqavilə, təklif, tibbi müayinə, icarə); boş şayiə, reklam, «daha çox oxu» çağırışı SEÇMƏ.
Uyğun paylaşım yoxdursa boş siyahı qaytar.

Hər seçilən üçün Azərbaycan ədəbi dilində qısa xəbər yaz:
- title: 25–110 hərf, içində «transfer» sözü MÜTLƏQ olsun (məsələn «Transfer: Real Madrid Çuameni ilə müqaviləni uzadıb»), sonunda nöqtə, sual, nida yoxdur.
- lead: 60–420 hərf. Mənbəni adı ilə de: «Fabrizio Romano-nun məlumatına görə…».
- body: 1–3 abzas, hər biri 40–800 hərf.
- Təsdiqlənmiş fakt kimi yazma: «bildirilir», «məlumata görə». «Here we go» — «razılaşma əldə olunub».
- Türkcə söz və şəkilçi işlətmə. Nida işarəsi, keçid, kiril hərfi YOXDUR. «bu gün», «dünən», «sabah» kimi sözlər YOXDUR.
- Mətndəki hər rəqəm paylaşımın mətnində olmalıdır. Paylaşımda olmayan fakt əlavə etmə.
- Azərbaycan mövzusu, prezident və dövlət rəhbərlərinin adları YOXDUR.

Yalnız JSON siyahısı qaytar, başqa heç nə:
[{{"id": "<paylaşımın id-si>", "title": "...", "lead": "...", "body": ["..."]}}]

Paylaşımlar:
{items}"""


REELS_PROMPT = """Sən 8ulduz.az saytının qısa video lentinin redaktorusan. Aşağıda X hesablarının videolu paylaşımları var.
Videolar YAZISIZ göstəriləcək (yalnız hesabın adı). Geniş auditoriya üçün ən maraqlı ən çox {n} videonu seç: ustalıq, texnika,
idman anları, təbiət, heyvanlar, elm, kosmos, yemək, səyahət, oyun, kino, musiqi, maraqlı hadisələr. Mövzular MÜXTƏLİF olsun: eyni
mövzudan (məsələn futbol) bir neçə video seçmə. Ən maraqlısını əvvələ yaz. SEÇMƏ: açıq-saçıq və erotik görüntü, qan, meyit, yaralı, edam, işgəncə, hücum və ya partlayış anı, qəza,
heyvana zülm, müharibə və terror səhnələri, reklam, mərc, təhqir, siyasi təbliğat, Azərbaycan mövzusu, mətni olmadan anlaşılmayan
xəbər videoları (müsahibə, bəyanat, studiya söhbəti). Uyğun video yoxdursa boş siyahı qaytar.

Yalnız JSON siyahısı qaytar, başqa heç nə: ["<id>", ...]

Paylaşımlar:
{items}"""


def by_topic(items, key, n):
    """Mövzulara bərabər: hər mövzunun öz sırası qalır, mövzular növbə ilə (idman, təbiət, elm, idman, təbiət …)."""
    groups = {}
    for x in items:
        groups.setdefault(xm.movzu(key(x)), []).append(x)
    out, lists = [], list(groups.values())
    while len(out) < n and any(lists):
        for g in lists:
            if g and len(out) < n:
                out.append(g.pop(0))
    return out


def pick_reels(cands, n):
    """Qısa video üçün id-lər. Gemini seçir (yalnız id, mətn yox); açar yoxdursa və ya cavab gəlmirsə REELS_SAFE hesabları."""
    if not cands:
        return []
    text = ""
    if os.environ.get("GEMINI_API_KEY"):
        items = "\n".join(f"- id {c['id']}, hesab {xm.ADLAR[c['handle']]} (@{c['handle']}): {c['src'][0][:300]}" for c in cands)
        text = ask_gemini(REELS_PROMPT.format(n=n, items=items), os.environ["GEMINI_API_KEY"])
    start, end = text.find("["), text.rfind("]")
    try:
        ids = [str(i) for i in json.loads(text[start:end + 1])] if 0 <= start < end else None
    except ValueError:
        ids = None
    if ids is None:
        print("Qısa video: Gemini seçmədi, yalnız təhlükəsiz hesablar", flush=True)
        ids = [c["id"] for c in cands if c["handle"] in REELS_SAFE or c.get("reel_only")]   # Videolent hesabları seçilmiş vizual hesablardır
    allowed = {c["id"] for c in cands}
    return [i for i in dict.fromkeys(ids) if i in allowed][:n]


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    baku = now.astimezone(BAKU)
    doc = json.loads((ROOT / "oz_x.json").read_text(encoding="utf-8"))
    rows = doc.get("items") or []
    reels = [r for r in doc.get("reels") or [] if isinstance(r, dict)]
    reel_floor = now - datetime.timedelta(days=xm.REELS_DAYS)
    reels = [r for r in reels if (xm._at(r.get("at")) or reel_floor) > reel_floor][-xm.REELS_MAX:]
    floor = baku.date() - datetime.timedelta(days=MAX_AGE_DAYS)
    kept = [r for r in rows if isinstance(r, dict) and str(r.get("date") or "") >= floor.isoformat()]
    known = {str(r.get("id")) for r in kept}
    cands, failed = collect(known, now)
    cands, more = [c for c in cands if not c.get("reel_only")][:MAX_CANDIDATES], cands
    print(f"Namizəd: {len(cands)}; açılmayan hesab: {len(failed)} {failed if failed else ''}", flush=True)
    added, rejected = [], []
    slot = (baku + datetime.timedelta(minutes=5)).strftime("%H:%M")
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")):
        print("GEMINI_API_KEY (və ANTHROPIC_API_KEY) yoxdur: xəbər yazılmır (yalnız X-in oxunuşu yoxlandı).")
    elif not xm.SLOT_FROM <= slot <= LAST_SLOT:
        print(f"Bakı vaxtı {slot}: {xm.SLOT_FROM}–{LAST_SLOT} xaricində xəbər yazılmır (gec yazılan gün bitənədək dərc olunmur).")
    elif cands and baku.hour % 2 and baku.minute < 20:   # saatın yalnız ilk işi (iş 20 dəqiqədən bir); xəbər iki saatdan bir (07, 09 … 21): dərc hissəsi gündə 8 video xəbər buraxır, artığı «gecikdi» olur
        by_id = {c["id"]: c for c in cands}
        for w in write(cands, PER_RUN)[:PER_RUN]:
            c = by_id.get(str(w.get("id")))
            if not c:
                continue
            row = {"id": c["id"], "date": baku.date().isoformat(), "slot": slot, "kind": w.get("kind"),
                   "title": " ".join(str(w.get("title") or "").split()), "lead": " ".join(str(w.get("lead") or "").split()),
                   "body": [" ".join(str(p).split()) for p in (w.get("body") or []) if str(p).strip()],
                   **{k: c[k] for k in ("handle", "post", "video", "poster", "w", "h", "src")}}
            why = xm.check(row)
            (rejected if why else added).append((row, why))
    if TRANSFERS and baku.hour % 2 and baku.minute < 20 and xm.SLOT_FROM <= slot <= LAST_SLOT and (os.environ.get("GEMINI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")):
        pool = [t for t in TRANSFERS if t["id"] not in known][:MAX_CANDIDATES]
        by_t = {t["id"]: t for t in pool}
        for w in (write(pool, TRANSFER_PER_RUN, TRANSFER_PROMPT) if pool else [])[:TRANSFER_PER_RUN]:
            t = by_t.get(str(w.get("id")))
            if not t:
                continue
            row = {"id": t["id"], "date": baku.date().isoformat(), "slot": slot, "kind": "x-transfer",
                   "title": " ".join(str(w.get("title") or "").split()), "lead": " ".join(str(w.get("lead") or "").split()),
                   "body": [" ".join(str(p).split()) for p in (w.get("body") or []) if str(p).strip()],
                   "handle": t["handle"], "post": t["post"], "src": t["src"], **({"poster": t["poster"]} if t.get("poster") else {})}
            why = xm.check(row)
            (rejected if why else added).append((row, why))
    new_reels = []
    if True:   # qısa videolar gecə də (sahib 2026-11-19: «daima təzələnsin»); dərc saatı yoxdur, lent hər açılışda təzəsini göstərir
        taken = {str(r.get("id")) for r in reels} | {r["id"] for r, _ in added}
        pool = by_topic([c for c in more if c["id"] not in taken], lambda c: c["handle"], REELS_ASK)   # Gemini-yə hər mövzudan
        by_id = {c["id"]: c for c in pool}
        for pid in by_topic(pick_reels(pool, REELS_PER_RUN * 3), lambda i: by_id[i]["handle"], REELS_PER_RUN):   # bir işdə mövzu təkrarlanmır
            c = by_id[pid]
            row = {**{k: c[k] for k in ("id", "handle", "post", "video", "poster", "w", "h", "at")}, "src": [c["src"][0][:300]]}   # tam mətn namizəddə yoxlanıb; fayl kiçik qalsın
            why = xm.reel_check(row)
            if why:
                print(f"Qısa video rədd: {pid} — {why}")
            else:
                new_reels.append(row)
                print(f"Qısa video: {pid} @{c['handle']}")
    for row, why in rejected:
        print(f"Rədd: {row['id']} — {why}")
    for row, _ in added:
        print(f"Növbəyə: {row['id']} @{row['handle']} — {row['title']}")
    new = kept + [r for r, _ in added]
    all_reels = reels + new_reels
    if new != rows or all_reels != (doc.get("reels") or []):
        new_doc = {"v": 1, "items": new, **({"reels": all_reels} if all_reels else {})}
        (ROOT / "oz_x.json").write_text(json.dumps(new_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"Namizəd {len(more)}, növbəyə {len(added)}, qısa video {len(new_reels)}, rədd {len(rejected)}, açılmayan hesab {len(failed)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
