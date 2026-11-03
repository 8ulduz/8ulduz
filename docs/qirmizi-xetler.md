# Saytın qırmızı xətləri

Sayt sahibinin qərarı (2026-10-30). Bu iki qayda dəyişməzdir. Hər kod dəyişikliyi, o cümlədən süni intellekt agentlərinin dəyişikliyi, bunlara əməl etməlidir. Qaydanı yumşaldan dəyişiklik yalnız sayt sahibinin açıq göstərişi ilə edilir.

## 1. Xəbər ən geci 60 saniyədən bir yenilənir və axın dayanmır

| Qat | Nə edir | Harada |
|---|---|---|
| Sürətli dövrə | Hər 60 saniyə lentləri oxuyur, cəmi 20 saniyə gözləyir. Vaxtında cavab verməyən lentin son nəticəsi işlədilir. | `updater.py --fast`, `pipeline.sh` |
| Canlı kanal | `status.json`, `latest.json`, `markets.json` tarixçəsiz `live` budağına, hər dəqiqə ayrı yola (`m/<dəqiqə>/`) yazılır. Repo şişmir, Pages limitinə toxunmur. | `push_live` |
| Yavaş işlər | Məzənnə, şəkil, video, idman, bölmə arxivi və SEO arxa planda işləyir, xəbəri gözlətmir. | `updater.py --slow` |
| Ölü linklər | 30 saniyədən bir linkləri yoxlayır: 404 verən xəbər çıxır və ya başqa mənbəyə keçir, link düzələndə qayıdır. Xəbər dövrəsi şəbəkə gözləmir, proses düşsə axına təsiri yoxdur. | `updater.py --links`, `links_loop` |
| Tam lent | Hər 10 dəqiqə `main`-ə yazılır, Pages yayımlayır. | `publish_main` |
| Növbə dəyişməsi | İş bitməzdən əvvəl növbətisini başladır, onu görəndən sonra çıxır. | `pipeline.sh`, `update.yml` |
| Sınıq kod | Cari kod işləməsə son işlək kodla davam edir. | `.lkg`, `run_py` |
| Zədəli fayl | Son sağlam nüsxə ilə əvəz olunur. | `guard_outputs`, `check_outputs.py` |
| Asılan dövrə | İşin özü dövrənin 4 dəqiqə irəliləmədiyini görsə çıxır, son addım yeni iş başladır. Yazının alınmaması ayrıdır: GitHub qısa kəsiləndə işlək iş öldürülmür, 15 dövrədən sonra dəyişir. | `self_watch`, `pipeline.sh` |
| İlişmiş iş | Nəzarətçi 6 dəqiqə yazmayan və 6 dəqiqədən köhnə işi dayandırıb yenisini başladır, 10 dəqiqədə issue açır. Təzə başlayan işə toxunmur. | `watchdog.yml` |
| Sayt | 30 saniyədən bir yoxlayır. Ardıcıllıq: canlı kanal, sayt, ehtiyat kanal, keş. | `sw.js`, `app.js` |

Yoxlama: `tests/test_red_lines.py`, `tests/browser-logic.test.cjs` və hər PR-da real lentlərlə işləyən `bir-deqiqe` işi (`check.yml`). Təkrar dövrə 35 saniyəni keçsə PR qırmızı olur.

Niyə ayrı yol: `raw.githubusercontent.com` budaq adı ilə verilən faylı sorğu parametrindən asılı olmayaraq 5 dəqiqə keşləyir (2026-10-30 ölçülüb), yeni yolu isə dərhal verir. Yaranmamış yola sorğu 404-ü 55 saniyə keşə salır, ona görə dövrə dəqiqənin 5-ci saniyəsində başlayır, `sw.js` dəqiqəni yalnız 45 saniyə keçəndən sonra istəyir. Bu rəqəmləri dəyişməyin.

Məlum hədd: hamısı GitHub üzərindədir. GitHub Actions və ya `raw.githubusercontent.com` tam dayansa axın da dayanır, sayt son xəbərləri göstərir. Bunu yalnız GitHub-dan kənar ehtiyat server aradan qaldırar.

## 2. Xarici mənbələrdən Azərbaycan və rəhbərliyi haqqında, müxalifət mənbələrindən heç bir xəbər düşmür

Qaydalar bir fayldadır: `assets/content-policy.js`.

