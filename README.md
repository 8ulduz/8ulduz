# 8ulduz — son xəbərlər saytı

Statik xəbər aqreqatoru: GitHub Actions hər 5 dəqiqədən bir RSS lentlərini toplayır, sayt isə JSON faylları oxuyur.

## Struktur

- `index.html`, `assets/app.js`, `assets/app.css` — saytın **mənbə kodu** (build addımı yoxdur, birbaşa redaktə olunur).
  Marşrutlar: `#/` (baş səhifə), `#/bolme/<slug>` (bölmə), `#/axtar?q=...` (axtarış).
- `data/news.json` — xəbər lenti (avtomatik yenilənir, yığcam JSON).
- `data/markets.json` — valyuta (AMB, ehtiyat: ExchangeRate-API), Brent/WTI neft və bitcoin (Yahoo Finance, ehtiyat: CNBC/CoinGecko), qızıl/gümüş (gold-api.com).
- `data/social.json` — Prezidentin və birinci xanımın rəsmi YouTube yazıları.
- `data/status.json` — son uğurlu yoxlamanın vaxtı (`checkedAt`). Saytdakı «Yeniləndi» bunu göstərir.
- `data/sources.json` — hər lentin son uğurlu vaxtı, xəbər sayı və son xətası. Saytda: `#/menbeler`.
- `data/og.json` — şəkilli olmayan xəbərlər üçün məqalə səhifəsinin `og:image` / `twitter:image` ünvanı. Hər keçid bir dəfə sorğulanır (vaxt limiti, paralel). Boş nəticə də saxlanır ki, təkrar sorğu olmasın.
- `data/ads.json` — reklam yerləri. `slots` boşdursa baş səhifədə «Reklam yeri» yazısı qalır. Doldurmaq üçün (şəkil ünvanı, keçid, alt mətn):

  ```json
  { "slots": [{ "image": "https://example.com/banner.jpg", "link": "https://example.com", "alt": "Reklam" }] }
  ```

  Bir neçə slot 30 saniyədən bir növbələnir. Şəkil zolağı 54px hündürlükdə kəsilir. Açar və ya ödənişli xidmət tələb olunmur.
- `assets/og-default.png` — paylaşım üçün 1200×630 şəkil. Hər xəbərə ayrı şəkil statik saytda mümkün deyil; `og:image` və Twitter bu şəkli istifadə edir.
- `feed.xml`, `sitemap.xml`, `robots.txt` — updater hər uğurlu yoxlamada yenidən yazır.
- `manifest.webmanifest`, `sw.js`, `assets/icon-*.png` — quraşdırılan PWA. Xəbər JSON-u onlayn olanda heç vaxt köhnə keşdən verilmir.
- `assets/config.js` — GoatCounter sayt kodu (standart: boş, statistika sönülü).
- `updater.py` — RSS + rəsmi səhifələr + bazar + sosial toplayıcı. Mənbə siyahısı: `AZ_FEEDS`, `WORLD_FEEDS`. Yaxın başlıqlı xəbərlər bir kartda birləşir (`alts`).
- `.github/workflows/update.yml` — avtomatik yeniləmə işi.

## Ziyarət statistikası (GoatCounter)

Saytda kuksuz sayğac var, amma **hesab kodu boşdur və heç nə göndərilmir**. Öz hesabınızı yaradın:

