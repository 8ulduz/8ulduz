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
REELS_ASK = 110    # Gemini-yə seçim üçün göstərilən ən çox namizəd (9 mövzu; 2026-11-22: xəbər qrupu əlavə olundu)
# Qısa video seçimi Gemini-siz də tam işləyir (sahib 2026-11-23: «Geminidən başqa daha dayanıqlı bir yol tap pulsuz. … Alınmırsa izah
# lazım deyil. 20-80 yaş arası ən çox baxılan videolar olsun. boş boş videolardır indi əksəriyyəti»): ən çox baxılan (heat), X-in
# «possibly_sensitive» nişanı, icma qeydi və mətn süzgəci (candidate), REEL_MIN_VIEWS. Gemini işləyəndə izah və sinif əlavə edir.
# Əvvəlki ehtiyat yolu yalnız «təhlükəsiz» hesabları götürürdü — 2026-11-23 kvota bitəndə lent az baxılan idman
# videoları ilə doldu, xəbər və hadisə gəlmədi.
FX_STATUS = "https://api.fxtwitter.com/{}/status/{}"
REFRESH_PER_RUN = 30   # hər işdə bu qədər növbə sətrinin X sayı yenilənir (sayı olmayan, sonra ən köhnə sayılı): ~1 dəqiqə
MAX_AGE_DAYS = 4
LAST_SLOT = "22:00"   # daha gec yazılan xəbər gün bitənədək dərc olunmağa çatmır və «gecikdi» deyə düşür (2026-11-18 gecəsi 4 xəbər)
GEMINI = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL") or ""   # boşdursa: açarın siyahısındakı ən yeni «flash» (2.5 artıq 404 verir)

# Saxta video (sahib 2026-11-24, X-in «Sizin üçün» lentindən 20 ekran şəkli: 7-si süni intellekt işi və ya doğrulanmamış iddia idi —
# Tramp ilə Putin üz yuyur, liderlər körpüdə, «Avstraliyada canavarlar», «Putinə sui-qəsd», «protez qollu mühafizəçi»). Seçim də,
# izah da bunu bilsin: belə video lentə düşməsin, xəbər kimi yazılmasın.
SAXTA = ("Süni intellektlə hazırlanmış və ya montajla saxtalaşdırılmış videoları SEÇMƏ: tanınmış adamların (liderlər, məşhurlar) real "
         "olmayan səhnələri, «AI», «yapay zeka», «Grok/Sora/Veo» nişanı və ya izahı olan, təbiətdə mümkün olmayan və ya yerə uyğun "
         "olmayan görüntü (məsələn Avstraliyada canavar). Doğrulanmamış sensasiya iddiası olan videoları da SEÇMƏ (sui-qəsd, gizli plan, "
         "«protez», «gizli silah», «məxfi görüntü» kimi; mətnində «@grok doğrula?» kimi şübhə olan paylaşım).")