| Qat | Nə edir | Harada |
|---|---|---|
| İcazəli siyahı | Siyahıda olmayan mənbə lentə qoşulmur. | `azSources`, `worldSources`, `FEEDS` |
| Keçid yoxlaması | Xəbərin keçidi mənbənin öz saytına aparmalıdır. | `source_allowed` |
| Qadağan saytlar | Heç vaxt düşmür, başqa mənbə adı ilə də. | `blockedHosts` |
| Xarici mənbə qaydası | Başlıq və xülasədə Azərbaycan mövzusu varsa düşmür. | `azTerms`, `foreign_about_azerbaijan` |
| Son qapı | Yazılan hər lent keçir: updater, sonra dərcdən əvvəl ayrıca skript. | `content_policy.enforce`, `check_outputs.py` |
| Brauzer | Telefondakı köhnə keş də eyni qaydadan keçir. | `policyViolation` |

İstisna: xarici idman mənbələrinin klub və idmançı xəbərləri (Qarabağ FK və s.). Rəhbərlik adı keçən idman xəbəri də düşmür (`leaderTerms`).

Yeni mənbə əlavə etmək üçün həm `updater.py`-dakı lentə, həm `content-policy.js`-ə yazılmalıdır. Müxalifət mənbəsi siyahıya əlavə edilmir. Hansı mənbənin müxalifət sayıldığına sayt sahibi qərar verir.

Qaydalar saytın «Haqqımızda» səhifəsində oxuculara açıq yazılıb və orada qalmalıdır.

## 3. Sayt sürətli işləyir: kompüterdə, planşetdə, telefonda və tətbiqlərdə

Sahibin qərarı (2026-10-31). Səhifəyə və ya məlumata ağırlıq əlavə edən hər dəyişiklikdən əvvəl və sonra ölçülür, rəqəmlər PR-da yazılır.

Ölçmə: `npx lighthouse https://8ulduz.az/` (telefon), `--preset=desktop` (kompüter), 768 enində `--screenEmulation.width` (planşet).

- İlk açılışda yükləmə 1,5 MB-dan az qalır. Şəkil birbaşa tam ölçüdə göstərilmir (`sized`, `assets/app.js`).
- Bir neçə faylın gəlməsi səhifəni bir neçə dəfə yenidən çəkmir (`requestRender`).
- Baş səhifənin ekrandan uzaq bölmələri yaxınlaşanda qurulur (`lazySection`).
- `app.js` və `app.css`-in ölçü limiti var, `tests/browser-logic.test.cjs` yoxlayır: `app.js` 220 000 baytdan az (sahibin qərarı, 2026-11-03; əvvəl 200 000), `app.css` 95 000 baytdan az. Limit kodun nəzarətsiz böyüməsini tutur; sürəti dəyişikliyin gördüyü iş təyin edir, ona görə ölçmə yenə hər PR-da lazımdır.
- Komanda səhifəsinin kodu (`komanda.js`, `komanda.css`) və məlumatı (`data/futbol/`) yalnız o ünvan açılanda yüklənir, fayllar yalnız `slow_cycle`-da yazılır.

