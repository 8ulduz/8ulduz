# TikTok-da video xəbərlər

Sahibin göstərişi (2026-11-22): «Tik-tok səhifəmizdə videolar verilsin. Videolarda başda 8ulduz.az yazılsın.»

| Nə | Kim | Harada |
|---|---|---|
| Videonu hazırlamaq, yuxarıda «8ulduz.az» yazısı | video modulu | `video-xeber.cjs`, `sosial-video.yml` |
| Videonu TikTok-a göndərmək, statusu yoxlamaq, token | hazırdır | `.github/scripts/tiktok.cjs`, `.github/workflows/tiktok.yml`, `tests/tiktok.test.cjs` |
| Yoxlama (App review) üçün demo video | hazırdır | `.github/workflows/tiktok-demo.yml`, `.github/scripts/tiktok-demo.cjs` |
| TikTok tətbiqi, yoxlama, açarlar, qoşulma | **siz** | aşağıdakı [bələdçi](#bələdçi-sizin-addımlarınız) |

Açar yoxdursa iş axını heç nə göndərmir, sakitcə ötürür. Xəbər axınından ayrıdır: saytın sürətinə və dəqiqəlik yenilənməyə toxunmur.

## Qərar (2026-11-23): hansı yol real

Məqsəd: videolar `SELF_ONLY` yox, hamıya görünsün. TikTok-un 2026-11-23-də yenidən oxunmuş qaydalarına görə üç yol var.

| | A. Birbaşa paylaşım (Direct Post auditi) | **B. Qaralama (tövsiyə)** | C. Auditdən keçmiş hazır xidmət |
|---|---|---|---|
| İcazə | `video.publish` | `video.upload` | xidmətin öz tətbiqi |
| Nə baş verir | Video özü ictimai dərc olunur | Video TikTok tətbiqinə bildiriş kimi gəlir, siz «Hamı» seçib dərc edirsiniz | Xidmət videonu bizim hesaba ictimai dərc edir |
| Görünmə | Audit yoxdursa yalnız `SELF_ONLY`, gizli hesab | **Hamı** (siz seçirsiniz), hesab ictimai | Hamı |
| TikTok yoxlaması | Tətbiq yoxlaması + Direct Post auditi | Yalnız tətbiq yoxlaması, audit lazım deyil | Bizdə yoxlama yoxdur |
| Sizin işiniz | Yoxdur | Hər videoya ~20 saniyə: bildirişə toxunmaq, mətni yapışdırmaq, «Dərc et» | Xidmətdə qeydiyyat, ödəniş |
| Hədd | ~15/gün | 24 saatda ən çox 5 gözləyən qaralama | Xidmətdən asılı |
| Şans | **Çox aşağı** (aşağıda səbəb) | Real (risk var, aşağıda) | Yüksək, amma pullu |
| Bu PR-da | kod hazırdır, standart deyil | **standartdır** (`TIKTOK_MODE` boş = `auto`) | yoxdur, ayrıca iş |

**Niyə A yox.** Bizim alət öz məzmunumuzu öz hesabımıza avtomatik yükləyir. TikTok-un qaydaları məhz bunu qəbul etmir:

1. Content Sharing Guidelines, «Intended Use»: tətbiq «intended for a wide audience, not limited to internal groups/private use» olmalıdır. Qəbuledilməz nümunə: «A utility tool to help upload contents to the account(s) you or your team manages».
2. App Review Guidelines: «Apps must not be for private or personal use».
3. Direct Post UX qaydaları hər post üçün insanın əlini tələb edir: görünmə siyahıdan əl ilə seçilir və standart dəyəri olmur; şərh, duet və stitch öz-özünə açılmır; önizləmə göstərilir; istifadəçi açıq razılıq vermədən TikTok-a heç nə göndərilmir. Serverdə, insansız işləyən alət bunu dürüst göstərə bilməz.
4. TikTok bir developerə yazılı cavab verib (2026-10-29, Postiz layihəsinin GitHub müzakirəsi, üçüncü tərəf mənbəsi). Cavabda yalnız təşkilatın öz tək TikTok hesabına paylaşan tətbiq «personal or internal use, which is not eligible for approval» sayılır. Orada həm də yazılıb ki, demo videonu, brendi və ya icazə siyahısını dəyişmək bu səbəbi aradan qaldırmır.

Ona görə A üçün ərizə vermək tövsiyə olunmur. Alətin işini başqa cür (məsələn, çox istifadəçili xidmət kimi) təsvir etmək də olmaz. Bu, yanlış məlumat olar və tətbiqin bağlanmasına səbəb ola bilər.

**Niyə B.**
- TikTok-un «yalnız gizli görünmə» məhdudiyyəti Direct Post-a aiddir («All content posted by unaudited clients will be restricted to private viewing mode»). Upload (qaralama) sənədində belə məhdudiyyət yoxdur.
- Developerlər qaralamanın auditsiz işlədiyini yazır.
- Qaralamada TikTok-un UX qaydaları TikTok-un öz tətbiqində ödənir: görünməni, şərhi, açıqlamanı siz seçirsiniz.
- Video sizin əlinizlə, TikTok tətbiqindən dərc olunur. Yəni adi post kimi hamıya görünür və tövsiyə lentinə düşə bilər.

**B-nin riski.** Tətbiq yoxlamasında da «private or personal use» qaydası var. Yoxlayıcı `video.upload` üçün də rədd edə bilər. Bunu qabaqcadan bilmək olmur. Ona görə ərizə mətni dürüstdür: tətbiq 8ulduz-un öz hesabı üçündür. Rədd olunsa iki yol qalır:
- C yolu;
- videoları əl ilə yükləmək: iş xülasəsindən videonu və mətni götürmək.

**C haqqında.** Buffer, Later, Metricool kimi planlama xidmətləri çox istifadəçiyə xidmət edir və TikTok-a ictimai avtomatik paylaşım təklif edir. Bu, TikTok-un nəzərdə tutduğu «wide audience» tətbiqidir, biz isə onun müştərisi oluruq. Tam avtomatik ictimai paylaşım üçün qaydaya uyğun yeganə yol budur, amma pullu və üçüncü tərəfdən asılıdır. Seçməzdən əvvəl xidmətin API ilə TikTok paylaşımını və qiymətini yoxlamaq lazımdır. Seçim sizindir. Xidməti seçsəniz, qoşulmanı ayrıca iş kimi hazırlamaq olar.

## Bələdçi: sizin addımlarınız

Agent hazırlayıb: kod (B yolu standartdır), saytın üç səhifəsi, demo video 1, ingiliscə ərizə mətnləri. Sizdə qalan: portala giriş, ərizə, telefon yazısı (demo video 2), açarlar, hesabın ictimai edilməsi. Açar, parol və kodu yalnız siz görür və yazırsınız.

### Addım 1. Portalda tətbiqin vəziyyətini yoxlayın

1. [developers.tiktok.com](https://developers.tiktok.com/) → 8ulduz TikTok hesabı ilə **Log in** → sağ yuxarıda profil → **Manage apps** → 8ulduz tətbiqi.
2. Yuxarıda **Sandbox / Production** keçidi var. Statusa baxın: Draft, In review, Live və ya Not approved.
3. GitHub-dakı `TIKTOK_CLIENT_KEY` hansı bölmənin açarıdır? Portal onu hər bölmədə göstərir, müqayisə edin. Açarın dəyərini agentə yazmayın.
   - **Sandbox açarıdırsa:** B yolunu yoxlamadan əvvəl də sınamaq olar: addım 2a.
   - **Production açarıdırsa:** addım 2b.

### Addım 2a. Sandbox-da B yolunu sınayın (demo video 2 üçün lazımdır)

TikTok-un tələbi: təsdiqlənməmiş tətbiqin demo videosu Sandbox-da çəkilir. Sandbox yalnız sınaq üçündür, gündəlik paylaşım üçün yox.

1. Sandbox → **Products** → Content Posting API: **Direct Post** açarını söndürün. **Scopes**: `user.info.basic` və `video.upload` qalsın, `video.publish`-i silin.
2. **Target users** → 8ulduz TikTok hesabı əlavə olunub? Yoxdursa əlavə edin. TikTok yazır ki, siyahı bir saata qədər gec yenilənə bilər.
3. Açarlar Sandbox-dan deyilsə, Sandbox-un **Client key** və **Client secret**-ini yazın (addım 5-in 1-ci bəndi).
4. Brauzerdə icazə ünvanını açın, **Authorize** basın, açılan ünvanı «TikTok-da paylaş» işinin **kod** sahəsinə yapışdırın (addım 5-in 2–3-cü bəndi).
   - Jurnalda belə sətir görünməlidir: «qoşuldu — 8ulduz.az; icazələr: user.info.basic,video.upload … B yolu hazırdır».
5. **Run workflow** → **sinaq** işarəsi → Run. Bir neçə dəqiqəyə TikTok tətbiqində bildiriş gəlməlidir.
6. Bunu telefonda ekran yazısı ilə çəkin, bu **demo video 2**-dir (ssenari aşağıda).

### Addım 2b. Tətbiqin məlumatı (Production → App details)

Mətnləri [ərizə mətnləri](#ərizə-mətnləri-ingiliscə) bölməsindən kopyalayın.

| Sahə | Nə yazılır |
|---|---|
| App icon | `ios/App/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png` (1024×1024, PNG) |
| App name | `8ulduz` (adda «TikTok» olmasın) |
| Category | News |
| Description | aşağıdakı «App description» |
| Terms of Service URL | `https://8ulduz.az/sertler/` |
| Privacy Policy URL | `https://8ulduz.az/mexfilik/` |
| Platforms | Web → Website URL `https://8ulduz.az/` |

Yoxlayıcının istədiyi kimi, şərtlər və məxfilik keçidləri hər səhifənin altında menyusuz görünür. Hər iki səhifədə ingiliscə bölmə var: `#en`, TikTok məlumatı `mexfilik/#tiktok`.

**URL properties:** üç ünvan **Verified** olmalıdır. Repoda `tiktok46dn…txt` imza faylı artıq var. «Verified» görünmürsə, **Verify** basın.

**Products:**
- **Login Kit**: Redirect URI `https://8ulduz.az/haqqinda/`, hərfbəhərf belə. Bu səhifədə indi ingiliscə izah da var.
- **Content Posting API**: **Direct Post açarı söndürülsün**.
- **Scopes**: yalnız `user.info.basic`, `video.upload`. TikTok yazır ki, artıq icazə yoxlamanı gecikdirir.

### Addım 3. Demo videolar

TikTok ən çox 5 video qəbul edir, hər biri 50 MB-a qədər. İki video yükləyin.

**Demo video 1 (agent hazırlayır).**
1. PR birləşəndən sonra GitHub → **Actions** → «TikTok demo videosu» → **Run workflow** (main) açın.
2. İş bitəndə **Artifacts** → `tiktok-demo` (zip) yükləyin, içindəki `tiktok-demo.mp4` faylını götürün. Ssenari `ssenari.txt`-dədir.
3. Videoda bunlar var (Chrome-un ünvan sətri ilə, aşağıda ingiliscə izah):
   - `https://8ulduz.az/`;
   - altdakı şərtlər və məxfilik keçidləri;
   - haqqında, şərtlər və məxfilik səhifələrinin TikTok bölmələri;
   - video modulunun son videosu;
   - TikTok işinin ictimai jurnalı.
4. Açar yoxdur.

PR-dakı nüsxə budağın yerli surətidir: küncündə «PREVIEW» yazılıb, onu göndərməyin.

**Demo video 2 (siz, telefonda və ya kompüterdə, Sandbox-da).** Fasiləsiz, 1–3 dəqiqə:
1. Kompüterdə icazə ünvanı açılır: TikTok-un səhifəsində tətbiqin adı və «Share content as a draft» icazəsi görünür → **Authorize**.
2. Brauzer `https://8ulduz.az/haqqinda/?code=…` açır. Ünvan sətrindəki kodu ekranda saxlamayın, tez keçin.
3. GitHub-da «TikTok-da paylaş» → **Run workflow** (kod sahəsinə yapışdırılır) → jurnalda «qoşuldu».
4. **Run workflow** → **sinaq** → jurnalda «qaralama göndərildi».
5. Telefonda TikTok → **Inbox** (Gələnlər) → bildiriş → video redaktorda açılır → mətn yapışdırılır → **Who can watch: Everyone** → **Post**.
6. Profildə video görünür.

Client secret, token və ya `code=` dəyəri videoda görünməsin. Görünsə həmin anı kəsin.

### Addım 4. Ərizəni göndərin

1. **App review** bölməsi: «how each product and scope works» sahəsinə aşağıdakı mətni yapışdırın. İki demo videonu yükləyin.
2. **Submit for review**. Göndərəndə qaydaları (Terms, Developer Guidelines) qəbul etmək sizin qərarınızdır.
3. Müddət: TikTok-un FAQ-ı «several days to two weeks» yazır. Status sırası: In review → Live və ya Not approved.
4. Rədd olunsa, rəy **History → Review comments**-də olur. Rəyi agentə verin, düzəldib yenidən göndərmək olar. Səbəb «private or personal use»-dursa, B yolu da bağlıdır: yuxarıdakı C və ya əl ilə yükləmə.

Yoxlama gedərkən gizli `SELF_ONLY` videolar hesabda yığılmasın deyə **Settings → Secrets and variables → Actions → Variables** bölməsində `TIKTOK` = `0` yaza bilərsiniz. Token itmir. Təsdiqdən sonra dəyişəni silin.

### Addım 5. Təsdiqdən sonra: açarlar və qoşulma

1. **Production açarları** (Sandbox-dakılardan fərqlidir). PowerShell-də:

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

2. **İcazə.** Brauzerdə bu ünvanı açın. `<CLIENT_KEY>` yerinə öz client key-inizi yazın:

```
https://www.tiktok.com/v2/auth/authorize/?client_key=<CLIENT_KEY>&scope=user.info.basic,video.upload&response_type=code&redirect_uri=https%3A%2F%2F8ulduz.az%2Fhaqqinda%2F&state=8ulduz
```

   8ulduz TikTok hesabı ilə girin, **Authorize** basın. Brauzer `https://8ulduz.az/haqqinda/?code=…` açacaq. **Ünvan sətrini tam kopyalayın.**

3. **Qoşulma.** GitHub → 8ulduz/8ulduz → **Actions** → «TikTok-da paylaş» → **Run workflow** → **kod** sahəsinə yapışdırın → **Run workflow**.
   - Kod bir dəfəlikdir və bir neçə dəqiqə işləyir, tez edin.
   - Jurnalda: «qoşuldu — 8ulduz.az; icazələr: user.info.basic,video.upload; token … gün işləyir» və «B yolu hazırdır».

4. **Hesabı yenidən ictimai edin.** TikTok tətbiqi → Profil → ☰ → **Settings and privacy** → **Privacy** → **Private account** söndürün.
   - Əvvəlki gizli sınaq videoları «Only me» olaraq qalır. Hər birini açıb **Privacy settings → Everyone** edin, ya da silin.

5. **Variables.**
   - `TIKTOK_MODE` boş qalsın (`auto`) və ya `inbox` yazın.
   - `TIKTOK_PRIVACY`-ni yazmayın. Qaralamada görünməni tətbiqdə özünüz seçirsiniz.
   - `TIKTOK=0` yazmışdınızsa, silin.

### Addım 6. Gündəlik iş (hər video ~20 saniyə)

Video modulu 2 saatdan bir video hazırlayır. TikTok-a 24 saatda ən çox 5 qaralama gedir, aralarında ən az 60 dəqiqə.

1. Telefonda TikTok-dan bildiriş gəlir → **Inbox** → 8ulduz videosu → redaktor açılır.
2. Mətni yapışdırın: GitHub → Actions → həmin «Video xəbər» işi → xülasədə «TikTok-da yapışdırılacaq mətn» bloku.
3. **Who can watch: Everyone**.
4. Videoda süni səs (SARA) varsa, **AI-generated content** etiketini açın.
5. **Post**.

Qaralama dərc olunandan sonra növbəti dövrə jurnala «paylaşıldı … (tətbiqdə dərc olundu)» yazır. 5 qaralama dərc olunmadan gözləyirsə, yenisi göndərilmir.

### İstəyə bağlı: A yolu (Direct Post auditi)

Tövsiyə olunmur (yuxarıda «Niyə A yox»). Yenə də sınamaq istəsəniz:
1. Tətbiq «Live» olmalıdır, `video.publish` icazəsi və **Direct Post** açarı ilə.
2. Audit formu: `developers.tiktok.com/application/content-posting-api`. Mətnlər aşağıdadır.
3. Keçsə, hesab ictimai olandan sonra:
   - `TIKTOK_PRIVACY=PUBLIC_TO_EVERYONE` yazın;
   - şərh üçün `TIKTOK_INTERACTIONS=comment` yazın.
   - Kod özü birbaşa paylaşıma keçir.

   Keçməsə, `auto` rejim hər videonu eyni dövrədə qaralama kimi göndərir.

## Ərizə mətnləri (ingiliscə)

Mətnlər dürüstdür: alət 8ulduz-un öz hesabı üçündür. Bunu gizlətmək olmaz.

**App description** (Basic information, qısa):

> Sends the short news videos made by 8ulduz.az to the 8ulduz TikTok account as drafts for our editor to post.

**App review → how each product and scope works** (B yolu):

> 8ulduz.az (https://8ulduz.az/) is a free Azerbaijani news aggregator website with Android and iPhone apps. We turn our own news summaries into short vertical videos: our own text, a text-to-speech voice-over, licensed stock footage (Pixabay/Pexels, credited) and our 8ulduz.az design. No third-party news videos and no music are used. This app sends those videos to the 8ulduz TikTok account, which is run by the 8ulduz.az team.
>
> Login Kit (user.info.basic): the owner of the 8ulduz TikTok account authorizes the app once in a web browser. The Redirect URI is https://8ulduz.az/haqqinda/, a static page without scripts that explains the integration. We read only the open ID and display name to confirm which account is connected. Readers never sign in with TikTok.
>
> Content Posting API, Upload (video.upload): when a news video is ready, our server job (GitHub Actions) uploads the file with FILE_UPLOAD via /v2/post/publish/inbox/video/init/ and checks /v2/post/publish/status/fetch/. It sends at most 5 drafts per 24 hours, at least 60 minutes apart. The video arrives in the TikTok inbox. The account owner opens the notification, edits the caption, chooses who can view the video and posts it with TikTok's own editing flow. The app never publishes anything by itself.
>
> Data: tokens are encrypted (AES-256-GCM) and kept with our encrypted GitHub secrets. TikTok data is never shown on the website, shared or used for advertising. Privacy: https://8ulduz.az/mexfilik/#tiktok. Terms: https://8ulduz.az/sertler/#en.
>
> Demo video 1 shows the website, the Terms and Privacy pages, a sample video and the server job log. Demo video 2 (Sandbox) shows the authorization and the draft being posted from the TikTok app.

**Direct Post audit formu** (yalnız A yolu, tövsiyə olunmur). Formun sahələri dəyişə bilər, mənası belədir:

| Sual | Cavab |
|---|---|
| Describe your product and how it uses the Content Posting API | 8ulduz.az is an Azerbaijani news website. Our server job posts the short news videos we produce ourselves (own text, text-to-speech voice-over, licensed stock footage, no music) to the 8ulduz TikTok account with Direct Post (FILE_UPLOAD). |
| Who are your users? | One account: the 8ulduz TikTok account, operated by the 8ulduz.az team. Readers do not connect TikTok accounts. |
| Expected daily users / posts | 1 creator, up to 10 posts per day (at least 60 minutes apart). |
| Describe the user experience for posting | Before every post the job queries creator_info: nickname, privacy options, interaction settings, maximum duration. The account owner chooses visibility in our settings; there is no default, and without a choice the job sends a draft instead. Comment, Duet and Stitch stay off unless the owner enables them, and are always off when the account disables them. Commercial disclosure flags are set per video, and branded content is never private. The AI label is set for synthetic voice. The job then polls the post status. |
| Per-scope justification | user.info.basic: confirm the connected account. video.publish: post our own videos to our own account. |

## Demo video

Necə hazırlanır (`tiktok-demo.yml`):
- Xvfb ekranında başlıqlı Chrome açılır, ffmpeg bütün ekranı yazır. Ünvan sətri videoda görünür, TikTok-un tələbinə görə domen Website URL ilə eyni olmalıdır.
- Altda 100 piksellik zolaqda ingiliscə izah gedir.
- Nümunə video `sosial-video.yml`-in son uğurlu işindən (`video-xeber` artifact-ı) götürülür, tapılmasa sınaq videosu hazırlanır. Göstərilən iş səhifəsi «tiktok / post» işi olan son işdir.
- İşə heç bir sirr verilmir. Video yalnız artifact kimi saxlanır (30 gün), heç yerə yazılmır.
- PR-da budağın səhifələri yerli serverdən yazılır (küncündə «PREVIEW»). main-də **Run workflow** ilə əsl `https://8ulduz.az/` yazılır.

## Necə işləyir

- **Tətik.** Video modulu videonu hazırlayıb bu iş axınını çağırır (`workflow_call`, bölmə «Video modulu ilə qoşulma»). Əl ilə də olar: **Run workflow** (`kod`, `sinaq`). PR-da ayrıca `sinaq-video` işi ffmpeg ilə əsl video hazırlayır və yükləyicini açarsız, saxta TikTok ilə yoxlayır.
- **Seçim.** Ən təzə video, dövrədə bir dənə. Video 12 saatdan köhnə olmamalıdır. Əvvəl getmiş video getmir: ad, fayl heşi və başlıq yoxlanır.
- **Mənbə qaydası (qırmızı xətt 2).** Videonun xəbəri (`source`, `sourceUrl`, `items`) saytın öz qaydasından (`policyViolation`) keçir. Xarici mənbədən Azərbaycan mövzusu və müxalifət mənbəyi düşür.
- **Yalnız öz videolarımız.** Yükləyici yalnız bu şərtlərin hamısı ödənəndə göndərir:
  - JSON-da `"own": true` var;
  - faylın metadatasında «8ulduz.az» nişanı var;
  - JSON-da başqa saytın video keçidi yoxdur;
  - video `data/reels.json`-da deyil.

  X-dəki F1, NBA, Fox News kimi videolar TikTok-a **heç vaxt** getmir. TikTok-un qaydası: «unoriginal or reused material» tövsiyə lentinə düşmür. Müəllif hüququnu təkrar pozan hesabı TikTok bağlaya bilər.
- **Su nişanı.** TikTok tətbiqə paylaşılan məzmuna öz brendini, loqosunu və ya reklam mətnini əlavə etməyi qadağan edir. Bizdə video da, ad da bizimdir: «8ulduz.az» videonun öz dizaynıdır, yükləyici videoya heç nə əlavə etmir.
- **Rejim (`TIKTOK_MODE`).**
  - `auto` (standart):
    - tokendə `video.upload` varsa və sahibin seçdiyi görünmə birbaşa alınmırsa, video qaralama gedir;
    - görünmə alınmır deməkdir: seçilməyib, hesabda yoxdur, brend məzmunu gizli olardı, ya da TikTok «unaudited» deyir;
    - yalnız `video.publish` varsa, video birbaşa gedir, audit yoxdursa `SELF_ONLY`.
  - `inbox`: həmişə qaralama.
  - `direct`: həmişə birbaşa.
- **Birbaşa paylaşımda TikTok-un UX qaydaları:**
  1. hər videodan əvvəl `creator_info`: ad, görünmə seçimləri, şərh/duet/stitch, ən uzun video; xəta varsa (həddi dolub, bağlanıb) paylaşım dayanır;
  2. görünmənin standart dəyəri yoxdur: `TIKTOK_PRIVACY`-ni sahib seçir;
  3. şərh, duet, stitch yalnız `TIKTOK_INTERACTIONS`-da olanlar açılır, hesab bağlayıbsa bağlı qalır;
  4. kommersiya açıqlaması: `TIKTOK_BRAND_ORGANIC` (öz biznesi), `TIKTOK_BRANDED_CONTENT` (pullu əməkdaşlıq) və ya videonun JSON-unda `brandOrganic`/`brandedContent`; brend məzmunu gizli göndərilmir;
  5. uzunluq: JSON-dakı `duration`, yoxdursa faylın öz `mvhd` qutusu;
  6. status sorğusu (`PUBLISH_COMPLETE`, `FAILED` səbəbi ilə).
- **AI etiketi (`is_aigc`).** Modul `aigc: true` yazıbsa, ya da videoda süni səs (`voice`) varsa qoyulur. Modul `aigc: false` yazıbsa qoyulmur.
- **Qaralama.**
  - Mətn TikTok-a getmir: Upload API-də sahə yoxdur. Ona görə iş xülasəsində «TikTok-da yapışdırılacaq mətn» bloku olur.
  - 24 saatda ən çox 5 qaralama.
  - Dərc olunub-olunmadığı 24 saat yoxlanır, dəyişməyən qaralama jurnalda təkrar yazılmır.
  - TikTok `spam_risk_too_many_pending_share` desə, 6 saat fasilə verilir.
- **Ardıcıllıq:**
  1. `creator_info` (birbaşa);
  2. `video/init` və ya `inbox/video/init` (`FILE_UPLOAD`);
  3. fayl göndərilir (64 MB-a qədər bir hissədə, böyük fayl 10 MB-lıq hissələrlə);
  4. status.
- **Mətn:** başlıq, izah, «Ətraflı: 8ulduz.az (keçid profildədir)», abunə çağırışı («Ən vacib xəbərlər hər gün — abunə olun: @8ulduz.az», vəd video növünə görə), haşteqlər (#8ulduz #xəbərlər #Azərbaycan və modulun verdikləri). TikTok-da keçid basılmır, sayt bio-dadır: bio-ya «8ulduz.az» yazın.
- **Token.**
  - Ömür: TikTok sənədində access token 24 saat, refresh token 365 gün; başqa səhifədə 2 saat və 180 gün yazılıb. Kod TikTok-un cavabındakı rəqəmi işlədir.
  - Yeniləmə: TikTok hər yeniləmədə yeni refresh token qaytarır, yeniləmə avtomatikdir. Zəncir `actions/cache`-də AES-256-GCM ilə şifrəli saxlanır. Açar `TIKTOK_CLIENT_SECRET`-dən alınır, PR işləri onu oxuya bilmir.
  - Bitmə: tokenin bitməsinə 14 gün qalanda jurnalda «DİQQƏT» yazılır. TikTok refresh tokenin ömrünü uzatmırsa, ildə bir dəfə addım 5-in 2–3-cü bəndini təkrarlayın.
  - Ehtiyat (istəyə bağlı): refresh tokeni özünüz alıbsınızsa, `gh secret set TIKTOK_REFRESH_TOKEN --repo 8ulduz/8ulduz` ilə yazın. İş axını keşdəki token itəndə ona keçir.
- **Hədlər.** Hesaba gündə təxminən 15 API postu (bütün tətbiqlər birlikdə). Bizdə gündə ən çox 10 (qaralama 5), aralarında ən az 60 dəqiqə. TikTok «çox post» desə, 6 saat fasilə verilir.
- **Jurnal.** GitHub → Actions → «TikTok-da paylaş» və ya «Video xəbər» → son iş, xülasədə «TikTok» bölməsi. Açar, token və kod jurnala düşmür.

## Video modulu ilə qoşulma (müqavilə)

Video modulu hər video üçün eyni adlı iki fayl yazır: `<ad>.mp4` + `<ad>.json`. Onları artifact kimi yükləyib bu işi çağırır. Qoşulma `sosial-video.yml`-in sonundadır:

```yaml
  tiktok:
    needs: video
    if: ${{ !cancelled() && github.ref == 'refs/heads/main' && needs.video.outputs.paylas == '1' && needs.video.outputs.yoxlandi == '1' }}
    uses: ./.github/workflows/tiktok.yml
    with:
      artifact: video-xeber
    secrets:
      TIKTOK_CLIENT_KEY: ${{ secrets.TIKTOK_CLIENT_KEY }}
      TIKTOK_CLIENT_SECRET: ${{ secrets.TIKTOK_CLIENT_SECRET }}
      TIKTOK_REFRESH_TOKEN: ${{ secrets.TIKTOK_REFRESH_TOKEN }}
```

- **Nə vaxt gedir.** Yalnız `main`-də və əsl paylaşım dövrəsində: `paylas` `1` olmalıdır. PR nümunəsi və `paylas=false` önizləməsi TikTok-a getmir.
- **Yoxlama.** Video modulun öz yoxlamasından («Videonu yoxla», çıxış `yoxlandi`) keçməlidir. Facebook və ya Instagram alınmasa da (iş qırmızı), yoxlanmış video TikTok-a gedir.
- **Sirlər.** TikTok işinə yalnız üç TikTok sirri verilir, Facebook açarı ora getmir.
- **Seçim.** Modul ən vacib xəbəri Facebook (`FB_PAGE_TOKEN`) və ya TikTok (`TIKTOK_CLIENT_KEY` + `TIKTOK_CLIENT_SECRET`) açarı olanda seçir (`VIDEO_ACAR`).
- **Tezlik.** Modul 2 saatdan bir, Bakı vaxtı ilə 08–23 arası, gündə ən çox 8 video hazırlayır.

`<ad>.json`:

| Sahə | Məcburi | Nə |
|---|---|---|
| `id` | bəli | Videonun sabit adı, məs. xəbər nömrəsi. Eyni `id` ikinci dəfə getmir. |
| `own` | bəli, `true` | Video bizim ffmpeg ilə hazırlanıb, başqasının görüntüsü yoxdur. |
| `title` | bəli | Başlıq: mətnin birinci sətri. |
| `summary` | yox | İzah, 1200 simvola qədər. |
| `text` | yox | Videoda gedən izah. Varsa mətndə `summary`-nin yerinə o yazılır. |
| `createdAt` / `publishedAt` | yox | ISO vaxt. 12 saatdan köhnə video getmir. |
| `hashtags` | yox | Əlavə haşteqlər, ən çox 5 (cəmi 8). |
| `source`, `sourceUrl`, `category`, `lang` | xəbərdən video olanda bəli | Lentdəki xəbərin sahələri, mənbə qaydası üçün. |
| `items` | yox | Bir neçə xəbərdən video: `[{ title, source, sourceUrl, category }]`, hər biri qaydadan keçir. |
| `aigc` | yox | `true`: AI etiketi; `false`: süni səs olsa da etiket yox. |
| `voice` | yox | Videoda süni səs var (AI etiketi). |
| `brandOrganic`, `brandedContent` | yox | Kommersiya açıqlaması (reklam videosu üçün). |
| `coverMs` və ya `cover_s` | yox | Üz qabığının anı: millisaniyə və ya saniyə (standart 1 s). |
| `duration` | yox | Saniyə. Yoxdursa faylın özündən oxunur. Hesabın həddindən uzundursa göndərilmir. |

JSON-da başqa saytın video keçidi (`video`, `videoUrl`, `src`, `clips`) olmamalıdır. Belə video getmir.

`<ad>.mp4`:
- **Format:** MP4, H.264 (+AAC), 1080×1920, 23–60 kadr/s.
- **Uzunluq və ölçü:** hesabın həddindən uzun olmamalıdır (`max_video_post_duration_sec`), 4 GB-dan kiçik.
- **Metadata:** `-movflags +faststart` və `-metadata comment=8ulduz.az`. Bu nişan olmasa video getmir.
- Yuxarıdakı «8ulduz.az» yazısı TikTok-un öz yazılarının altında qalmasın. Yuxarıdan təxminən 8–10% və aşağıdan ~20% hissəni TikTok-un düymələri örtür.

Sınaq videosu (`node .github/scripts/tiktok.cjs sinaq <qovluq>`) bu müqaviləyə uyğundur.

## Tənzimləmə (Variables, istəyə bağlı)

| Ad | Standart | Nə |
|---|---|---|
| `TIKTOK` | — | `0`: TikTok tam söndürülür. |
| `TIKTOK_MODE` | `auto` | `inbox`: həmişə qaralama (B). `direct`: həmişə birbaşa (A). |
| `TIKTOK_PRIVACY` | boş | Birbaşa paylaşımın görünməsi, standart dəyər yoxdur: `PUBLIC_TO_EVERYONE`, `MUTUAL_FOLLOW_FRIENDS`, `FOLLOWER_OF_CREATOR`, `SELF_ONLY`. Boşdursa `auto` qaralama, `direct` `SELF_ONLY` göndərir. |
| `TIKTOK_INTERACTIONS` | boş | Birbaşa paylaşımda açılanlar: `comment`, `duet`, `stitch` (vergüllə). Boşdursa hamısı bağlı. |
| `TIKTOK_BRAND_ORGANIC` | — | `1`: «Your brand» (öz biznesinin reklamı). Xəbər üçün lazım deyil. |
| `TIKTOK_BRANDED_CONTENT` | — | `1`: «Branded content» (pullu əməkdaşlıq). Gizli göndərilmir. |
| `TIKTOK_MAX_DAY` | 10 (qaralama 5) | 24 saatda ən çox; 15-dən (qaralama 5-dən) çox olmaz. |
| `TIKTOK_MIN_GAP_MIN` | 60 | Videolar arası dəqiqə. |
| `TIKTOK_MAX_AGE_H` | 12 | Bundan köhnə video getmir. |
| `TIKTOK_REDIRECT_URI` | `https://8ulduz.az/haqqinda/` | Tətbiqdəki Redirect URI başqadırsa. |

## Mənbələr (TikTok for Developers və TikTok qaydaları, 2026-11-23 oxunub)

- Paylaşma qaydaları: «Intended Use», Direct Post UX, su nişanı, audit, hədlər: https://developers.tiktok.com/doc/content-sharing-guidelines
- Tətbiq yoxlaması qaydaları: «private or personal use», demo video, sayt, şərtlər: https://developers.tiktok.com/doc/app-review-guidelines
- Yoxlama FAQ, müddət, statuslar: https://developers.tiktok.com/docs/en/getting-started-faq
- Tətbiq yaratmaq, URL properties, App review bölməsi: https://developers.tiktok.com/doc/getting-started-create-an-app
- Sandbox, Target users, ictimai videoya icazə yoxdur: https://developers.tiktok.com/doc/add-a-sandbox
- Content Posting API, Direct Post, auditsiz məhdudiyyət: https://developers.tiktok.com/doc/content-posting-api-get-started
- Direct Post reference: `post_info`, xəta kodları: https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
- Creator info: https://developers.tiktok.com/doc/content-posting-api-reference-query-creator-info
- Qaralama (Upload), 24 saatda 5, inbox bildirişi: https://developers.tiktok.com/doc/content-posting-api-reference-upload-video və https://developers.tiktok.com/doc/content-posting-api-get-started-upload-content
- Status və `fail_reason`: https://developers.tiktok.com/doc/content-posting-api-reference-get-video-status
- Fayl göndərmə (hissələr, formatlar): https://developers.tiktok.com/doc/content-posting-api-media-transfer-guide
- İcazələr (scopes): https://developers.tiktok.com/doc/tiktok-api-scopes
- OAuth və tokenin yenilənməsi: https://developers.tiktok.com/doc/login-kit-web, https://developers.tiktok.com/doc/oauth-user-access-token-management
- Musiqi razılığı: https://www.tiktok.com/legal/page/global/music-usage-confirmation/en
- Brend məzmunu qaydası: https://www.tiktok.com/legal/page/global/bc-policy/en
- Orijinallıq və FYF: https://www.tiktok.com/community-guidelines/en/integrity-authenticity
- Üçüncü tərəf: TikTok-un yazılı rəddi (2026-10-29), developer təcrübələri: https://github.com/gitroomhq/postiz-app/issues/1563
