# YouTube Shorts-da video xəbərlər

**Niyə (2026-11-22 yoxlaması).** Google saytın Videolentini indeksləmir:

- `#/videolent?r=` ünvanında `#`-dan sonrası ayrıca səhifə sayılmır;
- videonu indeksləmək üçün hər videonun öz səhifəsi olmalıdır;
- başqasının X videosundan qurulan yüzlərlə səhifə Google-un spam qaydalarına düşür.

Google-un video nəticələrinə ən real yol öz, orijinal videolarımızın YouTube Shorts-da olmasıdır. Google Shorts-u axtarışda «Qısa videolar» bölməsində göstərir.

| Nə | Kim | Harada |
|---|---|---|
| Videonu hazırlamaq, yuxarıda «8ulduz.az» yazısı | video modulu | `.github/scripts/video-xeber.cjs`, `.github/workflows/sosial-video.yml` |
| Videonu YouTube-a yükləmək, başlıq, təsvir, teqlər, təkrarın qarşısı | hazırdır | `.github/scripts/youtube.cjs`, `.github/workflows/youtube.yml`, `tests/youtube.test.cjs` |
| Kanal, Google Cloud layihəsi, açarlar | **siz** | aşağıdakı addımlar |

Açar yoxdursa iş axını heç nə göndərmir, sakitcə ötürür. Xəbər axınından ayrıdır: saytın sürətinə və dəqiqəlik yenilənməyə toxunmur, repoya yazmır.

## Qısa: sizin addımlarınız

