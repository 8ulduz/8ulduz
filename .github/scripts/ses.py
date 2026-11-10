#!/usr/bin/env python3
"""«Dinlə»: xəbərin tam mətni təbii Azərbaycan səsi ilə, hər telefonda, pulsuz.

Sahib, 2026-11-07: «xəbəri saytından tam oxusun»; «Edge daxilindəki səsini kənardan işlət»; «müəllif hüququ mənlikdir».
Əsas Azərbaycan xəbərlərinin tam mətni mənbə səhifəsindən götürülür (reader_content.extract_article: ödənişli xəbər
götürülmür), Microsoft Edge-in «Ucadan oxu» səsi (az-AZ-BabekNeural, edge-tts paketi) ilə mp3 olur və ayrıca 8ulduz/ses
reposuna yazılır. Mətnin özü heç yerdə yayımlanmır, yalnız səs; səs mənbənin adı ilə başlayır.
Sayt reposuna (8ulduz/8ulduz) heç nə yazılmır: səs faylları böyükdür, sayt reposunu və Pages-i ağırlaşdırmasın. Ses reposu
tarixçəsizdir (hər yazı valideynsiz commit), lentdən çıxmış və KEEP_H saatdan köhnə səs silinir; repo şişsə silinib yenidən
yaradıla bilər, sayta təsiri yoxdur. Edge xidməti Microsoft-un rəsmi açıq xidməti deyil: bağlansa iş səhv verir, sayt isə
cihazın öz səsi ilə oxumağa davam edir (assets/dinle.js). Qırmızı xətt 2: xəbərlər content_policy.enforce-dan keçir.

İşlədilmə (8ulduz/ses reposunun iş axını): python ses.py <ses-klonu>
"""
import asyncio
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
import content_policy  # noqa: E402
from reader_content import extract_article  # noqa: E402

SITE = "https://8ulduz.az/"
VOICE = "az-AZ-BabekNeural"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 8ulduz-bot"
# Bütün Azərbaycan xəbərləri (sahib, 2026-11-08: «ancaq başlığı oxudu»): gündə ~750, ən yenisi birinci.
# Bir dövrədə 6 xəbər (~45 s), sonra dərhal yazılır: təzə xəbər 40-lıq dəstənin bitməsini (~5 dəq) gözləmir («anında»).
PER_RUN, MAX_AGE_H, KEEP_H, MAX_FILES, MAX_CHARS = 6, 26, 26, 1000, 5000
ID_RE = re.compile(r"^[0-9a-f]{16}$")
# Mətn təmizliyi (2026-11-08, reader_content.tidy): bundan əvvəl yazılmış səslər yenidən səslənir — təzə xəbər həmişə birinci.
CLEAN_AT = datetime.datetime(2026, 11, 8, 9, 0, tzinfo=datetime.timezone.utc).timestamp()
# Mətni əvvəl tapılmayan mənbələr: bu vaxtdan əvvəl yazılmış səsləri yenidən səslənir (yalnız həmin saytın xəbərləri, hamısı yox).
# Oxu24.com: mətn news-detail blokunda idi, səs yalnız başlıq idi (sahib, 2026-11-09).
REDO_HOSTS = {"oxu24.com": datetime.datetime(2026, 11, 9, 18, 30, tzinfo=datetime.timezone.utc).timestamp()}
# Oxunmayan nişanlar (sahib, 2026-11-10: «ortada video sözü keçir — lazımsız yerlər oxunmasın»): başlığın sonundakı
# «- Video», «(FOTO)», «[VİDEO]», əvvəlindəki «VİDEO:», mətndə təkcə «Video.» cümləsi və «Foto: APA» imzası.
# Cümlənin içindəki adi söz («videoda görünür») qalır. Bu vaxtdan əvvəl yazılmış nişanlı səslər yenidən səslənir.
MARK = r"(?:foto\s*/\s*v[iİIı]deo|v[iİIı]deo\s*/\s*foto|foto\s*\+\s*v[iİIı]deo|v[iİIı]deo(?:lar|görüntü)?|foto(?:lar|şəkil(?:lər)?|reportaj)?|şəkillər|yen[iİ]l[əƏ]n[iİ]b|yen[iİ]l[əƏ]nd[iİ]|eksklüz[iİ]v|müsah[iİ]bə)"
_TAIL = re.compile(r"\s*(?:[-–—|:+]\s*)?[(\[]?\s*" + MARK + r"\s*[)\]]?\s*$", re.I)
_PAREN = re.compile(r"\s*[(\[]\s*" + MARK + r"(?:\s*[,+/]\s*" + MARK + r")*\s*[)\]]", re.I)
_HEAD = re.compile(r"^\s*" + MARK + r"\s*[:|–—-]\s*", re.I)
_ALONE = re.compile(r"(?:^|(?<=[.!?…]\s))\s*" + MARK + r"\s*[.!:]?(?=\s|$)", re.I)
_CREDIT = re.compile(r"(?:^|(?<=[.!?…]\s))(?:foto|fotolar|fotoşəkil|şəkil|şəkillər|v[iİIı]deo|mənbə)\s*:\s*[^!?]{1,40}?(?:[.!?](?=\s|$)|$)", re.I)
MARK_AT = datetime.datetime(2026, 11, 10, 16, 0, tzinfo=datetime.timezone.utc).timestamp()


