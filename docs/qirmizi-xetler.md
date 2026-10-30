# Saytın qırmızı xətləri

Sayt sahibinin qərarı (2026-10-30). Bu iki qayda dəyişməzdir. Hər kod dəyişikliyi, o cümlədən süni intellekt agentlərinin dəyişikliyi, bunlara əməl etməlidir. Qaydanı yumşaldan dəyişiklik yalnız sayt sahibinin açıq göstərişi ilə edilir.

## 1. Xəbər ən geci 60 saniyədən bir yenilənir və axın dayanmır

| Qat | Nə edir | Harada |
|---|---|---|
| Sürətli dövrə | Hər 60 saniyə lentləri oxuyur, cəmi 25 saniyə gözləyir. Vaxtında cavab verməyən lentin son nəticəsi işlədilir. | `updater.py --fast`, `pipeline.sh` |
| Canlı kanal | `status.json`, `latest.json`, `markets.json` tarixçəsiz `live` budağına yazılır. Repo şişmir, Pages limitinə toxunmur. | `push_live` |
| Yavaş işlər | Məzənnə, şəkil, səs mətni, video, idman və SEO arxa planda işləyir, xəbəri gözlətmir. | `updater.py --slow` |
| Tam lent | Hər 10 dəqiqə `main`-ə yazılır, Pages yayımlayır. | `publish_main` |
| Növbə dəyişməsi | İş bitməzdən əvvəl növbətisini başladır, onu görəndən sonra çıxır. | `pipeline.sh`, `update.yml` |
| Sınıq kod | Cari kod işləməsə son işlək kodla davam edir. | `.lkg`, `run_py` |
| Zədəli fayl | Son sağlam nüsxə ilə əvəz olunur. | `guard_outputs`, `check_outputs.py` |
| İlişmiş iş | Nəzarətçi 6 dəqiqə yazmayan işi dayandırıb yenisini başladır, 10 dəqiqədə issue açır. | `watchdog.yml` |
| Sayt | 30 saniyədən bir yoxlayır. Ardıcıllıq: canlı kanal, sayt, ehtiyat kanal, keş. | `sw.js`, `app.js` |

Yoxlama: `tests/test_red_lines.py`, `tests/browser-logic.test.cjs` və hər PR-da real lentlərlə işləyən `bir-deqiqe` işi (`check.yml`). Təkrar dövrə 50 saniyəni keçsə PR qırmızı olur.

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