PROMPT = """Sən 8ulduz.az xəbər saytının redaktorusan. Aşağıda türk və ingilis dilli X hesablarının videolu paylaşımları var.
Onlardan oxucunun ən çox izləmək istəyəcəyi ən çox {n} paylaşımı seç (idman, dünya, elm, maraqlı). Reklam, sponsor, bilet, mağaza,
mərc reklamı və qəza anı olanları SEÇMƏ. Müharibə xəbərlərinin videoları olar (Rusiya–Ukrayna və başqa münaqişələr: cəbhə, dron,
texnika, hava hücumundan müdafiə, dağıntı, təxliyə). Qan, meyit, yaralı, edam, işgəncə, əsir görüntüsü, insanın vurulduğu və ya
öldürüldüyü an olan videoları və terror təbliğatını SEÇMƏ. Şərh, söz atışması, təhqir və siyasi təbliğat olan paylaşımları SEÇMƏ.
{saxta}
Uyğun paylaşım yoxdursa boş siyahı qaytar.

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
{items}""".replace("{saxta}", SAXTA)


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
    # Gemini-siz süzgəc (sahib 2026-11-23): X-in özü ağır və ya açıq-saçıq kadrı «possibly_sensitive» ilə işarələyir; icma qeydi
    # (community note) yanlış məlumat deməkdir; mərc, qumar və ağır kadr xəbərdarlığı mətndən (oz_x.unsafe_text)
    if post.get("possibly_sensitive") or post.get("community_note") or xm.unsafe_text(text):
        return None
    views, likes, reposts = (int(post.get(k) or 0) for k in ("views", "likes", "reposts"))
    return {"id": pid, "handle": handle, "post": f"https://x.com/{handle}/status/{pid}", "video": url, "poster": poster,
            "w": w, "h": h, "src": [text[:xm.SRC_LEN[1]]], "at": datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).isoformat(timespec="seconds"),
            "_views": views, "_likes": likes, "_reposts": reposts, "_score": likes + reposts * 3 + views // 100}


def counts(c, now):
    """Namizədin X sayları növbə sətri üçün: v (baxış), l (bəyənmə), rp (paylaşma), vt (sayların vaxtı)."""
    return {"v": c["_views"], "l": c["_likes"], "rp": c["_reposts"], "vt": now.isoformat(timespec="seconds")}


