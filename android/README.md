# 8ulduz — Android tətbiqi (Google Play)

Bu qovluq 8ulduz.az-ın Google Play tətbiqidir. Tətbiq **Trusted Web Activity (TWA)** texnologiyası ilə qurulub: saytı telefondakı Chrome mühərriki ilə, ünvan sətri olmadan, tam ekranda açır. Google Play-dəki bir çox böyük xəbər və xidmət tətbiqi eyni üsulla işləyir.

**Nəticədə:**
- Saytda edilən hər dəyişiklik tətbiqdə dərhal görünür; yeni xəbər və ya dizayn üçün tətbiqi yeniləməyə ehtiyac yoxdur.
- Tətbiq çox yüngüldür (~1 MB), Chrome-un sürətini, girişlərini və təhlükəsizlik yeniləmələrini istifadə edir.
- Saytın «Son dəqiqə» bildirişləri tətbiqin adı və ikonu ilə gəlir (Android 13+ üçün icazə istənilir).
- 8ulduz.az keçidləri (məs. WhatsApp-dan) tətbiqdə açılır, xəbər mənbələrinin keçidləri isə tətbiqin içində açılan brauzer pəncərəsində.
- İkonu basılı saxlayanda qısa yollar: Gündəm, İdman, Seçilmişlər, Axtar.
- Android 13+ tematik (monoxrom) ikon, adaptiv ikon, açılış ekranı.

| | |
|---|---|
| Paket adı | `az.ulduz8.app` (Play-də yüklədikdən sonra **dəyişmək olmur**) |
| Minimum Android | 7.0 (API 24) |
| Hədəf API | 36 (Android 16) |
| Kitabxana | `com.google.androidbrowserhelper` 2.7.4 |

## Necə yığılır

Kompüterdə Android Studio lazım deyil. `android/**` dəyişəndə GitHub Actions (`.github/workflows/android.yml`) avtomatik:

1. lint yoxlamasını keçirir;
2. imzalı **AAB** (Play üçün) və **APK** (telefona birbaşa quraşdırmaq üçün) yığır;
3. imzanın barmaq izinin `.well-known/assetlinks.json`-da olduğunu yoxlayır;
4. faylları **Actions → Android tətbiqi → son işin «Artifacts» bölməsinə** qoyur.

`versionCode` hər yığımda avtomatik artır. Mağazada görünən versiyanı (`1.0.0`) `android/gradle.properties`-də dəyişin.

## Bir dəfəlik quraşdırma

### 1. İmza açarı → GitHub secrets

Play-ə yüklənən hər fayl eyni **yükləmə açarı** ilə imzalanmalıdır. Açar repoda **yoxdur** (repo açıqdır) və GitHub-da iki secret kimi saxlanır:

| Secret | Dəyər |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | `upload-keystore.p12` faylının base64 forması |
| `ANDROID_KEYSTORE_PASSWORD` | açarın parolu |

Repo → Settings → Secrets and variables → Actions və ya `gh secret set` ilə yazılır. Secret yoxdursa, workflow yalnız test APK-sı yığır.

> Açarı və parolu itirsəniz, Play Console-dan yeni yükləmə açarı istəmək mümkündür (Play App Signing sayəsində), amma bu bir neçə gün çəkir. Ehtiyat nüsxəsini saxlayın.

### 2. Play Console

1. <https://play.google.com/console> — tərtibatçı hesabı (birdəfəlik 25 $, şəxsiyyət təsdiqi).
2. **Tətbiq yarat** → ad «8ulduz — Son xəbərlər», dil Azərbaycan, tətbiq, pulsuz.
3. Mağaza səhifəsi və «Tətbiq məzmunu» — hazır mətn və cavablar: [`play-store/listing.md`](play-store/listing.md).
4. **Test → Daxili test** → yeni buraxılış → Actions-dan yüklədiyiniz `.aab` faylı. Play App Signing-ə razılıq verin.

> **Yeni şəxsi hesablar üçün:** istehsala (hamıya) çıxmazdan əvvəl ən azı **12 test istifadəçisi 14 gün** ərzində qapalı testdə olmalıdır. Təşkilat (şirkət) hesablarında bu tələb yoxdur.

### 3. Play imza açarının barmaq izi → assetlinks.json

Play App Signing tətbiqi Google-un öz açarı ilə yenidən imzalayır. Ünvan sətri görünməsin deyə həmin açarın izi də saytda olmalıdır:

1. Play Console → **Test və buraxılış → Tətbiqin bütövlüyü → Tətbiq imzalama** → «Tətbiq imzalama açarının sertifikatı» → **SHA-256**.
2. Onu `.well-known/assetlinks.json`-da `sha256_cert_fingerprints` siyahısına ikinci sətir kimi əlavə edin (yükləmə açarının izi qalmalıdır).
3. Dəyişiklik saytda dərc olunandan sonra yoxlayın:
   <https://digitalassetlinks.googleapis.com/v1/statements:list?source.web.site=https://8ulduz.az&relation=delegate_permission/common.handle_all_urls>

## Yeni versiya buraxmaq

Sayt dəyişiklikləri üçün buna ehtiyac yoxdur. Yalnız tətbiqin özü (ikon, ad, qısa yollar, Android versiyası) dəyişəndə:

1. `android/gradle.properties`-də `appVersionName`-i artırın, dəyişikliyi `main`-ə salın.
2. Actions-dakı yeni `.aab` faylını Play Console-a yükləyin.

**Avtomatik yükləmə (istəyə bağlı):** Google Cloud-da Play Developer API xidmət hesabı yaradıb Play Console-da ona «Buraxılışları idarə et» icazəsi verin, JSON açarını `PLAY_SERVICE_ACCOUNT_JSON` secret-inə yazın. Sonra Actions → Android tətbiqi → **Run workflow** → `internal` / `alpha` / `production`. İstehsal buraxılışı qaralama kimi gedir, «Yayımla»nı Play Console-da siz basırsınız. İlk buraxılış həmişə əl ilə yüklənməlidir.

## Problemlər

| Əlamət | Səbəb və həll |
|---|---|
| Tətbiqin yuxarısında ünvan sətri görünür | İmzanın izi `assetlinks.json`-da yoxdur (çox vaxt Play imza açarı — yuxarıda 3-cü addım) və ya `https://8ulduz.az/.well-known/assetlinks.json` açılmır. `.nojekyll` faylı silinməməlidir. |
| Bildiriş gəlmir | Android parametrlərində tətbiqin bildiriş icazəsi; saytda «Bildiriş» düyməsi basılmalıdır. |
| Workflow: «Açar oxunmadı» | `ANDROID_KEYSTORE_PASSWORD` və ya base64 səhv kopyalanıb. |
| Workflow: «… assetlinks.json-da yoxdur» | Başqa açarla imzalanıb; ya düzgün açarı secret-ə yazın, ya da yeni izi `assetlinks.json`-a əlavə edin. |

## Lokal yığım (istəyə bağlı)

Android Studio ilə `android/` qovluğunu açın. İmzalı yığım üçün `android/keystore.properties` yaradın (`.gitignore`-dadır):

```properties
storeFile=../../8ulduz-android-acar/upload-keystore.p12
storePassword=…
keyAlias=upload
```
