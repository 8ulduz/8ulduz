# TikTok-da video xəbərlər

Sahibin göstərişi (2026-11-22): «Tik-tok səhifəmizdə videolar verilsin. Videolarda başda 8ulduz.az yazılsın.»

| Nə | Kim | Harada |
|---|---|---|
| Videonu hazırlamaq, yuxarıda «8ulduz.az» yazısı | video modulu (ayrı iş: «Facebook və Instagram-da video xəbərlər») | onun öz faylları |
| Videonu TikTok-a yükləmək, statusu yoxlamaq, token | hazırdır | `.github/scripts/tiktok.cjs`, `.github/workflows/tiktok.yml`, `tests/tiktok.test.cjs` |
| TikTok tətbiqi, audit, açarlar, qoşulma | **siz** | aşağıdakı addımlar |

Açar yoxdursa iş axını heç nə göndərmir, sakitcə ötürür. Xəbər axınından ayrıdır: saytın sürətinə və dəqiqəlik yenilənməyə toxunmur.

## Əvvəlcə bilməli olduğunuz 5 qayda

1. **Auditdən əvvəl hər şey gizlidir.** TikTok-un sözü ilə: «All content posted by unaudited clients will be restricted to private viewing mode.» Auditə qədər video yalnız sizə görünür (`SELF_ONLY`), hesab gizli (Private account) olmalıdır, tətbiq 24 saatda ən çox 5 istifadəçiyə işləyir. İctimai paylaşım üçün TikTok-un ayrıca **Direct Post auditi** lazımdır.
2. **Audit rədd edilə bilər — bu ən böyük riskdir.** TikTok-un paylaşma qaydalarında (Content Sharing Guidelines) «qəbuledilməz» nümunə kimi bu yazılıb: «A utility tool to help upload contents to the account(s) you or your team manages». Tətbiq yoxlaması qaydalarında da: «Apps must not be for private or personal use». Bizim alət məhz öz hesabımıza yükləyir. Yəni ictimai avtomatik paylaşım üçün audit keçməyə bilər. Rədd olunsa, aşağıdakı **B yolu** (qaralama) qalır.
3. **Su nişanı qaydası.** TikTok tətbiqlərdən tələb edir ki, paylaşılan məzmuna brend adı, loqo, keçid və ya reklam mətni əlavə etməsinlər. Bu qayda başqalarının videosuna tətbiqin öz brendini vurmağa aiddir. Bizdə video da, ad da bizimdir: «8ulduz.az» videonun öz məzmunudur, yükləyici videoya heç nə əlavə etmir. Auditdə bunu belə izah edin, amma yoxlayıcı başqa cür qərar verə bilər.
4. **Gündəlik hədd.** Hesaba gündə təxminən 15 API postu (bütün tətbiqlər birlikdə). Bizdə gündə ən çox 10 video, aralarında ən az 60 dəqiqə. TikTok «çox post» desə, 6 saat fasilə verilir.
5. **Yalnız öz videolarımız.** TikTok-un qaydası: «Content is also ineligible for the FYF if it includes unoriginal or reused material without anything new.» Başqasının videosu tövsiyə lentinə düşmür. Müəllif hüququnu təkrar pozan hesabı TikTok bağlaya bilər. Ona görə X-dəki F1, NBA, Fox News kimi videolar (`data/reels.json`) TikTok-a **heç vaxt** getmir. Yükləyici yalnız bu şərtlərin hamısı ödənəndə göndərir:
   - JSON-da `"own": true` var;
   - faylın metadatasında «8ulduz.az» nişanı var;
   - JSON-da başqa saytın video keçidi yoxdur;
   - video `data/reels.json`-da deyil.

## Üç yol

| | A. Birbaşa paylaşım (tövsiyə) | B. Qaralama | C. Hazır xidmət |
|---|---|---|---|
| TikTok icazəsi | `video.publish` | `video.upload` | — |
| Nə baş verir | Video avtomatik dərc olunur | Video TikTok tətbiqində bildiriş kimi gəlir, siz bir toxunuşla dərc edirsiniz | TikTok-un auditdən keçmiş planlama xidməti (Buffer, Later, Metricool kimi) |
| Audit | Direct Post auditi lazımdır, ona qədər yalnız sizə görünür | Tətbiqin adi yoxlaması kifayətdir | Xidmətin öz qaydaları və qiyməti |
| Hədd | Gündə 10 (bizim seçim) | 24 saatda 5 | Xidmətdən asılıdır |
| Bu PR-da | var | var (`TIKTOK_MODE=inbox`) | yoxdur, ayrıca iş |