Ölçü 2026-10-31 (lokal, PR #55-dən sonra): telefon 46, planşet 51, kompüter 71 bal. Telefonda hədəfə hələ çatılmayıb.

Sahibin qərarı (2026-11-03): sürət qırmızı xəttdir, hər keçid «göz qırpımında» olmalıdır. Həmin gün canlı ölçü (telefon): baş səhifə 54 bal, FCP 2,4 s, LCP 4,7 s, 1450 KB; paylaşılan xəbər səhifəsi 64 bal, LCP 6,0 s. Ona görə qaydalar əlavə olundu, hamısını `tests/browser-logic.test.cjs` («speed red line») tutur:

- Şəbəkədən şrift gəlmir: sistem şrifti (`app.css`). 131 KB-lıq Inter ilk ekranla eyni xətti bölüşürdü.
- `index.html` qabığı (başlıq, bölmələr, skelet) statik daşıyır, `shell()` onu silmir: CSS gələn kimi səhifə görünür. Statik nüsxə `shell()` ilə eyni olmalıdır; `shell()` və ya `renderNav()` dəyişəndə index.html də yenilənir (test tutur).
- `sw.js`: HTML/JS/CSS saxlanmış nüsxədən dərhal verilir, təzəsi arxada saxlanır (`cachedShell`); kod dəyişəndə `VERSION` artır, artmasa da fərq səhifəyə bildirilir. `app.js` təkrar açılışda keşdəki lenti şəbəkəni gözləmədən çəkir (`loadCached`).
- Paylaşılan keçid (`#/xeber/ID`) tam lenti gözləmir: xəbər `data/paylas/N.json`-dan çəkilir (`loadShared`), `index.html` onu erkən istəyir.
- Proksidən keçməyən saytların (`PROXY_SKIP`) 170–290 KB-lıq orijinal şəkli telefonda slayderdən başqa yerdə yüklənmir (`heavyImage`), slayderə yalnız kiçildilə bilən şəkil düşür.
- Başlıqda `backdrop-filter` yoxdur; canlı kanalın hostuna `preconnect` var; telefonda lent üçün yer saxlanır.
- Baş səhifənin ilk ekranı (slayder, Zuğulba, «Son xəbərlər») `index.html`-də hazır HTML kimi gəlir: pipeline hər main yazılışında (10 dəqiqə) `.github/scripts/prerender.cjs` ilə onu app.js-in öz `homeView()`-undan qurur (`data/first.json`, telefon eni); `#view` blokunu əl ilə dəyişməyin, növbəti yazılışda üstündən yazılır. Brauzer onu CSS ilə birgə çəkir, ilk şəkil HTML-dən dərhal yüklənir, JS gözlənilmir; app.js gələndə eyni görünüşü təzə məlumatla əvəz edir (`patchView` sarğını açır, dəyişməyən kart yerində qalır), skelet və ya xəta mesajı hazır ekranı silmir (`renderView`). Mənbə qaydası (qırmızı xətt 2) hazır nüsxədə də işləyir: skript `content-policy.js`-i yükləyir. Hazır blokda yalnız ekranda görünən hissə var (3 slayd, 8 Zuğulba kartı, 4 son xəbər; tam blok 24 KB gzip idi və ilk çəkilişi gecikdirirdi): index.html gzip ilə 5 → 11 KB olur, qalanını app.js tam siyahı ilə doldurur, 44 Zuğulba kartı qaydası səhifənin özündə dəyişmir. Başlıqdakı HTML işarələri brauzerdəki kimi açılır (skriptdə textarea yoxdur, cədvəl var); skript alınmasa index.html olduğu kimi qalır və sayt app.js ilə dolur.

Ölçü 2026-11-03 (lokal, dəyişiklikdən əvvəl → sonra, eyni serverdə): telefon simulyasiyası (gzip ilə lokal server, şəbəkə və CPU Lighthouse-un standart yavaşlatması). Baş səhifə: 58 → 60 bal, FCP 1,8 s → 1,2 s, LCP 6,3 s → 4,7 s, Speed Index 4,7 s → 3,2 s, CLS 0.005 → 0.035. Paylaşılan xəbər səhifəsi: 64 → 68 bal, FCP 1,8 s → 1,7 s, LCP 5,6 s → 5,0 s, Speed Index 4,6 s → 4,2 s, CLS 0 → 0. Canlı saytda təkrar açılış əlavə olaraq keşdən gəlir (burada ölçülmür). Ölçmə skriptləri: Lighthouse 12, `node serve3.js <kök> <port>`. Canlı sayt (telefon, ilk açılış, keşsiz; əvvəl → sonra, 2026-11-03): baş səhifə: 54 → 67 bal, FCP 2,4 s → 1,7 s, LCP 4,7 s → 3,9 s, Speed Index 5,3 s → 3,5 s, yük 1450 → 730 KB; paylaşılan xəbər səhifəsi: 64 → 83 bal, FCP 1,9 s → 1,6 s, LCP 6,0 s → 3,5 s, Speed Index 2,8 s → 2,4 s, yük 670 → 506 KB. Təkrar açılış canlıda service worker keşindən gəlir: HTML 10 ms, app.js 26 ms, ilk ekranın məlumatı 160 ms (brauzerdə ölçülüb). Şəkillər geri qaytarılandan sonra (sahib: «şəkil gəlmir», proksisiz orijinal atılmır, yalnız aşağı prioritetdədir) və sw.js v34 ilə: baş səhifə 66 bal, FCP 1,6 s, LCP 3,4 s, yük 1087 KB; xəbər səhifəsi 71 bal, LCP 4,2 s.
