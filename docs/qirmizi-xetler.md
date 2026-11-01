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
- `app.js` və `app.css`-in ölçü limiti var, `tests/browser-logic.test.cjs` yoxlayır.

Ölçü 2026-10-31 (lokal, PR #55-dən sonra): telefon 46, planşet 51, kompüter 71 bal. Telefonda hədəfə hələ çatılmayıb.