def spoken_title(title):
    """Başlıq səs üçün: «- Video», «(FOTO)», «VİDEO:» nişanları atılır, qalan söz dəyişmir."""
    t = re.sub(r"\s+", " ", title or "").strip()
    for _ in range(3):
        n = _PAREN.sub("", _HEAD.sub("", _TAIL.sub("", t))).strip()
        if n == t or not n:
            break
        t = n
    return t


def spoken_text(text):
    """Mətn səs üçün: təkcə nişandan ibarət cümlələr və şəkil/video imzaları atılır."""
    t = re.sub(r"\s+", " ", text or "").strip()
    t = _ALONE.sub(" ", _CREDIT.sub(" ", _PAREN.sub("", t)))
    return re.sub(r"\s+", " ", t).strip()


def marker_redo(have, born, feed, at=None):
    """Başlığında nişan olan və səsi düzəlişdən əvvəl yazılmış xəbərlər: yenidən səslənir."""
    at = MARK_AT if at is None else at
    return {a.get("id") for a in feed if a.get("id") in have and born.get(a.get("id"), 0) < at
            and spoken_title(a.get("title", "")) != re.sub(r"\s+", " ", a.get("title", "")).strip()}


def host_redo(have, born, feed, hosts=REDO_HOSTS):
    """Səsi yenidən yazılacaq xəbərlər: mənbəsi REDO_HOSTS-dadır və səsi o vaxtdan əvvəl yazılıb."""
    out = set()
    for a in feed:
        i, h = a.get("id"), re.sub(r"^www\.", "", urllib.parse.urlparse(str(a.get("sourceUrl", ""))).hostname or "")
        if i in have and h in hosts and born.get(i, 0) < hosts[h]:
            out.add(i)
    return out


def parse_time(s):
    try:
        t = datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return None


def pick(articles, have, now):
    """Səslənəcək xəbərlər: Azərbaycan dilində, son 26 saat, ən yenisi birinci (təzə xəbərin səsi tez hazır olsun)."""
    rows = []
    for a in articles:
        t = parse_time(a.get("publishedAt"))
        if (ID_RE.match(str(a.get("id", ""))) and (a.get("lang") or "az") == "az" and a.get("title") and a["id"] not in have
                and str(a.get("sourceUrl", "")).startswith("https://") and t and -600 <= (now - t).total_seconds() < MAX_AGE_H * 3600):
            rows.append(a)
    rows, _ = content_policy.enforce(rows)
    return sorted(rows, key=lambda a: (-parse_time(a["publishedAt"]).timestamp(), -len(a.get("alts") or [])))


def evict(have, live, pub, born, t):
    """Hədd (MAX_FILES) dolanda yer açılacaq səs: əvvəl lentdən çıxmış xəbərin (ən köhnəsi), sonra ən əvvəl dərc olunmuş
    xəbərin səsi. Yalnız yeni xəbərdən (t) köhnədirsə; yoxsa None — təzə xəbər köhnə xəbər üçün silinmir.
    2026-11-08: hədd dolub səs 8 saat dayanmışdı (köhnə səs yalnız 26 saatdan sonra silinirdi)."""
    if not have:
        return None
    rank = lambda i: (i in live, pub.get(i, born.get(i, 0)))
    old = min(have, key=rank)
    return old if rank(old) < (True, t) else None


def stale(have, born, cutoff=CLEAN_AT):
    """Təmizlikdən əvvəl yazılmış səslər: yenidən səslənəcək (köhnə fayl yenisi hazır olana qədər qalır)."""
    return {i for i in have if born.get(i, 0) < cutoff}