def heat(c, now):
    """Bu işdə ən çox baxılan: populyarlıq (oz_x.popularity) paylaşımın yaşına bölünür — 2 saatda 200 min baxış 20 saatda 300 mindən
    üstündür. Sahib 2026-11-23: «20-80 yaş arası ən çox baxılan videolar olsun»."""
    hours = max(0.0, (now - datetime.datetime.fromisoformat(c["at"])).total_seconds() / 3600)
    return xm.popularity({"v": c["_views"], "l": c["_likes"], "rp": c["_reposts"]}) / (hours + 2) ** 0.7


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
    # Birinci dərəcəli mənbələr (oz_x.VIDEOLENT_ONDE) və usta işi hesabları (oz_x.USTA_HESABLAR: lentin 40%-i, mənbəyi az) hər işdə;
    # xəbər hesabı olanlar onsuz da hər işdə yoxlanır
    out = list(dict.fromkeys(h for h in (*xm.VIDEOLENT_ONDE, *sorted(xm.USTA_HESABLAR)) if h in xm.VIDEOLENT_HESABLAR))
    per, run = max(1, (VL_PER_RUN - len(out)) // len(groups)), int(now.timestamp()) // 1200   # cəmi VL_PER_RUN-dan çox deyil
    for g in groups:
        g = [h for h in g if h not in out]
        start = (run * per) % len(g)
        out += (g + g)[start:start + min(per, len(g))] if g else []
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


def _gemini_models(key, lite=False):
    """Açarın görə bildiyi, generateContent edən «flash» modelləri, ən yenisi birinci (ad dəyişəndə iş dayanmasın). lite: yalnız «flash-lite»."""
    req = urllib.request.Request(GEMINI + "?pageSize=200", headers={"x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=30) as r:
        models = json.loads(r.read().decode("utf-8")).get("models") or []
    names = [m["name"].split("/", 1)[-1] for m in models if "generateContent" in (m.get("supportedGenerationMethods") or [])
             and "flash" in m.get("name", "") and ("lite" in m.get("name", "")) == lite
             and not re.search(r"image|tts|audio|live|exp|preview|thinking", m.get("name", ""))]
    return sorted(names, key=lambda s: [int(x) if x.isdigit() else 0 for x in re.findall(r"\d+", s)], reverse=True)


def ask_gemini(prompt, key, max_tokens=4000, lite=False):
    """Gemini API (pulsuz səviyyə, açar başlıqda; ünvanda yox). Model: GEMINI_MODEL, alınmasa siyahıdakı ən yeni flash.
    lite: flash modellərin hamısı cavab verməsə «flash-lite» da sınanır (qısa videonun sinfi və izahı üçün; kvotası ayrıdır)."""
    body = json.dumps({"contents": [{"role": "user", "parts": [{"text": prompt}]}],
                       "generationConfig": {"temperature": 0.4, "maxOutputTokens": max_tokens, "responseMimeType": "application/json"}}).encode("utf-8")
    tried, listed = [], _safe_models(key)
    # 2026-11-22: 04:25 UTC-dən model siyahısı HTTP xətası verirdi, siyahı boş qalırdı və Gemini heç çağırılmırdı (videolar izahsız,
    # sinifsiz, X xəbəri yazılmırdı). Siyahı alınmasa son işlək modellər birbaşa sınanır.
    order = list(dict.fromkeys(([GEMINI_MODEL] if GEMINI_MODEL else []) + (listed or list(FALLBACK_MODELS))))[:4]
    if lite:   # 2026-11-23: açarın flash kvotası günün ortasında bitdi (başqa işlər də eyni açarı işlədir), qısa videolar izahsız qaldı
        order += [m for m in (_safe_models(key, lite=True) or list(LITE_MODELS)) if m not in order][:2]
    for model in order:
        doc = None
        for attempt in range(3):   # 503 (yüklüdür) və 429 keçicidir: gözləyib təkrar; 404 (model yoxdur) — növbəti model
            req = urllib.request.Request(f"{GEMINI}/{model}:generateContent", data=body, method="POST",
                                         headers={"x-goog-api-key": key, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=150) as r:
                    doc = json.loads(r.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                why = _why(e)
                tried.append(f"{model}: {e.code} {why}")
                # «exceeded your current quota»: gözləmək kömək etmir, növbəti model (əvvəl hər model 3 dəfə, 90 s gözlənilirdi —
                # 2026-11-23 işi 18 dəqiqəsini belə keçirdi, 30 dəqiqəlik həddə yaxın)
                if e.code not in (429, 500, 503) or e.code == 429 and "quota" in why.lower():
                    break
                time.sleep(15 * (attempt + 1))
            except (TimeoutError, OSError, ValueError) as e:   # cavab gecikdi, bağlantı qırıldı, JSON pozuq: növbəti model
                tried.append(f"{model}: {type(e).__name__}")
                break
        if doc is None:
            continue
        cand = (doc.get("candidates") or [{}])[0]
        parts = (cand.get("content") or {}).get("parts") or []
        end = cand.get("finishReason") or ""   # MAX_TOKENS: cavab həddə dəyib kəsilib (düşünmə də həddən yeyir)
        print(f"Model: {model}" + (f" (cavab sonu: {end})" if end not in ("", "STOP") else ""), flush=True)
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))
    print("Gemini cavab vermədi: " + ", ".join(tried), flush=True)
    return ""


FALLBACK_MODELS = ("gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest")   # 2026-11-21-də işləyən modellər
LITE_MODELS = ("gemini-flash-lite-latest",)   # siyahı alınmasa «lite» üçün


def _why(e):
    """HTTP xətasının qısa səbəbi (Google-un «message» sahəsi; açar başlıqdadır, cavabda olmur)."""
    try:
        msg = json.loads(e.read().decode("utf-8", "replace")).get("error", {}).get("message", "")
    except Exception:
        msg = ""
    return " ".join(str(msg).split())[:160]


def _safe_models(key, lite=False):
    try:
        return _gemini_models(key, lite)
    except urllib.error.HTTPError as e:
        print(f"Model siyahısı alınmadı: HTTP {e.code} {_why(e)}", flush=True)
        return []
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


# Sahib 2026-11-22: «videoların 60%-i həm yeni, həm maraqlı hadisələr, ekstremal hadisələr, işlər, yeniliklər (ən son model avtomobil,
# təqdimat, reklam videoları, avto yarışlar, avto yolsuzluq …), qısa sürətli çəkiliş yemək hazırlama videoları, xəbər mahiyyətli videolar,
# siyasi kontekstdə arxa qapı videoları və Azərbaycan insanlarının maraqla baxdığı digər videolar … Təmir-tadilatdakı videolar bənzəri
# videolar (çox fərqli mövzularda) təşkil etsin. Mənası başa düşülməyən videolar olmasın.» Maraq dairələri: TikTok-un regional rəhbərinə
# görə Azərbaycanda ən populyar kateqoriyalar yumor və əyləncə, təhsil, yemək bişirmə, oyunlar, idman, həyat tərzi və cəmiyyətdir
# (Trend.az, 2024-10); üstəlik avtomobil, Türkiyə futbolu, döyüş idmanı və güləş, Türkiyə müdafiə sənayesi, texnika yenilikləri.
# Özünə qəsd və ölüm anı göstərilmir: belə hadisədən yalnız xilasetmə anı (sahibin «körpüdən atmaq istəyir» nümunəsi).
# Sahib 2026-11-22: «maraqlı videolar x də olur-müharibələrə aid (rusiya ukrayna və sair) x də yayımlanır. deməli olar.» Müharibə
# videoları lentə düşür; qan, meyit, yaralı, insanın vurulduğu an və əsir görüntüsü düşmür (Gemini düşəndə qısa video yazılmır).
REELS_PROMPT = """Sən 8ulduz.az saytının qısa video lentinin redaktorusan. Aşağıda X hesablarının videolu paylaşımları var (baxış sayı ilə).
Azərbaycan oxucusu üçün ən maraqlı ən çox {n} videonu seç və hər birini iki sinifdən birinə ayır:
«hadise» (lentin 60%-i): təzə və maraqlı hadisələr — ekstremal və gözlənilməz anlar (xilasetmə, son anda qurtulma, təhlükəli an,
təbiət hadisəsi, rekord); yeniliklər (ən son avtomobil modeli, təqdimat, reklam çarxı, telefon və texnika, robot, təyyarə, Türkiyə
müdafiə sənayesinin yenilikləri); avtoyarış, drift, yolsuzluq (off-road); sürətli çəkilmiş yemək hazırlanması; xəbər mahiyyətli videolar
(dünyada baş verən hadisənin anı); müharibələrin görüntüləri (Rusiya–Ukrayna və başqa münaqişələr: cəbhə, dron, texnika, hava hücumundan
müdafiə, dağıntı, təxliyə); siyasətin kadr arxası (xarici liderlərin gözlənilməz, maraqlı anları); futbolun, döyüş idmanının və
güləşin yaddaqalan anları; yumor, heyvanlar — Azərbaycan insanlarının maraqla baxdığı nə varsa.
«usta» (lentin 40%-i): «Tamir & Tadilat» kimi — bir işin necə görüldüyü: təmir, tikinti, bərpa, dülgərlik, dəmirçilik, zavodda istehsal,
sənətkarlıq, maşın və mexanizm işi, kənd təsərrüfatı, təmizlik, aşpazın texnikası, faydalı ev ixtiraları; sahələr çox müxtəlif olsun.
ƏN BİRİNCİ birinci dərəcəli maraqlı hadisələr: nadir, heyrətamiz, gözlənilməz anlar; çox baxılan (baxış sayı) və «seçilmiş mənbə»
videoları üstündür. Mövzular MÜXTƏLİF olsun: eyni mövzudan (məsələn futbol) bir neçə video seçmə. Ən maraqlısını əvvələ yaz.
Hər video üçün Azərbaycan dilində bir qısa cümlə izah yaz («c», 20–100 simvol): videoda nə baş verir, kim, harada — yalnız paylaşımın
mətnindən, uydurma yox. İzahla da mənası başa düşülməyən, ancaq danışıqdan ibarət (müsahibə, çıxış, studiya söhbəti), dil bilmədən
anlaşılmayan videoları SEÇMƏ.
SEÇMƏ: açıq-saçıq və erotik görüntü, qan, meyit, yaralı, ölüm və ya özünə qəsd anı, edam, işgəncə, heyvana zülm, insanın vurulduğu
döyüş anı, əsir görüntüsü, terror təbliğatı, mərc və qumar reklamı, təhqir, nifrət, siyasi təbliğat və çağırış, Azərbaycan, Ermənistan və Qarabağ mövzusu, uşağın
təhlükədə olduğu görüntü.
{saxta}
Uyğun video yoxdursa boş siyahı qaytar.

Eyni izahı rus («ru») və ingilis («en») dilində də yaz: eyni məna, 20–100 simvol, tərcümə kimi yox, həmin dilin xəbər üslubunda.

Yalnız JSON siyahısı qaytar, başqa heç nə: [{{"id": "<id>", "s": "hadise" və ya "usta", "c": "<izah>", "ru": "<izah rusca>", "en": "<izah ingiliscə>"}}, ...]

Paylaşımlar:
{items}""".replace("{saxta}", SAXTA)
REEL_META = {}   # id -> {"sinif": "h"/"u", "c": izah, "ru"/"en": rus/ingilis izahı}: pick_reels Gemini-nin cavabından doldurur
DILLER = ("ru", "en")   # sahib 2026-11-24: «videoları tam şəkildə rus və ingilis dillərində də verməliyik» (saytın rus/ingilis oxucusu)
# 2026-11-22: yeni açarla ilk işdə Gemini cavab verdi, amma siyahı oxunmadı — 36 video × izah 4000 token həddinə sığmır
# (Azərbaycan mətni çox token tutur, model düşünməyə də həddən xərcləyir). Videoya geniş hədd; kəsilsə tam elementlər götürülür.
REELS_TOKENS = 16000


def json_list(text):
    """Cavabdakı JSON siyahısı. Cavab yarımçıq kəsilibsə (sonu yoxdur) tam yazılmış {…} elementləri; heç nə yoxdursa None."""
    start, end = text.find("["), text.rfind("]")
    try:
        got = json.loads(text[start:end + 1]) if 0 <= start < end else None
    except ValueError:
        got = None
    if isinstance(got, list) or start < 0:
        return got if isinstance(got, list) else None
    whole = []
    for m in re.finditer(r"\{[^{}]*\}", text[start:]):
        try:
            whole.append(json.loads(m.group(0)))
        except ValueError:
            pass
    return whole or None


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


def izah(c):
    """Gemini-nin izahı: bir sətir, artıq boşluqsuz, ən çox oz_x.IZAH_LEN[1] simvol (söz sərhədində). Boşdursa ""."""
    c = " ".join(str(c or "").split()).strip(" \"'«»")
    if len(c) > xm.IZAH_LEN[1]:
        c = c[:xm.IZAH_LEN[1] - 1].rsplit(" ", 1)[0].rstrip(",;:—- ") + "…"
    return c


def split_reels(ids, handle_of, n):
    """Seçilmiş id-lərdən n video: USTA_PAY qədəri «usta», qalanı «hadise», hər sinifdə mövzular növbə ilə. Bir sinif çatmasa
    yer o birindən dolur (lent onsuz da 3:2 qarışdırır)."""
    cls = lambda i: REEL_META.get(i, {}).get("sinif") or xm.sinif({"handle": handle_of(i)})
    usta, hadise = [i for i in ids if cls(i) == "u"], [i for i in ids if cls(i) != "u"]
    want_u = round(n * xm.USTA_PAY)
    u = by_topic(usta, handle_of, want_u)
    h = by_topic(hadise, handle_of, n - len(u))
    if len(u) + len(h) < n:
        u += by_topic([i for i in usta if i not in u], handle_of, n - len(u) - len(h))
    return h + u


def guess(c):
    """Gemini-siz sinif: usta hesabı və ya mətndə işin necə görüldüyü (oz_x.usta_text) — «u», qalanı «h»."""
    return "u" if xm.sinif(c) == "u" or xm.usta_text(c["src"][0]) else "h"


def pick_reels(cands, n):
    """Qısa video üçün id-lər, cands sırası ilə (ən çox baxılan əvvəl). Gemini işləyirsə uyğun olmayanı çıxarır, sinif və izah verir
    (REEL_META). Açar yoxdursa və ya cavab gəlmirsə seçim Gemini-siz qalır: namizəd süzgəcindən keçənlər, izahsız, sinfi guess-dən."""
    if not cands:
        return []
    text = ""
    if os.environ.get("GEMINI_API_KEY"):
        items = "\n".join(f"- id {c['id']}, hesab {xm.ADLAR[c['handle']]} (@{c['handle']}{', seçilmiş mənbə' if xm.onde(c['handle']) else ''}), "
                          f"baxış {c.get('_views', 0)}: {c['src'][0][:300]}" for c in cands)
        text = ask_gemini(REELS_PROMPT.format(n=n, items=items), os.environ["GEMINI_API_KEY"], REELS_TOKENS, lite=True)
    got = json_list(text)
    ids = None
    if isinstance(got, list):
        ids = []
        for g in got:   # yeni cavab: {"id", "s", "c", "ru", "en"}; köhnə cavab: yalnız id
            if isinstance(g, dict):
                pid = str(g.get("id") or "")
                meta = {"sinif": "u" if str(g.get("s") or "").strip().lower() == "usta" else "h"}
                c = izah(g.get("c"))
                if c:
                    meta["c"] = c
                for k in DILLER:
                    t = izah(g.get(k))
                    if t:
                        meta[k] = t
                REEL_META[pid] = meta
                ids.append(pid)
            elif isinstance(g, (str, int)):
                ids.append(str(g))
    if ids is None:
        told = f" (cavab oxunmadı: {len(text)} simvol, sonu {' '.join(text[-80:].split())!r})" if text else ""
        print(f"Qısa video: Gemini seçmədi{told} — Gemini-siz: ən çox baxılanlar, izahsız", flush=True)
        for c in cands:
            REEL_META[c["id"]] = {"sinif": guess(c)}
        return [c["id"] for c in cands][:n]
    chosen = set(ids)
    return [c["id"] for c in cands if c["id"] in chosen][:n]


def refresh(reels, now, fetch=None):
    """Növbə sətirlərinin X saylarını yeniləyir (ən çox baxılan sırası düzgün qalsın): əvvəl sayı olmayanlar, sonra sayı ən köhnə
    olanlar, son 2 günün sətirləri, ən çox REFRESH_PER_RUN. X sonradan «possibly_sensitive» və ya icma qeydi qoyubsa sətir silinir."""
    fetch = fetch or fetch_json
    floor = now - datetime.timedelta(days=2)
    todo = sorted((r for r in reels if (xm._at(r.get("at")) or floor) > floor), key=lambda r: ("v" in r, r.get("vt") or ""))[:REFRESH_PER_RUN]
    drop, done = set(), 0
    for r in todo:
        try:
            t = (fetch(FX_STATUS.format(r["handle"], r["id"])) or {}).get("tweet") or {}
        except Exception:   # bir sətir alınmasa digərləri
            t = {}
        if t.get("possibly_sensitive") or t.get("community_note"):
            drop.add(r["id"])
        elif isinstance(t.get("views"), int):
            r.update(v=t["views"], l=int(t.get("likes") or 0), rp=int(t.get("retweets") or 0), vt=now.isoformat(timespec="seconds"))
            done += 1
        time.sleep(2)   # FxTwitter tez soruşanda 404 verir
    if todo:
        print(f"Qısa video sayları: {done}/{len(todo)} yeniləndi, {len(drop)} sətir X-in nişanı ilə silindi", flush=True)
    return [r for r in reels if r.get("id") not in drop]


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    baku = now.astimezone(BAKU)
    doc = json.loads((ROOT / "oz_x.json").read_text(encoding="utf-8"))
    rows = doc.get("items") or []
    # son həftənin videoları; usta işi bütün həftə qalır (oz_x.keep_reels)
    reels = xm.keep_reels(doc.get("reels") or [], now)
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
    # qısa videolar gecə də (sahib 2026-11-19: «daima təzələnsin»); dərc saatı yoxdur, lent hər açılışda təzəsini göstərir
    # növbədəki videoların X sayları: bu işdə yenə görünən paylaşımlar namizəddən (sorğusuz), qalanı refresh ilə
    queued = {str(r.get("id")): r for r in reels}
    for c in more:
        if c["id"] in queued:
            queued[c["id"]].update(counts(c, now))
    reels = refresh(reels, now)
    taken = {str(r.get("id")) for r in reels} | {r["id"] for r, _ in added}
    # eyni video (X media nömrəsi) başqa paylaşımda gəlirsə namizəd deyil: 2026-11-23 lentində 32 video iki dəfə idi
    media = {xm.video_key(r.get("video")) for r in reels}
    first = []
    # ən çox baxılan əvvəl (heat); birinci dərəcəli mənbəyə 1,5 qat üstünlük; REEL_MIN_VIEWS-dan az baxılan «boş»dur; köhnə klipin
    # təzə paylaşımı hadisə deyil (oz_x.stale_event, sinif Gemini-siz guess-dən)
    for c in sorted(more, key=lambda c: -heat(c, now) * (1.5 if xm.onde(c["handle"]) else 1)):
        cls = {"video": c["video"], "sinif": guess(c), "at": c["at"], **counts(c, now)}
        if c["id"] in taken or xm.empty(cls) or xm.stale_event(cls, now) or xm.video_key(c["video"]) in media:
            continue
        media.add(xm.video_key(c["video"]))
        first.append(c)
    pool = by_topic(first, lambda c: c["handle"], REELS_ASK)   # hər mövzudan, mövzunun içində ən çox baxılan əvvəl
    by_id = {c["id"]: c for c in pool}
    picked = [i for i in pick_reels(pool, REELS_PER_RUN * 3)
              if not xm.stale_event({"video": by_id[i]["video"], "handle": by_id[i]["handle"], **REEL_META.get(i, {})}, now)]
    # 60% hadisə, 40% usta işi (sahib 2026-11-22); bir işdə hər sinifdə mövzu təkrarlanmır
    for pid in split_reels(picked, lambda i: by_id[i]["handle"], REELS_PER_RUN):
        c = by_id[pid]
        meta = REEL_META.get(pid, {})
        row = {**{k: c[k] for k in ("id", "handle", "post", "video", "poster", "w", "h", "at")}, "src": [c["src"][0][:300]],   # tam mətn namizəddə yoxlanıb; fayl kiçik qalsın
               "sinif": meta.get("sinif") or guess(c), **counts(c, now), **{k: meta[k] for k in ("c", *DILLER) if meta.get(k)}}
        for k in ("c", *DILLER):
            if k in row and xm.izah_check(row[k]) and not xm.forbidden_topic(row[k]):
                print(f"Qısa video: {pid} {k} izahsız — {xm.izah_check(row.pop(k))}")   # biçim xətası: video qalır, izah düşür (izah məcburi deyil)
        why = xm.reel_check(row)   # izahda Azərbaycan/Ermənistan mövzusu varsa video düşür
        if why:
            print(f"Qısa video rədd: {pid} — {why}")
        else:
            new_reels.append(row)
            print(f"Qısa video: {pid} @{c['handle']} — {c['_views']} baxış")
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