1. YouTube kanalı açın: «8ulduz.az» ([1](#1-kanal)).
2. Google Cloud-da layihə yaradın, «YouTube Data API v3»-ü yandırın ([2](#2-google-cloud-layihəsi)).
3. OAuth razılıq ekranını qurun və tətbiqi **«In production»** edin. «Testing» rejimində token 7 gündə ölür ([3](#3-oauth-razılıq-ekranı)).
4. «Web application» klienti yaradın ([4](#4-oauth-klienti)).
5. OAuth Playground-da refresh token alın ([5](#5-refresh-token-oauth-playground)).
6. Üç açarı `gh secret set` ilə GitHub-a yazın ([6](#6-açarları-github-a-yazın)).
7. Actions → «YouTube Shorts» → `yoxla`, sonra `sinaq` ([7](#7-yoxlayın)).

Açarı, parolu və kodu heç kimə göndərməyin, söhbətə yapışdırmayın. Onları yalnız siz görürsünüz və yalnız GitHub Secrets-ə yazırsınız.

## Əvvəlcə bilməli olduğunuz qaydalar

1. **Yalnız öz videolarımız.** X-dəki F1, NBA, Fox News, klub videoları (`data/reels.json`) YouTube-a **heç vaxt** getmir. YouTube-un qaydası belədir: 1 dəqiqədən uzun Shorts-a müəllif hüququ iddiası (Content ID) gələrsə, video bütün dünyada bloklanır. Təkrar pozuntu kanalı da riskə salır. Yükləyici yalnız bu şərtlərin hamısı ödənəndə göndərir:
   - JSON-da `"own": true` var;
   - faylın metadatasında «8ulduz.az» nişanı var (`ffmpeg -metadata comment=8ulduz.az`);
   - JSON-da başqa saytın video keçidi yoxdur, xəbərin mənbəyi video və ya sosial şəbəkə saytı deyil;
   - video `data/reels.json`-da deyil;
   - video şaquli və ya kvadratdır və **60 saniyədən uzun deyil**. Bu hədd dəyişəndə də 60-dan yuxarı qalxmır.
2. **Qırmızı xətt 2.** Videonun aid olduğu hər xəbər saytın öz mənbə qaydasından (`policyViolation`) keçir. Xarici mənbədən Azərbaycan və rəhbərlik mövzusu, müxalifət mənbəyi olan video yüklənmir. Qayda faylı oxunmasa, iş dayanır və heç nə yüklənmir.
3. **Kvota.** 2026-06-01-dən yükləmənin ayrıca kvotası var: gündə 100 yükləmə, hər biri 1 vahid. Kvota Sakit okean vaxtı ilə gecə yarısı yenilənir: Bakı vaxtı ilə qışda 12:00, yayda 11:00.
   - Bizim seçim: gündə ən çox 8 video, aralarında ən az 30 dəqiqə. «Günün icmalı» aranı gözləmir. Gündəlik hava videosu bu 8-ə sayılmır (xəbər videosunun həddinə də sayılmır), yəni gündə 8 xəbər + 1 hava.
   - Kvota dolsa, yükləyici yenilənməyə qədər fasilə verir. Kanalın öz həddi dolsa, 24 saat fasilə verir.
4. **Audit lazım deyil.** 2020-07-28-dən 2026-11-02-dək yoxlanmamış layihənin videoları məcburi gizli (private) olurdu. YouTube 2026-11-02-də bu məhdudiyyəti götürdü. İndi video birbaşa ictimai (public) çıxır. YouTube videonu yenə də gizli qoysa, jurnalda «DİQQƏT» yazılır.
5. **Token.** Razılıq ekranı «Testing» rejimindədirsə, Google-un refresh tokeni **7 gündə** ölür. Ona görə tətbiqi «In production» edin (3-cü addım).
   - Google tətbiqi yoxlamayıbsa, icazə verəndə «Google hasn't verified this app» xəbərdarlığı çıxır. Öz hesabınız üçün bu normaldır.
   - Token 6 ay işlənməsə və ya icazəni geri götürsəniz də ölür.
6. **Təsvirdəki keçid.** Hər videonun təsvirində saytın səhifəsi var: xəbərin paylaşma səhifəsi `https://www.8ulduz.az/<nömrə>?h=<saat>` və ya icmal səhifəsi.
   - YouTube Shorts təsvirindəki keçidi basılan etməyə bilər.
   - Kanalın «haqqında» bölməsindəki keçid basılır, ona görə sayt ünvanını oraya mütləq yazın (1-ci addım).
7. **Süni intellekt bildirişi.** Səs SARA modelidir, amma real insanı və ya real hadisəni təqlid etmir, ona görə bildiriş tələb olunmur və `containsSyntheticMedia` `false` gedir. Video modulu JSON-da `"aigc": true` yazsa, YouTube-a bildirilir.

## 1. Kanal

1. youtube.com-a 8ulduz-un Google hesabı ilə daxil olun (məsələn, Search Console-dakı hesab).
2. Sağ yuxarıda şəkil → **Kanal yaradın** (Create a channel). Ad: **8ulduz.az**. Şirkət adı ilə yaradılan kanal «Brand Account» olur, belə də yaxşıdır.
3. YouTube Studio → **Fərdiləşdirmə** (Customization) → **Əsas məlumat**:
   - Ad: **8 Ulduz | 8ulduz.az** (2026-11-24: kanalın adı «8ULDUZ» idi, təsviri və açar sözləri boş idi; YouTube «8 ulduz» axtarışını iki söz kimi oxuyur və kanal çıxmırdı, «8ulduz» axtaranda çıxırdı). Tutacaq (@8ULDUZ) dəyişmir.
   - Təsvir: «8 Ulduz (8ulduz.az) — Azərbaycan və dünyadan son xəbərlər, hər dəqiqə yenilənir.»
   - **Keçidlər** → `https://8ulduz.az/`.
4. Studio → **Ayarlar** → **Kanal** → **Qabaqcıl ayarlar** → Auditoriya: «Xeyr, uşaqlar üçün deyil».
   Eyni yerdə (**Ayarlar** → **Kanal** → **Əsas məlumat**) **Açar sözlər**: `8 ulduz`, `8ulduz`, `8ulduz.az`, `səkkiz ulduz`, `xəbərlər`, `Azərbaycan xəbərləri`. Yükləyici hər videonun teqlərinə və təsvirinə də hər iki yazılışı qoyur (`youtube.cjs` `BASE_TAGS`, `TAGLINE`).
5. Studio → **Ayarlar** → **Yükləmə standartları** → Dil: Azərbaycan dili. Bu istəyə bağlıdır, yükləyici dili özü də göndərir.
6. İstəyə bağlı: youtube.com/verify — telefonla təsdiq. Shorts üçün şərt deyil.

## 2. Google Cloud layihəsi

1. console.cloud.google.com → yuxarıda layihə seçimi → **New project** → ad: `8ulduz-youtube` → Create.
2. **APIs & Services** → **Library** → «YouTube Data API v3» → **Enable**.

Ödəniş kartı lazım deyil: YouTube Data API pulsuzdur.

## 3. OAuth razılıq ekranı

Google Cloud → **Google Auth Platform** (köhnə adı «OAuth consent screen»):

1. **Branding**:
   - App name: `8ulduz`;
   - User support email: öz ünvanınız;
   - Developer contact: öz ünvanınız;
   - istəyə bağlı: App home page `https://8ulduz.az/`, Privacy policy `https://8ulduz.az/mexfilik/`.
2. **Audience**: User type **External**, sonra **Publish app** → **In production**. Bu vacibdir, yoxsa token 7 gündə ölür. Google yoxlama istəsə belə, öz hesabınız üçün işləyir.
3. **Data access** → **Add or remove scopes** → bu ikisini seçin:
   - `https://www.googleapis.com/auth/youtube.upload` — video yükləmək;
   - `https://www.googleapis.com/auth/youtube.readonly` — kanalın adını görmək və eyni videonun iki dəfə getməməsi üçün son videoları yoxlamaq (istəyə bağlı, amma tövsiyə olunur).

## 4. OAuth klienti

1. Google Auth Platform → **Clients** → **Create client**.
2. Application type: **Web application**, ad: `8ulduz GitHub`.
3. **Authorized redirect URIs** → **Add URI** → `https://developers.google.com/oauthplayground`.
4. **Create**. Ekranda **Client ID** və **Client secret** görünür. Google sirri sonradan bir daha göstərməyə bilər, ona görə JSON-u yükləyin və ya pəncərəni bağlamayın, 6-cı addımda lazım olacaq.

## 5. Refresh token (OAuth Playground)

1. developers.google.com/oauthplayground səhifəsini açın.
2. Sağ yuxarıda dişli çarx (⚙):
   - **Use your own OAuth credentials** işarələyin;
   - 4-cü addımdakı Client ID və Client secret-i yazın;
   - «Access type» **Offline** qalsın.
3. Solda **Step 1** → aşağıdakı xanaya bunu yazın və **Authorize APIs** basın:
   `https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly`
4. Google hesabını seçin:
   - kanal Brand Account-dadırsa, növbəti ekranda **8ulduz.az kanalını** seçin;
   - «Google hasn't verified this app» → **Advanced** → **Go to 8ulduz (unsafe)** → hər iki icazəni işarələyin → **Continue**.
5. **Step 2** → **Exchange authorization code for tokens**. Sağda **Refresh token** görünür, `1//` ilə başlayır. Onu kopyalayın.
6. Playground pəncərəsini bağlayın. İstəyə bağlı: 4-cü addımdakı redirect URI-ni sonra silə bilərsiniz, token işləməyə davam edir.

## 6. Açarları GitHub-a yazın

Öz kompüterinizdə PowerShell-də. Hər əmr dəyəri soruşur («Paste your secret»): yapışdırıb Enter basın. Dəyər ekranda görünmür və əmrlər tarixçəsinə düşmür.

```powershell
gh secret set YOUTUBE_CLIENT_ID --repo 8ulduz/8ulduz
```

```powershell
gh secret set YOUTUBE_CLIENT_SECRET --repo 8ulduz/8ulduz
```

```powershell
gh secret set YOUTUBE_REFRESH_TOKEN --repo 8ulduz/8ulduz
```

`gh` 8ulduz hesabı ilə işləməlidir (`gh auth status`). Başqa yol: GitHub → 8ulduz/8ulduz → Settings → Secrets and variables → Actions → **New repository secret**.

## 7. Yoxlayın

1. GitHub → Actions → **YouTube Shorts** → **Run workflow** → `əmr: yoxla`. Jurnalda «kanal — 8ulduz.az (https://www.youtube.com/channel/…)» yazılmalıdır. Kvotaya dəymir, heç nə yüklənmir.
2. Yenə **Run workflow** → `əmr: sinaq`. 6 saniyəlik sınaq videosu (yuxarıda «8ulduz.az») **gizli** (private) yüklənir. Jurnalda ünvan yazılır. YouTube Studio → Məzmun bölməsində görünəcək, baxandan sonra silin.

Hər şey qaydasındadırsa, videolar özü gedəcək: video modulu hər 30 dəqiqədən bir yoxlayır, vaxtı çatanda (2 saatdan bir, Bakı vaxtı 8:00–23:59) video hazırlayır, hazır video YouTube-a da yüklənir.

## 8. Video modulu ilə qoşulma

Qoşulub. Video modulu (`.github/scripts/video-xeber.cjs`, `.github/workflows/sosial-video.yml`) videonu hazırlayıb yoxlayır, sonra `youtube` işi `youtube.yml`-i çağırır:

```yaml
  youtube:
    needs: video
    if: ${{ !cancelled() && github.ref == refs/heads/main && needs.video.outputs.paylas == 1 && needs.video.outputs.yoxlandi == 1 }}
    uses: ./.github/workflows/youtube.yml
    with:
      artifact: video-xeber
    secrets:
      YOUTUBE_CLIENT_ID: ${{ secrets.YOUTUBE_CLIENT_ID }}
      YOUTUBE_CLIENT_SECRET: ${{ secrets.YOUTUBE_CLIENT_SECRET }}
      YOUTUBE_REFRESH_TOKEN: ${{ secrets.YOUTUBE_REFRESH_TOKEN }}
```

- Bu iş TikTok işi ilə eyni şərtlərlə işləyir: yalnız `main`-də, əsl paylaşım dövrəsində (`paylas == 1`: PR nümunəsi və `paylas=false` önizləməsi getmir) və video «Videonu yoxla» addımından keçəndə (`yoxlandi == 1`).
- Facebook və ya Instagram alınmasa da hazır video YouTube-a gedir. Bu işə yalnız YouTube sirləri verilir.
- «Xəbər seç» addımı (`VIDEO_ACAR`) Facebook, TikTok **və ya YouTube** açarı olanda video hazırlayır. YouTube Facebook-dan asılı deyil.
- Modul ən çox 59 saniyəlik video hazırlayır (`MAX_S = 59`), YouTube həddi 60 saniyədir.

Artefaktda `video.mp4` və `video.json` var. `xeber.json` kimi cütü olmayan fayllar oxunmur. Müqavilə TikTok yükləyicisi ilə eynidir, bir JSON hər ikisinə gedir:

- `<ad>.mp4`: şaquli (1080×1920), H.264 + AAC, `-movflags +faststart -metadata comment=8ulduz.az`. Konteynerin müddəti **≤ 60,0 s** olmalıdır: 60,02 s da qəbul edilmir.
- `<ad>.json`: video modulunun yazdığı sahələr `{ id, own: true, title, summary, text, source, sourceUrl, category, lang, publishedAt, duration, … }`. Təsvirdə `summary` gedir; o boşdursa, videodakı izahın (`text`) əvvəli. Gələcək video növləri üçün istəyə bağlı sahələr:
  ```json
  { "kind": "icmal", "url": "https://8ulduz.az/…", "createdAt": "ISO", "hashtags": ["…"],
    "items": [{ "title": "…", "source": "…", "sourceUrl": "…" }], "aigc": false }
  ```

Məzmun növləri (`kind`):

| `kind` | Nə | Keçid | Mənbə yoxlaması |
|---|---|---|---|
| `xeber` | əsas xəbər | `url`; yoxdursa `https://www.8ulduz.az/<nömrə>?h=<saat>` (`publishedAt`-dan) | `source` + `sourceUrl` |
| `icmal` | «Günün icmalı», 09:00 və 19:00 (`updater.write_digest`); `id`: `icmal-<tarix>-seher` / `-axsam` | `https://8ulduz.az/icmal/<tarix>-seher/` | hər `items` sətrində `source` + `sourceUrl` **olmalıdır**, yoxdursa yüklənmir |
| `hava`, `valyuta`, `bazar` | hava və valyuta (`data/markets.json`) | `url` (saytın səhifəsi), yoxdursa ana səhifə | xəbər yoxdur, yoxlanmır |

Video modulu əsas xəbərdən (`xeber`) və 2026-11-23-dən gündəlik hava proqnozundan (`hava`, `video-hava.cjs`, `url`: `https://8ulduz.az/bolme/hava/`) video hazırlayır; icmal və valyuta videoları əlavə olunanda yükləyici onları da `kind`-ə görə tanıyır. Hava/valyuta/bazar videosunun keçidi hər gün eyni səhifədir: kanalda təkrar yalnız tarixli başlıqla axtarılır (keçidlə axtarış xəbər və icmal üçündür). Keçid yalnız 8ulduz.az-a ola bilər: başqa saytın ünvanı verilsə, ana səhifə yazılır.

## 9. Tənzimləmə (Variables, istəyə bağlı)

GitHub → Settings → Secrets and variables → Actions → **Variables**:

| Ad | Standart | Nə edir |
|---|---|---|
| `YOUTUBE` | — | `0` — YouTube-u söndürür |
| `YOUTUBE_PRIVACY` | `public` | `unlisted` və ya `private` (məsələn ilk günlər) |
| `YOUTUBE_MAX_DAY` | `8` | 24 saatda ən çox neçə video, hava videosundan başqa (ən çox 50, kvota 100-dür) |
| `YOUTUBE_MIN_GAP_MIN` | `30` | iki video arasında ən az dəqiqə (icmal gözləmir) |
| `YOUTUBE_MAX_AGE_H` | `12` | bundan köhnə video yüklənmir |
| `YOUTUBE_MAX_S` | `60` | ən uzun video, saniyə (60-dan yuxarı qalxmır) |
| `YOUTUBE_NOTIFY` | — | `0` — abunəçilərə bildiriş göndərilmir |

## 10. Token köhnələndə

Jurnalda «token alınmadı (invalid_grant)» yazılırsa:

1. Google Auth Platform → **Audience**: tətbiq «In production»-dırmı? Deyilsə, **Publish app** basın.
2. 5-ci addımı təkrarlayın. Yeni refresh token alın.
3. `gh secret set YOUTUBE_REFRESH_TOKEN --repo 8ulduz/8ulduz` ilə yeniləyin. Client ID və secret dəyişmir.

## Necə işləyir

- Video modulu videonu artifact kimi verir, `youtube.yml` onu alır. Bir dövrədə bir video yüklənir: əvvəl sınaq videosu, sonra icmal, sonra ən təzə xəbər.
- Yükləmədən əvvəl yoxlanır:
  - öz videomuzdurmu;
  - mənbə qaydasından keçirmi;
  - MP4 qutularına görə ölçüsü və müddəti necədir (ffprobe lazım deyil);
  - 24 saatlıq hədd, ara və fasilə.
- Başlıq xəbərin başlığıdır, ən çox 100 simvol.
- Təsvirdə xülasə (icmalda xəbərlərin siyahısı), «Ətraflı:» keçidi, mənbə, saytın bir sətirlik təqdimatı və `#8ulduz #xəbərlər #Shorts` var, ən çox 5000 bayt.
- Teqlər: 8ulduz, xəbərlər, bölmə adı və s., cəmi ≤ 500 simvol. Kateqoriya «News & Politics» (25), dil `az`, «uşaqlar üçün deyil».
- Eyni video iki dəfə getmir:
  - yüklənənlərin nömrəsi, fayl izi və başlıq izi `.youtube/state.json`-da 30 gün saxlanır (actions/cache, içində açar yoxdur);
  - keş itsə, yükləmədən əvvəl kanalın son 50 videosuna baxılır: eyni başlıq və ya eyni keçid varsa, video yüklənmir.
- Yükləmə «resumable» üsulu ilədir: əlaqə kəsilsə, qalan hissə göndərilir, fayl yenidən göndərilmir.
- Açar, token və yükləmə ünvanı jurnala yazılmır.
- Heç nə alınmayanda iş qırmızı olur, GitHub sizə xəbər verir. Ötürmə və fasilə yaşıl qalır.
