# 8ulduz — son xəbərlər saytı

## Mənbə keçid sayları və sürücü rejimi

Mənbə adının yanında `gün/həftə/ay/il` ümumi keçid sayları göstərilir. `assets/config.js`-dəki GoatCounter hesabında Settings → **Allow adding visitor counts on your website** aktiv olmalıdır; hesabın saat qurşağını **Asia/Baku** seçin. Sayım `source-click-MƏNBƏ` hadisələri ilə yalnız istehsal domenində aparılır, fərdi istifadəçi identifikatoru yaradılmır. Hər klik ayrıca sayılır. Başlanğıcdan əvvəlki statistika bərpa edilmir; xidmət rəqəmləri 4 saata qədər keşləyə bilər. `—` rəqəmin əlçatan olmadığını göstərir.

> Hazırda sürücü rejimi və mikrofonlu «Köməkçi» söndürülüb (`assets/config.js`: `driver`, `assistant`). Kod yerindədir; `true` yazanda geri qayıdır.

**Sürücü rejimi** aktiv olanda Azərbaycan dilində xəbər keçidi mənbəni yeni vərəqdə açır, bu səhifə isə mənbədən ayrıca alınmış mətni səsləndirir. Məqalə mətni səhifədə göstərilmir. `reader_content.py` updater tərəfindən çağırılıb `data/reader.json` audio mətn keşini yaradır; bir dövrədə ən çox 24 yeni məqalə işlənir. İlk yayımda keş boş ola bilər. Bloklanmış və ya tanınmayan mənbələr üçün səsləndirmə edilmir. Azərbaycan Web Speech səsi olmayan cihazda ayrıca Azərbaycan TTS provayderi lazımdır; API açarları brauzerə yazılmamalıdır. Mobil brauzerlər başqa vərəqə keçəndə səsi dayandıra bilər.

Yoxlama hesabatı: [29 oktyabr 2026 oxucu auditi](docs/reader-audit-2026-10-29.md).

Statik xəbər aqreqatoru: GitHub Actions hər 5 dəqiqədən bir RSS lentlərini toplayır, sayt isə JSON faylları oxuyur.

## Struktur

- `index.html`, `assets/app.js`, `assets/app.css` — saytın **mənbə kodu** (build addımı yoxdur, birbaşa redaktə olunur).
  Marşrutlar: `#/` (baş səhifə), `#/bolme/<slug>` (bölmə), `#/axtar?q=...` (axtarış), `#/tixac` (tıxac xəritəsi).
- `data/news.json` — xəbər lenti (avtomatik yenilənir, yığcam JSON).
- `data/markets.json` — valyuta (AMB, ehtiyat: ExchangeRate-API), Brent/WTI neft və bitcoin (Yahoo Finance, ehtiyat: CNBC/CoinGecko), qızıl/gümüş (gold-api.com).
- `data/social.json` — Prezidentin və birinci xanımın rəsmi YouTube videoları və X/Instagram/Facebook paylaşımları (X-in açıq lenti bağlı olduğundan paylaşımlar onları xəbər verən rəsmi/agentlik xəbərlərindən götürülür, `via` sahəsi mənbəni göstərir). Yalnız vaxta görə sıralanır.
- `data/status.json` — son uğurlu yoxlamanın vaxtı (`checkedAt`). Saytdakı «Yeniləndi» bunu göstərir.
- `data/sources.json` — hər lentin son uğurlu vaxtı, xəbər sayı və son xətası. Saytda: `#/menbeler`.
- `data/og.json` — şəkilli olmayan xəbərlər üçün məqalə səhifəsinin `og:image` / `twitter:image` ünvanı. Hər keçid bir dəfə sorğulanır (vaxt limiti, paralel). Boş nəticə də saxlanır ki, təkrar sorğu olmasın.
- `data/dates.json` — lentində tarix olmayan mənbələr (İki Sahil-in RSS-ində `pubDate` yoxdur) üçün məqalə səhifəsindən oxunan dərc vaxtı (`datePublished`, `article:published_time`, `<time>`). Əvvəl belə xəbərlər hər dövrədə «indi» tarixi alır, hər bölmənin başında «N dəqiqə əvvəl» kimi qalırdı. Bir dövrədə ən çox 30 səhifə sorğulanır (`DATE_LOOKUPS`), ünvanındakı tarix 5 gündən köhnə olan yazılar sorğusuz atılır; tarixi tapılmayan yazı ilk görüldüyü vaxtı alır və bir daha dəyişmir.
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
- Redaksiya süzgəci (`is_negative_about_leadership`): rəhbərlik və dövlət qurumları (`LEADERSHIP`, az/ru/en/tr) neqativ sözlərlə (`NEGATIVE`) birlikdə gələndə, həmçinin müxalif çərçivə ifadələri və müxalif partiya/media adları (`OPPOSITION`) olanda xəbər dərc edilmir; rəsmi səhifələr istisnadır. Müxalif mənbələr lentdə yoxdur. Xarici mənbələrin Azərbaycan dövləti haqqında xəbərləri də dərc edilmir (idman istisna).
- Son dəqiqə lenti Web Animations API ilə hərəkət edir (telefonda «hərəkəti azalt» rejimində də axır), barmaqla/siçanla çəkilir, siçan üstündə dayanır. Valyuta kartları həmişə görünür (açılıb-bağlanan panel yoxdur), hündürlüyü ~55px-dir. Toxunma ekranında karusel oxları gizlidir (sürüşdürmə ilə).
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
- Xarici mənbələrin (WORLD_FEEDS) Azərbaycan dövləti, rəhbərliyi, Bakı, Qarabağ, Naxçıvan haqqında xəbərləri dərc edilmir (`foreign_about_azerbaijan`, idman istisna); bu mövzu yalnız Azərbaycan mənbələrindən gəlir.
- «Bölgələr» bölməsi: rayon və şəhər adları ilə təyin olunur (Bakı istisna), mənbə kimi AZƏRTAC-ın «Regionlar» lenti də var. GəncəXəbər və Patriotnews lent vermir (biri bot-qoruma arxasındadır, digəri açılmır).
- Loqo: `assets/logo.png` (ağ «8» içində 8 guşəli ulduz və yumruq, sarı «ULDUZ»; fon şəffaf, mənbə şəkil sahibdən). Başlıq/altlıqda `logo-80.png` (retina), şəkilsiz kartların yerində də o; açıq temada tünd lövhə üstündə. Favicon, PWA ikonları (`icon-*.png`, maskable) və `og-default.png` (1200×630) eyni loqodan `C:/t8/build_logo.js` ilə yaradılıb (xarici kitabxanasız PNG emalı, `png.js`). Telefonda səhifəyə qayıdanda lent dərhal yoxlanır (`visibilitychange`/`pageshow`/`online`).
- Mənbə sayı 54-dən 78-ə çıxdı (Oxu, Publika, Lent, Axar, Ölkə, Yeniçağ, AzVision, Moderator, Bizim.Media, Reyting, News24, Anews, Aznews, Zim, Konkret, 525, İki Sahil, Femida, Ordu, Azpolitika, Marja, Banco, Media.az, AZƏRTAC Regionlar); Baku.ws və Hafta.az GitHub-dan 403 qaytardığı üçün yoxdur. Limitlər: mənbə başına 40, cəmi 1200.
- Zuğulba xronikasında rəsmi səhifələrlə yanaşı dövlət və iqtidar saytlarının prezident xəbərləri də var (`STATE_SRC`: AZƏRTAC, Cross Media, Xalq qəzeti, «Azərbaycan» qəzeti, Yeni Azərbaycan, Baku TV, APA, Report, Trend…) və kartlar şəkillidir (xəbərin öz şəkli, yoxdursa digər mənbənin şəkli). Cross Media, Xalq qəzeti və Yeni Azərbaycanın RSS-i yoxdur — siyahı/ana səhifələri oxunur (`PAGE_PARSERS`), Baku TV Google News sitemap-ı ilə gəlir; Caliber.az yalnız rus/ingilis dilində (Yandex Turbo lenti) olduğu üçün yoxdur.
- «Təhsil» və «Səhiyyə» bölmələri açar sözlərlə təyin olunur (`CATEGORIES`, 1.5 çəki); «Həyat» həyat tərzi, qidalanma və psixologiya üçün qalır.
- Şəkil: saytın ümumi paylaşım şəkli (azertag social.jpg və s.) və 3+ xəbərdə təkrarlanan şəkil xəbərin şəkli sayılmır; şəkilsiz xəbər üçün səhifədən og:image → twitter:image → image_src → JSON-LD oxunur (hər dövrədə 120 səhifə), yoxdursa eyni xəbərin digər mənbəsinin şəkli götürülür.

