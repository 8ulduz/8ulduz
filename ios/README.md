# 8ulduz: iPhone tətbiqi

Bu qovluq 8ulduz.az-ın App Store tətbiqidir. Android tətbiqindən fərqli olaraq saytı WebView-a bükmür, **tam nativ SwiftUI** tətbiqidir. Səbəb: Apple saytın bükülmüş nüsxəsini adətən «minimum funksionallıq» qaydası ilə (Guideline 4.2) rədd edir.

Tətbiq saytın məlumatını oxuyur: `data/*.json`, eyni qaydalar, eyni zəncir. Lentdəki dəyişiklik üçün tətbiqi yeniləmək lazım deyil.

| | |
|---|---|
| Bundle ID | `az.ulduz8.app` (vidcet: `az.ulduz8.app.widget`) |
| App Group | `group.az.ulduz8.app` |
| Minimum iOS | 17.0, yalnız iPhone, portret |
| Kitabxana | Yoxdur, yalnız Apple çərçivələri |
| Layihə | `project.yml` ([XcodeGen](https://github.com/yonaskolb/XcodeGen)), `.xcodeproj` repoda saxlanmır |

## Nə var

- **Əsas:** son dəqiqə sətri, bazar zolağı, hava və namaz, ən çox mənbədə çıxan xəbərlər karuseli, Zuğulba Xronikası, «Ən yeni / Ən çox mənbədə», bölmə zolaqları, video.
- **Bölmələr:** bütün bölmələr, idmanda klub süzgəci, Zuğulba Xronikasında rəsmi hesablar.
- **Axtar:** `qarabag`, `ilham eliyev` kimi yazılışları da tapır, son axtarışlar.
- **Seçilmişlər:** telefonda saxlanır, oflayn da görünür.
- **Xidmətlər:** bazar və çevirici, hava, namaz vaxtları, tıxac xəritəsi və yol xəbərləri, futbol cədvəlləri, video, mənbə vəziyyəti, tənzimləmələr.
- **iOS imkanları:** ana və kilid ekranı vidcetləri (son xəbərlər, bazar), «Son dəqiqə» bildirişləri, ikonu basılı saxlayanda qısa yollar, qaranlıq və işıqlı tema, Dynamic Type, VoiceOver.

## Qırmızı xətlər ([docs/qirmizi-xetler.md](../docs/qirmizi-xetler.md))

**1. Xəbər ən geci 60 saniyədən bir.** Tətbiq açıq olanda sayt kimi 30 saniyədən bir yoxlayır. Ardıcıllıq `sw.js` ilə eynidir: canlı kanal (`live/m/<dəqiqə>/`), sayt, ehtiyat kanal, keş. Vaxt rəqəmləri də eynidir. Kod: `Packages/UlduzCore/Sources/UlduzCore/FeedClient.swift`.

iOS-un qoymadığı yer: tətbiq **bağlı** olanda dəqiqəlik işləmək mümkün deyil. Vidcet və arxa plan yoxlamasının vaxtını iOS özü təyin edir (adətən 15 dəqiqə və daha seyrək). Mağaza mətnində buna görə bildirişin anında gələcəyi yazılmayıb. Anında bildiriş üçün push serveri lazımdır, bu isə indiki «serversiz, abunəliksiz» məxfilik vədini dəyişir.

**2. Xarici mənbələrdən Azərbaycan və rəhbərliyi haqqında, müxalifət mənbələrindən xəbər düşmür.** Qayda tətbiqdə ayrıca yazılmayıb: `assets/content-policy.js` faylı yığımda tətbiqə qoyulur (`project.yml`) və açılışda saytdan yenilənir, yəni qayda dəyişəndə tətbiq yenilənmədən qüvvəyə minir. Fayl yalnız məlumat kimi oxunur, kod kimi işlədilmir. Lent, əlavə mənbələr, seçilmişlər, vidcet və bildiriş hamısı bu qapıdan keçir. Fayl oxunmasa heç nə göstərilmir. Testlər: `ContentPolicyTests.swift` saytın və updater-in hallarını təkrarlayır.

## Yığım

Mac lazım deyil. `ios/**` dəyişəndə GitHub Actions (`.github/workflows/ios.yml`) macOS serverində:

1. məntiq testlərini işlədir (`swift test`);
2. layihəni yaradır, simulyatorda tətbiqi real lentlə sınayır;
3. App Store ekran şəkillərini çəkir (Actions → son iş → Artifacts → `ekran-sekilleri`, 6.9″, 1320×2868);
4. cihaz üçün imzasız yığımı yoxlayır.

Mac varsa, lokal:

```bash
brew install xcodegen
cd ios && xcodegen generate && open Ulduz8.xcodeproj
```

## App Store-a çıxış

Bu addımlar hesab sahibinindir (hesab, ödəniş, şəxsiyyət təsdiqi):

1. **Apple Developer Program:** <https://developer.apple.com/programs/enroll/>, ildə 99 $. Şəxsi hesabda satıcı adı kimi şəxsin adı görünür; «8ulduz» adı üçün təşkilat hesabı və D-U-N-S nömrəsi lazımdır.
2. **Team ID:** <https://developer.apple.com/account> → Membership details.
3. **App Store Connect → Apps → + New App:** iOS, ad `8ulduz: Son xəbərlər`, dil Azerbaijani, Bundle ID `az.ulduz8.app`, SKU `8ulduz-ios`. Bundle ID siyahıda yoxdursa, əvvəl <https://developer.apple.com/account/resources/identifiers> ünvanında yaradın, vidcet ID-si və App Group-u da ora əlavə edin.
4. **API açarı:** App Store Connect → Users and Access → Integrations → Team Keys → `+`, rol **App Manager**, «Access to Cloud Managed Distribution Certificate» aktiv. `.p8` faylı **bir dəfə** yüklənir, repoya qoymayın.
5. **Secrets:** repo Settings → Secrets and variables → Actions:

   | Secret | Dəyər |
   |---|---|
   | `ASC_KEY_ID` | Açarın Key ID-si |
   | `ASC_ISSUER_ID` | Issuer ID (açarlar səhifəsinin başında) |
   | `ASC_KEY_BASE64` | `.p8` faylının base64 forması |
   | `APPLE_TEAM_ID` | Team ID |

   Repo `8ulduz` hesabına aiddir: secret-ləri yalnız o hesab yaza bilər.
6. **Actions → iOS tətbiqi → Run workflow → `testflight`.** Sertifikat kompüterdə saxlanmır, imzanı Apple buludda edir. Yığım 10-30 dəqiqəyə TestFlight-da görünür.
7. **Mağaza səhifəsi:** hazır mətn, cavablar və yoxlayıcı üçün qeyd: [`app-store/listing.md`](app-store/listing.md).

## Yeni versiya

Sayt, xəbər, mənbə və qayda dəyişiklikləri üçün buna ehtiyac yoxdur. Yalnız tətbiqin özü dəyişəndə `project.yml`-də `MARKETING_VERSION`-u artırın, `main`-ə salın, `testflight` işini işə salın. Build nömrəsi avtomatik artır.

## Sonra edilə bilənlər

- **Universal Links** (`https://8ulduz.az/#/...` keçidləri tətbiqdə açılsın): Team ID bəlli olandan sonra `.well-known/apple-app-site-association` faylı və `com.apple.developer.associated-domains` lazımdır.
- **`manifest.webmanifest`-də `related_applications`:** tətbiq mağazada çıxandan sonra `itunes` sətri əlavə olunur.

## Saytla uyğunluq

Saytda aşağıdakılar dəyişəndə tətbiqdə də dəyişməlidir:

- Bölmələr: `CATS` və `SECTION_ALIAS` (`assets/app.js`), tətbiqdə `Catalog.swift`.
- İdman və bölgə düymələri: `SPORT_TABS`, `REGION_TABS`, tətbiqdə `TopicData.swift`. `TopicTests` adları saytla tutuşdurur.
- Komanda səhifəsi: `assets/komanda.js`, tətbiqdə `TeamData.swift` və `TeamViews.swift`.

## İnterfeys dili

Xəbərin dili türk, rus və ya ingilis seçiləndə interfeys də həmin dilə keçir, xəbər mətni tərcümə olunmur. Vidcetin yazıları azərbaycanca qalır.

Lüğət saytındır (`assets/dil-*.js`), yalnız tətbiqə xas yazılar `ios/tools/app-strings.json`-dadır. Yazı dəyişəndə:

```bash
node ios/tools/localize.cjs --check
node ios/tools/localize.cjs
```