def clip(text, limit=MAX_CHARS):
    """Çox uzun mətn cümlə sərhədində kəsilir."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[: end + 1] if end > limit // 2 else cut


def script_of(a, body):
    """Oxunan mətn: başlıq, mənbə, tam mətn (alınmayıbsa saytdakı xülasə)."""
    title = re.sub(r"[.!?…\s]+$", "", spoken_title(a.get("title", "")))
    lead = f"{title}. {a['source']} xəbər verir." if a.get("source") else f"{title}."
    rest = body or re.sub(r"<[^>]+>", " ", a.get("summary") or "")
    rest = clip(spoken_text(rest))
    if rest.startswith(title):
        rest = rest[len(title):].lstrip(" .")
    return f"{lead} {rest}".strip()


def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/json,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(3_000_000).decode("utf-8", errors="replace")


LIVE = "https://raw.githubusercontent.com/8ulduz/8ulduz/live/m/"


def live_rows(now):
    """Saytın dəqiqəlik canlı lenti (live budağı, app.js liveDirect ilə eyni yol): yeni xəbər 10 dəqiqəlik əsas lenti gözləmir.
    Sahib, 2026-11-08: «anında düşən xəbəri mənbədən oxusun»."""
    slot = int(now.timestamp() - 45) // 60
    for minute in (slot, slot - 1, slot - 2):
        try:
            return json.loads(fetch(f"{LIVE}{minute}/latest.az.json", 15)).get("articles") or []
        except Exception:
            continue
    return []


def merged(feed, live):
    """Canlı lentin xəbərləri əsas lentə qatılır (eyni id bir dəfə)."""
    seen = {a.get("id") for a in feed}
    return [a for a in live if a.get("id") not in seen] + feed


def git(d, *args, data=None):
    return subprocess.run(["git", "-C", d, *args], input=data, capture_output=True, check=True).stdout.decode().strip()


async def speak(text, path):
    import edge_tts  # yalnız iş axınında quraşdırılır
    raw = path + ".raw.mp3"
    await edge_tts.Communicate(text, VOICE).save(raw)
    # 24 kbit/s mono: nitq üçün kifayətdir, fayl ~4 dəfə kiçik (telefonun interneti az yeyilir)
    if shutil.which("ffmpeg"):
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", raw, "-ac", "1", "-ar", "16000", "-b:a", "24k", path], check=True)
        os.remove(raw)
    else:  # ffmpeg yoxdursa Edge-in öz faylı (48 kbit/s)
        os.replace(raw, path)
    if os.path.getsize(path) < 3000:
        raise RuntimeError("boş səs")


def main(d):
    now = datetime.datetime.now(datetime.timezone.utc)
    feed = json.loads(fetch(f"{SITE}data/news.json?t={int(now.timestamp())}", 30)).get("articles") or []
    if len(feed) < 50:
        print(f"ses: lent alınmadı ({len(feed)})")
        return
    feed = merged(feed, live_rows(now))
    have, other, index = {}, [], {}
    try:
        for line in git(d, "ls-tree", "HEAD").splitlines():
            meta, name = line.split("\t", 1)
            m = re.fullmatch(r"([0-9a-f]{16})\.mp3", name)
            if m:
                have[m.group(1)] = meta.split()[2]
            elif name == "index.json":
                index = json.loads(git(d, "cat-file", "blob", meta.split()[2]))
            else:
                other.append(line)  # .github/ (iş axınının özü), README
    except subprocess.CalledProcessError:
        pass
    born = dict(index.get("t") or {})
    live = {a.get("id") for a in feed}
    dropped = 0
    for i in list(have):
        if i not in live and now.timestamp() - born.get(i, 0) > KEEP_H * 3600:
            del have[i]
            dropped += 1
    made = 0
    pub = {a.get("id"): (parse_time(a.get("publishedAt")) or now).timestamp() for a in feed}
    redo = stale(have, born) | host_redo(have, born, feed) | marker_redo(have, born, feed)
    with tempfile.TemporaryDirectory() as tmp:
        for a in pick(feed, {i: s for i, s in have.items() if i not in redo}, now):
            if made >= PER_RUN:
                break
            full = a["id"] not in have and len(have) >= MAX_FILES
            old = evict(have, live, pub, born, parse_time(a["publishedAt"]).timestamp()) if full else None
            if full and not old:
                continue
            try:
                body = extract_article(fetch(a["sourceUrl"]))
            except Exception:
                body = ""
            path = os.path.join(tmp, a["id"] + ".mp3")
            try:
                asyncio.run(speak(script_of(a, body), path))
            except Exception as e:  # Edge xidməti cavab vermirsə bu dövrə dayanır
                print("ses:", a["id"], type(e).__name__, str(e)[:120])
                break
            if old:
                del have[old]
                dropped += 1
            have[a["id"]] = git(d, "hash-object", "-w", path)
            born[a["id"]] = int(now.timestamp())
            made += 1
    if not made and not dropped:
        print("ses: yeni səs yoxdur")
        return
    born = {i: t for i, t in born.items() if i in have}
    idx = json.dumps({"at": int(now.timestamp()), "ids": sorted(have), "t": born}, separators=(",", ":")).encode()
    rows = other + [f"100644 blob {sha}\t{i}.mp3" for i, sha in sorted(have.items())]
    rows.append(f"100644 blob {git(d, 'hash-object', '-w', '--stdin', data=idx)}\tindex.json")
    tree = git(d, "mktree", "--missing", data=("\n".join(rows) + "\n").encode())
    commit = git(d, "-c", "user.name=8ulduz-bot", "-c", "user.email=bot@8ulduz.az", "commit-tree", tree, "-m", "Xəbər səsləri")
    git(d, "push", "-q", "--force", "origin", f"{commit}:refs/heads/main")
    print(f"ses: {made} yeni səs, {dropped} köhnə silindi, cəmi {len(have)}")


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".ses"))