## 1. Hazırlıq (bir dəfə)

1. **TikTok hesabı:** 8ulduz hesabı. Bio-ya «8ulduz.az» yazın, çünki TikTok-da postdakı keçid basılmır. Basılan veb-sayt keçidi üçün TikTok hesab növünə və ya izləyici sayına görə şərt qoya bilər. «Profili redaktə et → Vebsayt» görünmürsə, ünvanı hələlik bio-da mətn kimi saxlayın.
2. **Saytda iki səhifə.** TikTok tətbiq üçün Terms of Service və Privacy Policy ünvanı istəyir, ikisi də təsdiqlənmiş domendə olmalıdır.
   - Məxfilik siyasəti var: `https://8ulduz.az/mexfilik/`. Ora TikTok haqqında bir abzas əlavə etmək lazımdır: tətbiq yalnız 8ulduz hesabının öz tokenini saxlayır, oxucu məlumatı toplamır.
   - **İstifadə şərtləri səhifəsi yoxdur**, ayrıca əlavə edilməlidir (məsələn `https://8ulduz.az/sertler/`).

## 2. Developer hesabı və tətbiq

1. [developers.tiktok.com](https://developers.tiktok.com/)-a 8ulduz TikTok hesabı ilə daxil olun. Developer qeydiyyatını özünüz keçin: e-poçt təsdiqi və CAPTCHA sizdədir.
2. Profil ikonu → **Manage apps** → **Connect an app** → sahibi seçin (fərdi və ya təşkilat) → **Confirm**.
3. **Basic information** bölməsi:
   - **App icon:** 1024×1024 PNG/JPG, 5 MB-a qədər. Saytın loqosundan böyük nüsxə: `assets/icon-512.png` kiçikdir, 1024 ölçü lazımdır.
   - **App name:** «8ulduz». Adda sosial şəbəkə adı (TikTok) olmamalıdır.
   - **Category:** News.
   - **Description:** icazə səhifəsində görünür. Məsələn: «8ulduz.az xəbər saytının öz video xəbərlərini 8ulduz TikTok hesabında paylaşır.»
   - **Terms of Service URL** və **Privacy Policy URL:** yuxarıdakı iki səhifə.
   - **Platforms:** Web → Website URL `https://8ulduz.az/`.
4. **Products → Add products**:
   - **Login Kit:** Redirect URI `https://8ulduz.az/haqqinda/`, hərfbəhərf belə. Bu səhifədə skript yoxdur, ona görə kod ünvan sətrində qalır və heç bir statistikaya getmir.
   - **Content Posting API:** A yolu üçün **Direct Post** açarını yandırın.
5. **Scopes:**
   - `user.info.basic` avtomatik əlavə olunur;
   - A yolu üçün `video.publish`, B yolu üçün `video.upload`.

   İşlətmədiyiniz məhsul və icazəni əlavə etməyin: TikTok yazır ki, artıq icazə yoxlamanı gecikdirir.

## 3. Domen təsdiqi (URL properties)

Tətbiq səhifəsinin yuxarısında **URL properties** → Production rejimində olduğunuzu yoxlayın → **Verify properties**. 2024-09-09-dan sonra yaradılan tətbiqlərdə Website, Terms və Privacy ünvanları təsdiqlənməlidir.

Bizim yükləyici `FILE_UPLOAD` işlədir: video faylı birbaşa göndərilir, `PULL_FROM_URL` deyil. Ona görə videonun ünvanını təsdiqləmək lazım deyil, təsdiq yalnız tətbiqin qeydiyyatı üçündür.

**Variant 1: Domain, DNS ilə (tövsiyə, bütün alt domenləri əhatə edir)**

1. **Domain** seçin → `8ulduz.az` yazın → **Verify**. TikTok imza mətni verir.
2. 8ulduz.az-ın DNS-i Cloudflare-dədir (`gemma.ns.cloudflare.com`, `sage.ns.cloudflare.com`). Bunu edin:
   1. dash.cloudflare.com-a girin.
   2. **8ulduz.az** → **DNS** → **Records** → **Add record**.
   3. Type **TXT**, Name `@`, Content TikTok-un verdiyi mətn. Saxlayın.
3. TikTok-da yenidən **Verify** basın. DNS bir neçə dəqiqədən bir neçə saata qədər yayıla bilər, alınmasa sonra təkrarlayın.

**Variant 2: URL prefix, fayl ilə**

1. **URL prefix** seçin → `https://8ulduz.az/` yazın (www yox: `www.8ulduz.az` 302 ilə yönləndirir, TikTok 3xx-i qəbul etmir) → **Verify**.
2. TikTok-un verdiyi imza faylını yükləyin. Faylı **adını dəyişmədən** reponun kökünə, `main`-ə qoyun: ya GitHub veb-də **Add file → Upload files**, ya da faylı agentə verib commit etdirin. Fayl gizli deyil.
3. GitHub Pages 1–2 dəqiqədən sonra faylı `https://8ulduz.az/<fayl adı>` ünvanında verir. Brauzerdə açılırsa TikTok-da **Verify** basın.

## 4. Yoxlamaya (audit) nə göndərilir

**Mərhələ 1, tətbiqin yoxlaması (App review).** Tətbiq səhifəsində **App review** bölməsinə iki şey yazılır:

1. **Hər məhsul və icazə necə işlədilir.** Hazır mətn (ingiliscə, A yolu):
   > 8ulduz.az is an Azerbaijani news website. This app publishes short vertical news videos produced by 8ulduz.az itself (headlines and summaries rendered as video, no third-party footage) to the 8ulduz TikTok account. Login Kit is used once by the account owner to authorize the app (user.info.basic). video.publish is used to post each video with the Content Posting API (Direct Post, FILE_UPLOAD) from our server: before each post we query creator info and respect the account's privacy options, comment/duet/stitch settings and the daily posting limit, then check the post status.
2. **Demo video.** Ən çox 5 video, hər biri 50 MB-a qədər, tam axın görünməlidir. TikTok-un tələbləri:
   - videodakı sayt Website URL ilə eyni olmalıdır;
   - təsdiqlənməmiş tətbiq üçün Sandbox-da çəkilir.

   Təklif olunan ssenari:
   1. icazə ünvanı açılır, TikTok-da «Authorize» basılır;
   2. GitHub → Actions → «TikTok-da paylaş» → **Run workflow** (`sinaq`);
   3. jurnalda «paylaşıldı» sətri görünür;
   4. TikTok tətbiqində yalnız sizə görünən sınaq videosu açılır.

Sandbox-da 10-a qədər öz hesabınızı «Target users» kimi əlavə edə bilərsiniz, Sandbox-un ayrıca açarları olur. TikTok yazır ki, Sandbox ictimai video paylaşımına icazə vermir. Gizli paylaşımın Sandbox-da işləyib-işləmədiyini sənəd açıq demir, ona görə sınaqda yoxlayın.

Status sırası: Draft → In review → Live və ya Not approved (rəy ilə). Rədd olunsa, rəyi oxuyub düzəldin və yenidən göndərin.

**Mərhələ 2, Direct Post auditi (yalnız A yolu, ictimai paylaşım üçün).** Tətbiq «Live» olandan sonra TikTok-un Content Posting API audit formu doldurulur. TikTok onu Content Sharing Guidelines-dan keçid ilə verir: `developers.tiktok.com/application/content-posting-api`. Formada gündəlik istifadəçi və post təxmini soruşulur, TikTok gündəlik həddi bu təxminə görə qoyur. Bizim təxmin: 1 istifadəçi, gündə 10-a qədər video.

Diqqət: TikTok-un Direct Post üçün interfeys tələbləri var. Interfeysdə bunlar olmalıdır:
- hesabın adı;
- standart seçimi olmayan gizlilik siyahısı;
- şərh, duet və stitch düymələri;
- önizləmə;
- istifadəçinin açıq razılığı.

Bizim alət isə serverdə işləyir və interfeysi yoxdur. Yoxlayıcı interfeys tələb etsə, iki yol var: B yolu, ya da kiçik idarə səhifəsi (ayrıca iş).

**Müddət.**
- Tətbiq yoxlaması: TikTok-un yoxlama FAQ-ına istinadən «bir neçə gündən iki həftəyə qədər» (FAQ-ın özünü oxuya bilmədik, sitat üçüncü tərəf mənbəsindəndir).
- Direct Post auditi: TikTok rəsmi müddət yazmır.
- Rədd olunsa, hər yeni cəhd yenə bu qədər çəkir.

## 5. Açarlar və qoşulma

Açar, parol və kodu yalnız siz görür və yazırsınız.

1. Tətbiq səhifəsində **Client key** və **Client secret** var. PowerShell-də əvvəl 8ulduz hesabının GitHub açarını seçin:

```powershell
$env:GH_TOKEN = (gh auth token --user 8ulduz)
```

```powershell
gh secret set TIKTOK_CLIENT_KEY --repo 8ulduz/8ulduz
```

```powershell
gh secret set TIKTOK_CLIENT_SECRET --repo 8ulduz/8ulduz
```

   `gh` dəyəri soruşur, yapışdırıb Enter basın. Dəyər ekranda görünmür.

2. **İcazə.** Brauzerdə bu ünvanı açın. `<CLIENT_KEY>` yerinə öz client key-inizi yazın. B yolu üçün `video.publish` əvəzinə `video.upload` yazın.

```
https://www.tiktok.com/v2/auth/authorize/?client_key=<CLIENT_KEY>&scope=user.info.basic,video.publish&response_type=code&redirect_uri=https%3A%2F%2F8ulduz.az%2Fhaqqinda%2F&state=8ulduz
```

   8ulduz TikTok hesabı ilə girin və **Authorize** basın. Brauzer `https://8ulduz.az/haqqinda/?code=…` ünvanını açacaq. **Ünvan sətrini tam kopyalayın.**

3. **Qoşulma.** GitHub → 8ulduz/8ulduz → **Actions** → «TikTok-da paylaş» → **Run workflow** → **kod** sahəsinə yapışdırın → **Run workflow**.
   - Kod bir dəfəlikdir və bir neçə dəqiqə işləyir, tez edin.
   - Kod env-ə qoyulmur və jurnalda gizlədilir. client_secret olmadan onunla heç nə etmək olmur.
   - Jurnalda belə sətir görünməlidir: «qoşuldu — 8ulduz (@…), görünmə seçimləri: …; icazələr: user.info.basic,video.publish; token 365 gün işləyir».

4. **Sınaq.** Auditə qədər TikTok-da hesabı gizli edin: Settings → Privacy → **Private account**. Sonra **Run workflow** → **sinaq** işarəsi → Run. İş ffmpeg ilə 6 saniyəlik 9:16 sınaq videosu hazırlayıb yalnız sizə görünən kimi paylaşır.

5. **Audit keçəndən sonra** hesabı yenidən ictimai edin. Gizli hesabda `PUBLIC_TO_EVERYONE` seçimi olmur, iş axını videonu yenə `SELF_ONLY` göndərər və jurnalda bunu yazar.

Ehtiyat yol (istəyə bağlı): refresh tokeni özünüz alıbsınızsa, `gh secret set TIKTOK_REFRESH_TOKEN --repo 8ulduz/8ulduz` ilə yazın. İş axını keşdəki token itəndə ona keçir. Sirri yeniləsəniz, iş köhnə zəncir əvəzinə onu götürür.

## 6. Necə işləyir

- **Tətik.** Video modulu videonu hazırlayıb bu iş axınını çağırır (`workflow_call`, bölmə 7). Əl ilə də olar: **Run workflow** (`kod`, `sinaq`). PR-da ayrıca `sinaq-video` işi ffmpeg ilə əsl video hazırlayır və yükləyicini açarsız, saxta TikTok ilə yoxlayır.
- **Seçim.** Ən təzə video, dövrədə bir dənə. Video 12 saatdan köhnə olmamalıdır. Əvvəl getmiş video getmir: ad, fayl heşi və başlıq yoxlanır.
- **Mənbə qaydası (qırmızı xətt 2).** Videonun xəbəri (`source`, `sourceUrl`, `items`) saytın öz qaydasından (`policyViolation`) keçir. Xarici mənbədən Azərbaycan mövzusu və müxalifət mənbəyi düşür.
- **Ardıcıllıq:**
  1. hesab məlumatı (`creator_info`);
  2. `video/init` (`FILE_UPLOAD`);
  3. fayl göndərilir (64 MB-a qədər bir hissədə, böyük fayl 10 MB-lıq hissələrlə);
  4. status: `PUBLISH_COMPLETE`, `FAILED` (səbəbi ilə), emal davam edirsə növbəti dövrədə yenə yoxlanır.
- **Görünmə.** `PUBLIC_TO_EVERYONE` hesabın seçimlərində yoxdursa (audit yoxdur, hesab gizlidir), video `SELF_ONLY` göndərilir və jurnalda bu yazılır. Şərh, duet və stitch hesabın öz ayarı ilə gedir.
- **Mətn:** başlıq, izah, «Ətraflı: 8ulduz.az (keçid profildədir)», haşteqlər (#8ulduz #xəbərlər #Azərbaycan və modulun verdikləri). TikTok-da keçid basılmır, sayt bio-dadır.
- **Token.**
  - Ömür: TikTok sənədində access token 24 saat, refresh token 365 gün; başqa səhifədə 2 saat və 180 gün yazılıb. Kod TikTok-un cavabındakı rəqəmi işlədir.
  - Yeniləmə: TikTok hər yeniləmədə yeni refresh token qaytarır, yeniləmə avtomatikdir. Zəncir `actions/cache`-də AES-256-GCM ilə şifrəli saxlanır. Açar `TIKTOK_CLIENT_SECRET`-dən alınır, PR işləri onu oxuya bilmir.
  - Bitmə: tokenin bitməsinə 14 gün qalanda jurnalda «DİQQƏT» yazılır. TikTok refresh tokenin ömrünü uzatmırsa, ildə bir dəfə bölmə 5-in 2–3-cü addımını təkrarlayın.
- **Jurnal.** GitHub → Actions → «TikTok-da paylaş» → son iş, iş xülasəsində «TikTok» bölməsi. Açar, token və kod jurnala düşmür.

## 7. Video modulu ilə qoşulma (müqavilə)

Video modulu hər video üçün eyni adlı iki fayl yazır: `<ad>.mp4` + `<ad>.json`. Onları artifact kimi yükləyib bu işi çağırır:

```yaml
jobs:
  video:
    # … videonu hazırlayır, sonra:
    #   - uses: actions/upload-artifact@330a01c490aca151604b8cf639adc76d48f6c5d4 # v5
    #     with: { name: tiktok-video, path: out/tiktok/, retention-days: 1 }
  tiktok:
    needs: video
    uses: ./.github/workflows/tiktok.yml
    with:
      artifact: tiktok-video
    secrets: inherit
```

`<ad>.json`:

| Sahə | Məcburi | Nə |
|---|---|---|
| `id` | bəli | Videonun sabit adı, məs. xəbər nömrəsi. Eyni `id` ikinci dəfə getmir. |
| `own` | bəli, `true` | Video bizim ffmpeg ilə hazırlanıb, başqasının görüntüsü yoxdur. |
| `title` | bəli | Başlıq: mətnin birinci sətri. |
| `summary` | yox | İzah, 1200 simvola qədər. |
| `createdAt` | yox | ISO vaxt. 12 saatdan köhnə video getmir. |
| `hashtags` | yox | Əlavə haşteqlər, ən çox 5 (cəmi 8). |
| `source`, `sourceUrl`, `category`, `lang` | xəbərdən video olanda bəli | Lentdəki xəbərin sahələri, mənbə qaydası üçün. |
| `items` | yox | Bir neçə xəbərdən video: `[{ title, source, sourceUrl, category }]`, hər biri qaydadan keçir. |
| `aigc` | yox | Realistik AI səhnə və ya insan varsa `true` (TikTok etiketi). |
| `text` | yox | Videoda gedən izah. Varsa mətndə `summary`-nin yerinə o yazılır. |
| `coverMs` və ya `cover_s` | yox | Üz qabığının anı: millisaniyə və ya saniyə (standart 1 s). |
| `duration` | yox | Saniyə. Hesabın həddindən uzundursa göndərilmir. |

JSON-da başqa saytın video keçidi (`video`, `videoUrl`, `src`, `clips`) olmamalıdır. Belə video getmir.

**Video modulu (`video-xeber.cjs`, FB/IG video sessiyası).** O, `node .github/scripts/video-xeber.cjs <giriş.json> <çıxış.mp4>` ilə işləyir. Çıxışda `<çıxış>.mp4`, `<çıxış>.json` (`duration`, `width`, `height`, `bytes`, `cover_s`, `voice`) və `<çıxış>.jpg` yaranır. Yükləyici bu `<çıxış>.json`-u oxuyur: `text`, `cover_s` və `duration`-u tanıyır. Videonun TikTok-a getməsi üçün modulda iki əlavə lazımdır:

1. `<çıxış>.json`-a giriş xəbərinin sahələri yazılmalıdır: `id`, `title`, `summary`, `text`, `source`, `sourceUrl`, `category`, `lang`, `publishedAt`, üstəgəl `"own": true`.
2. ffmpeg əmrinə `-metadata comment=8ulduz.az` əlavə edilməlidir.

Bunlar olmasa video «öz videomuz» sayılmır və ötürülür. Bunu test yoxlayır.

`<ad>.mp4`:
- **Format:** MP4, H.264 (+AAC), 1080×1920, 23–60 kadr/s.
- **Uzunluq və ölçü:** hesabın həddindən uzun olmamalıdır (`max_video_post_duration_sec`, adətən 3–10 dəq), 4 GB-dan kiçik.
- **Metadata:** `-movflags +faststart` və `-metadata comment=8ulduz.az`. Bu nişan olmasa video getmir.

Yuxarıdakı «8ulduz.az» yazısı TikTok-un öz yazılarının altında qalmasın. Yuxarıdan təxminən 8–10% və aşağıdan ~20% hissəni TikTok-un düymələri örtür.

Sınaq videosu (`node .github/scripts/tiktok.cjs sinaq <qovluq>`) bu müqaviləyə uyğundur, nümunə kimi işlədilə bilər.

## 8. Tənzimləmə (Variables, istəyə bağlı)

| Ad | Standart | Nə |
|---|---|---|
| `TIKTOK` | — | `0`: TikTok tam söndürülür. |
| `TIKTOK_MODE` | `direct` | `inbox`: B yolu, qaralama. |
| `TIKTOK_PRIVACY` | `PUBLIC_TO_EVERYONE` | Hesabda yoxdursa `SELF_ONLY`. |
| `TIKTOK_MAX_DAY` | 10 (qaralama 5) | 24 saatda ən çox; 15-dən (qaralama 5-dən) çox olmaz. |
| `TIKTOK_MIN_GAP_MIN` | 60 | Videolar arası dəqiqə. |
| `TIKTOK_MAX_AGE_H` | 12 | Bundan köhnə video getmir. |
| `TIKTOK_BRAND_ORGANIC` | — | `1`: TikTok-un «öz biznesinin reklamı» işarəsi (Brand Organic). Xəbər üçün lazım deyil. |
| `TIKTOK_REDIRECT_URI` | `https://8ulduz.az/haqqinda/` | Tətbiqdəki Redirect URI başqadırsa. |

## Mənbələr (TikTok for Developers və TikTok qaydaları, 2026-11-22 oxunub)

- Content Posting API, başlanğıc: https://developers.tiktok.com/doc/content-posting-api-get-started
- Direct Post: https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
- Creator info: https://developers.tiktok.com/doc/content-posting-api-reference-query-creator-info
- Status: https://developers.tiktok.com/doc/content-posting-api-reference-get-video-status
- Fayl göndərmə (hissələr, formatlar, domen təsdiqi): https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide
- Qaralama (Upload): https://developers.tiktok.com/doc/content-posting-api-reference-upload-video
- Paylaşma qaydaları (audit, hədd, su nişanı, qəbuledilməz istifadə): https://developers.tiktok.com/doc/content-sharing-guidelines
- Tətbiq yaratmaq, URL properties: https://developers.tiktok.com/doc/getting-started-create-an-app
- Tətbiq yoxlaması qaydaları: https://developers.tiktok.com/doc/app-review-guidelines
- Sandbox: https://developers.tiktok.com/doc/add-a-sandbox
- OAuth, Login Kit və tokenin yenilənməsi:
  - https://developers.tiktok.com/doc/login-kit-web
  - https://developers.tiktok.com/doc/oauth-user-access-token-management
  - https://developers.tiktok.com/doc/oauth-refresh-a-user-access-token
- İcazələr (scopes): https://developers.tiktok.com/doc/tiktok-api-scopes
- Orijinallıq və FYF: https://www.tiktok.com/community-guidelines/en/integrity-authenticity
- Müəllif hüququ: https://www.tiktok.com/legal/page/global/copyright-policy/en