1. [goatcounter.com](https://www.goatcounter.com)-da pulsuz hesab açın və sayt kodunu götürün (ünvan `https://KOD.goatcounter.com` formasındadır).
2. `assets/config.js` içində boş sətri öz kodunuzla əvəz edin: `goatcounter: "KOD"`.
3. Dəyişikliyi `main` budağına göndərin. Kodu silsəniz (yenidən `""`), sayğac dayanır.

Hazır kod uydurulmayıb — sahib öz hesabını yaratmalıdır.

Hava məlumatı brauzerdə birbaşa Open-Meteo-dan alınır (açar tələb etmir).

«Ən çox oxunan» bloku hazırda gizlidir: məqalə üzrə oxunma statistikası yoxdur (GoatCounter kodu boşdur və oxunma siyahısı açarsız gəlmir). Əvəzinə baş səhifədə «Günün 5 əsas xəbəri» son 18 saatda ən çox mənbədə çıxan xəbərləri göstərir.

- `data/video.json` — İctimai TV, Xezer TV, ARB 24, Report.az və Trend TV YouTube RSS lentləri. Başlıqlar liderlik süzgəcindən keçir. Saytda video yalnız düyməyə basanda açılır.
- `data/football.json` — TheSportsDB-nin açıq sınaq açarı (`123`, hesab deyil) Premyer Liqa cədvəlini yarımçıq qaytarır, ona görə cədvəl göstərilmir. Son oyun və mövcud futbol xəbərləri, üstəlik [pfl.az](https://pfl.az/) keçidi qalır.
- Namaz vaxtı və hicri tarix brauzerdə [aladhan.com](https://api.aladhan.com) açarsız API-sindən, seçilmiş bölgənin koordinatı ilə alınır.
- Yol/hava zolağı xəbər başlıqlarındakı açar sözlərdən və Open-Meteo-nun günlüq hava kodundan yığılır. Open-Meteo Azərbaycan üçün rəsmi xəbərdarlıq lenti vermir.

## Oxucu

- Seçilmişlər bu cihazda qalır (`localStorage` açarı `8ulduz-saved`). Ulduz kartın küncündədir, siyahı `#/secilmis`.
- «Mənim bölmələrim» (`#/bolmeler`) bölmələrin sırasını və hansının baş səhifədə göründüyünü saxlayır (`8ulduz-sects`). Zuğulba, hero və video/foto blokları bu siyahıdan asılı deyil.
- «Son dəqiqə» lentindəki **Bildiriş** düyməsi brauzer icazəsi istəyir. Səhifə açıq olanda `news.json` hər dəqiqə yoxlanır və yeni son-dəqiqə xəbəri üçün bildiriş çıxır. Push server yoxdur. Brauzer dəstəkləyəndə Periodic Background Sync (`breaking`, ən azı 5 dəqiqə) da qeydiyyatdan keçir; çox brauzer bunu seyrək və ya heç işlətmir.
- Xəbər kartı, hero və siyahılar mənbə ünvanını yeni vərəqdə açır. «+N mənbə» düyməsi həmin xəbərin digər mənbələrini kiçik siyahıda göstərir. Axtarış başlıqla yanaşı xülasənin mətnində də axtarır, amma xülasə səhifədə göstərilmir.
- Telegram kanalı sahibin öz kanalını yaratmasını gözləyir. Düymə hələ `https://t.me/` ünvanına gedir.

## Lokal yoxlama

```bash
python updater.py            # xəbər + bazar
python updater.py --no-markets
python -m http.server 8000   # sonra http://localhost:8000/
```

## Yenilənmə

GitHub planlaşdırılmış işləri çox vaxt 20–30 dəqiqədən bir buraxır. Buna görə hər iş təxminən 55 dəqiqə
açıq qalır və `updater.py`-ni hər 4 dəqiqədən bir işlədib nəticəni push edir. Növbəti iş növbədə gözləyir
və bu iş bitəndə davam edir. `data/status.json` hər uğurlu yoxlamada yenilənir (xəbər mətni dəyişməsə belə).
Sayt JSON-u `?t=` ilə istəyir ki, GitHub Pages-in 10 dəqiqəlik keşi köhnə faylı saxlamasın.

Manual işə salmaq üçün: **Actions → Xəbərləri yenilə → Run workflow**.

Hər dövrədə `data/sources.json`, `feed.xml`, `sitemap.xml` və `robots.txt` də push olunur.

## Saytı dərc etmək

**Settings → Pages → Source: `main` branch** → Save. Ünvan: `https://8ulduz.github.io/8ulduz/`
