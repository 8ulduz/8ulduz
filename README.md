# 8ulduz — son xəbərlər saytı

Statik xəbər aqreqatoru: GitHub Actions hər 5 dəqiqədən bir RSS lentlərini toplayır, sayt isə JSON faylları oxuyur.

## Struktur

- `index.html`, `assets/app.js`, `assets/app.css` — saytın **mənbə kodu** (build addımı yoxdur, birbaşa redaktə olunur).
  Marşrutlar: `#/` (baş səhifə), `#/bolme/<slug>` (bölmə), `#/axtar?q=...` (axtarış), `#/tixac` (tıxac xəritəsi).
- `data/news.json` — xəbər lenti (avtomatik yenilənir, yığcam JSON).
- `data/markets.json` — valyuta (AMB, ehtiyat: ExchangeRate-API), Brent/WTI neft və bitcoin (Yahoo Finance, ehtiyat: CNBC/CoinGecko), qızıl/gümüş (gold-api.com).
- `data/social.json` — Prezidentin və birinci xanımın rəsmi YouTube yazıları.
- `data/status.json` — son uğurlu yoxlamanın vaxtı (`checkedAt`). Saytdakı «Yeniləndi» bunu göstərir.
- `data/sources.json` — hər lentin son uğurlu vaxtı, xəbər sayı və son xətası. Saytda: `#/menbeler`.
- `data/og.json` — şəkilli olmayan xəbərlər üçün məqalə səhifəsinin `og:image` / `twitter:image` ünvanı. Hər keçid bir dəfə sorğulanır (vaxt limiti, paralel). Boş nəticə də saxlanır ki, təkrar sorğu olmasın.
- `data/ads.json` — reklam yerləri. `slots` boşdursa baş səhifədə heç nə göstərilmir. Doldurmaq üçün (şəkil ünvanı, keçid, alt mətn):

  ```json
  { "slots": [{ "image": "https://example.com/banner.jpg", "link": "https://example.com", "alt": "Reklam" }] }
  ```

  Bir neçə slot 30 saniyədən bir növbələnir. Şəkil zolağı 54px hündürlükdə kəsilir. Açar və ya ödənişli xidmət tələb olunmur.