## Domen (8ulduz.az)

Sayt GitHub Pages-dədir; xüsusi domen üçün:

1. Domenin DNS-ində (nic.az / qeydiyyatçı paneli): kök `8ulduz.az` üçün 4 A yazısı — `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153` (istəyə görə AAAA: `2606:50c0:8000::153`, `…8001::153`, `…8002::153`, `…8003::153`); `www` üçün CNAME → `8ulduz.github.io`.
2. DNS yayılandan sonra (`nslookup 8ulduz.az` GitHub ünvanlarını göstərəndə) repo kökünə bir sətirlik `CNAME` faylı (`8ulduz.az`) əlavə edilir və GitHub → Settings → Pages → Custom domain-də `8ulduz.az` yazılıb «Enforce HTTPS» seçilir (sertifikat bir neçə dəqiqəyə verilir).
3. `updater.py` CNAME faylını görən kimi bölmə səhifələrini, sitemap, robots və feed-i yeni ünvanla yazır (`site_url`). `index.html`-dəki canonical/og ünvanları (9 yer) və README-dəki keçidlər əl ilə dəyişdirilir. Manifest və service worker nisbi yollarla işlədiyi üçün dəyişmir.
4. Köhnə `8ulduz.github.io/8ulduz/` ünvanı avtomatik yeni domenə yönlənir.

DNS qoşulmamış CNAME faylı əlavə edilməməlidir — Pages saytı mövcud olmayan domenə yönləndirər və sayt açılmaz.

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

**Ehtiyat kanal.** Bəzi şəbəkələrin DNS-i `8ulduz.az` üçün «domen yoxdur» cavabı verə bilir, domenin özü sağlam olsa da. Buna görə saytı bir dəfə açmış ziyarətçidə `sw.js` məlumatı əvvəl saytdan, alınmasa `raw.githubusercontent.com`-dan götürür. Pages 15 dəqiqədən çox yayımlamayıbsa `status.json` və `news.json` də oradan gəlir. Keş yalnız ikisi də alınmayanda göstərilir («Oflayn — saxlanmış xəbərlər»). Repo adı dəyişsə `sw.js`-dəki `MIRROR` da dəyişməlidir.

Manual işə salmaq üçün: **Actions → Xəbərləri yenilə → Run workflow**.

Hər dövrədə `data/sources.json`, `feed.xml`, `sitemap.xml` və `robots.txt` də push olunur.

## Saytı dərc etmək

**Settings → Pages → Source: `main` branch** → Save. Ünvan: `https://8ulduz.az/`