- `assets/og-default.png` — paylaşım üçün 1200×630 şəkil. Hər xəbərə ayrı şəkil statik saytda mümkün deyil; `og:image` və Twitter bu şəkli istifadə edir.
- `feed.xml`, `sitemap.xml`, `robots.txt` — updater hər uğurlu yoxlamada yenidən yazır.
- `bolme/<slug>/index.html` — hər bölmə üçün statik səhifə (updater yazır, `SECTIONS`). Axtarış sistemləri üçün həqiqi ünvandır: başlıq, təsvir, son 30 azərbaycandilli xəbərin keçidi. Brauzerdə açılanda resurslar nisbi yolla yüklənir, sonra ünvan `#/bolme/<slug>`-a keçir və adi tətbiq işləyir. Sitemap-da hamısı var.
- `manifest.webmanifest`, `sw.js`, `assets/icon-*.png` — quraşdırılan PWA. Xəbər JSON-u onlayn olanda heç vaxt köhnə keşdən verilmir.
- `assets/config.js` — GoatCounter sayt kodu (standart: boş, statistika sönülü), Telegram kanalı (`telegram`, boş olanda «kanala qoşulun» bloku görünmür) və əlaqə e-poçtu (`contact`, «Haqqımızda» səhifəsində).
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
- `data/sports.json` — dünya liqaları: İngiltərə, İspaniya, İtaliya, Almaniya, Fransa, Türkiyə, Çempionlar Liqası və NBA (Şərq/Qərb) cədvəlləri ESPN-in açıq, sənədsiz cədvəl API-sindən (`ESPN_LEAGUES`, `parse_espn`), 30 dəqiqədən bir. Avroliqa ESPN-də boş gəldiyi üçün yoxdur. Futbol blokunda Azərbaycan liqalarından sonra çiplərlə seçilir.
- `data/football.json` — Premyer Liqa, I Liqa, II Liqa, Azərbaycan Kuboku və Əvəzedicilər Liqası (`leagues`, `PFL_PROJECTS`; üst səviyyə Premyer Liqadır): turnir cədvəli, son turun nəticələri, növbəti turun təqvimi və bombardirlər. 10 dəqiqədən bir yenilənir. Mənbə pfl.az saytının öz tətbiqinin istifadə etdiyi açıq JSON API-dir (`https://pfl.az/api/v1`, açar tələb etmir; `parse_pfl`). Alınmayanda köhnə fayl `stale` nişanı ilə qalır; cədvəl heç olmayanda blok göstərilmir. Baş səhifədə komanda kartları (karusel) və sağda Nəticələr / Təqvim / Cədvəl / Bombardirlər paneli var.
- Namaz vaxtı və hicri tarix brauzerdə [aladhan.com](https://api.aladhan.com) açarsız API-sindən alınır (`method=13`, şəhərin eni və uzunluğu). Şəhər siyahısı hava bölgələri ilə eynidir. Seçim bu cihazda qalır (`8ulduz-pray-city`).
- Yol/hava zolağı xəbər başlıqlarındakı açar sözlərdən və Open-Meteo-nun günlüq hava kodundan yığılır. Open-Meteo Azərbaycan üçün rəsmi xəbərdarlıq lenti vermir.
- `#/tixac` Bakının canlı tıxac xəritəsini Waze-in açarsız iframe ünvanından göstərir (`https://embed.waze.com/iframe?zoom=&lat=&lon=`). Xəritə yalnız «Xəritəni aç» düyməsindən sonra yüklənir. Tam ekran keçidi `waze.com/live-map`. Yol xəbərləri yeni lent əlavə etmədən mövcud xəbərlərdən süzülür: `bna.az` / `bna.gov.az` açılmır (səhifə tikinti vəziyyətindədir), DYP-nin (`dyp.gov.az`) və AYNA-nın (`ayna.gov.az/az/news`) işlək RSS-i yoxdur. İş günü Bakı vaxtı ilə 08:00–10:00 və 17:00–20:00 «Pik saat» nişanı çıxır.

## Oxucu

- Dil süzgəci standart olaraq «Azərbaycan dilində»dir; «Hamısı» və ya başqa dil seçimi bu cihazda qalır (`8ulduz-lang`).
- Baş səhifədəki hero (böyük kart + 8 yan kart) ən yeni xəbərləri yox, son 18 saatda ən çox mənbədə çıxan xəbərləri göstərir (`heroPick`; az olanda pəncərə 48 saata genişlənir). Prezident xəbərləri Zuğulba blokunda olduğu üçün hero-ya düşmür. Ayrıca «Günün 5 əsas xəbəri» bloku buna görə çıxarılıb.
- «Son dəqiqə» nişanı və bildiriş yalnız son 15 dəqiqənin xəbərləri üçündür və yalnız lentdə və hero-da görünür; «Son dəqiqə» bölməsi isə son bir saatı əhatə edir.
- Tıxac keçidi bir yerdədir: masaüstündə naviqasiyada, dar ekranda alt paneldə. Qırmızı nöqtə yalnız pik saatda və ya təzə yol hadisəsində çıxır.
- Dar ekranda başlıq iki sətirdir: loqo + axtarış, altında üfüqi sürüşən bölmələr (aktiv bölmə görünən yerə gətirilir).

- Seçilmişlər bu cihazda qalır (`localStorage` açarı `8ulduz-saved`). Ulduz kartın küncündədir, siyahı `#/secilmis`.
- «Mənim bölmələrim» (`#/bolmeler`) bölmələrin sırasını və hansının baş səhifədə göründüyünü saxlayır (`8ulduz-sects`). Zuğulba, hero və video/foto blokları bu siyahıdan asılı deyil.
- «Son dəqiqə» lentindəki **Bildiriş** düyməsi brauzer icazəsi istəyir. Səhifə açıq olanda `news.json` hər dəqiqə yoxlanır və yeni son-dəqiqə xəbəri üçün bildiriş çıxır. Push server yoxdur. Brauzer dəstəkləyəndə Periodic Background Sync (`breaking`, ən azı 5 dəqiqə) da qeydiyyatdan keçir; çox brauzer bunu seyrək və ya heç işlətmir.
- Xəbər kartı, hero və siyahılar mənbə ünvanını yeni vərəqdə açır. «+N mənbə» düyməsi həmin xəbərin digər mənbələrini kiçik siyahıda göstərir. Axtarış başlıqla yanaşı xülasənin mətnində də axtarır, amma xülasə səhifədə göstərilmir.
- Telegram kanalı: `assets/config.js`-də `telegram` boş olduğu üçün «kanala qoşulun» bloku göstərilmir; kanal yarananda ünvanı yazın.
- Kartlarda başlığın altında xülasənin ilk iki sətri görünür (dar ekranda yalnız şəkilsiz kartlarda). Başlıqdakı xam ünvanlar (Telegram lentləri) həm updater-də, həm brauzerdə kəsilir.
- Baş səhifə hər dəqiqə yalnız `data/status.json`-u (151 bayt) yoxlayır; `news.json` yalnız `checkedAt` dəyişəndə çəkilir. Lentdəki xəbərlərin demək olar ki, hamısı son 24 saatındır, ona görə faylı arxivə bölməyə ehtiyac yoxdur.
- «Haqqımızda» (`#/haqqinda`): sayt nədir, mənbələr, redaksiya prinsipləri, məxfilik, əlaqə. Altlıqdan keçid var.
- Valyuta kartlarında AMB rəsmi məzənnəsi alınmayanda «bazar» nişanı və qeyd çıxır (ehtiyat: ExchangeRate-API). Updater AMB bülletenini hər gün üçün iki dəfə yoxlayır, alınmayan günü keçir.
- «Texnologiya» bölməsi: elm, texnologiya və süni intellekt xəbərləri (əvvəl «Həyat»a düşürdü).

## Lokal yoxlama

Şəbəkəyə müraciət etmədən xəta ssenarilərini yoxlamaq üçün Python 3.12 və Node.js 22 ilə:

```bash
python -m unittest discover -s tests -v
node --test tests/browser-logic.test.cjs
```

Bu yoxlamalar pull request-lərdə də avtomatik işləyir. Mənbələr tam dayananda əvvəlki xəbər
lenti və son uğurlu `checkedAt` saxlanılır; `attemptedAt` son cəhdi, `ok` isə nəticəni göstərir.
Sayt oflayn və ya 15 dəqiqədən çox köhnəlmiş xəbər lentini ayrıca işarələyir.
Dar ekranda xronikanın ilk dörd xəbəri sabit görünür; tam siyahı «Hamısı» keçidindədir.

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
