# Xəbərlərin profillərimizdə paylaşılması

Sahibin göstərişi (2026-11-05): «bizim xəbərlərimiz profillərimizdə paylaşılsın».

## Necə işləyir

- `.github/workflows/social.yml` hər 20 dəqiqədən bir (:07, :27, :47) işə düşür. Xəbər axınından ayrıdır, repoya yazmır, sayta yük gətirmir.
- `.github/scripts/social.cjs` lentdən ən vacib xəbəri seçir: son 3 saatda ən azı 4 mənbənin yazdığı azərbaycanca xəbər və ya Prezident bölməsinin xəbəri. Ən çox mənbəli birinci gedir.
- Hər şəbəkəyə bir dövrədə bir post gedir, yəni saatda ən çox 3. Eyni xəbər iki dəfə getmir.
- Keçid saytın paylaşma səhifəsidir (`https://8ulduz.az/x/<nömrə>`). Önizləmədə başlıq və şəkil görünür, oxucu saytda açılır.
- Şəbəkə yalnız açarı GitHub-da yazılanda işləyir. Açar yoxdursa heç nə göndərilmir.

Açarlar burada yazılır: GitHub → 8ulduz/8ulduz → Settings → Secrets and variables → Actions.
«Secrets» tabına gizli açarlar, «Variables» tabına gizli olmayan nömrələr.

## Telegram (pulsuz, 3 dəqiqə)

1. Telegram-da @BotFather-ə yazın: `/newbot`. Ad və `_bot` ilə bitən istifadəçi adı verin. BotFather tokeni göndərəcək.
2. Kanalda: İdarəçilər → İdarəçi əlavə et → yeni bot. «Mesaj göndərmək» icazəsi kifayətdir. (t.me/sekkizulduz kanal deyil, şəxsi hesabdır: bot ora yaza bilmir.)
3. Secrets: `TELEGRAM_BOT_TOKEN` = BotFather-in verdiyi token.

Kanal ünvanı yazmaq lazım deyil: iş axını botun admin edildiyi kanalı botun öz yeniləmələrindən tapır və yadda saxlayır (jurnalda «kanal tapıldı — ad (nömrə)»). Bot 24 saatdan əvvəl əlavə edilibsə, onu kanaldan çıxarıb yenidən admin edin. Başqa kanal seçmək üçün Variables: `TELEGRAM_CHAT` = `@kanal_adi` və ya `-100…` nömrəsi.

## Facebook

API yalnız Facebook **səhifəsinə** yazır, şəxsi profilə yazmır. Botun yazdığı səhifə «8ulduz»dur (`profile.php?id=61596264031461`, köhnə səhifə nömrəsi 1470250006171917). Saytın «izlə» düyməsi 6 noyabra qədər səhvən «Səkkiz Ulduz» profilinə (`61596034210996`, 1 izləyici) aparırdı.

1. developers.facebook.com → Create App → «Other» → «Business».
2. Graph API Explorer: səhifəni seçin, `pages_manage_posts` və `pages_read_engagement` icazələri ilə səhifə tokeni alın, sonra Access Token Debugger-də «Extend» ilə uzunmüddətli edin.
3. Secrets: `FB_PAGE_TOKEN`. Səhifənin nömrəsi (8ulduz: 1470250006171917) social.yml-də yazılıb; başqa səhifə üçün Variables: `FB_PAGE_ID`.

2026-11-05-də qurulub: səhifə «8ulduz», Meta tətbiqi «8ulduz paylasma» (1000332509080909). Səhifə açarı uzadılmış (60 günlük) istifadəçi açarından alındığı üçün müddətsizdir; Facebook parolu dəyişsə və ya tətbiqin icazəsi götürülsə, yenidən alınmalıdır.

## X

1. developer.x.com → Project və App yaradın. User authentication settings → «Read and write».
2. İcazəni dəyişəndən **sonra** Keys and tokens → Access Token and Secret yaradın.
3. Secrets: `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_SECRET`.

X API-də yazma ödənişli ola bilər; qiyməti developer portalında yoxlayın.

## LinkedIn

1. linkedin.com/developers → Create app. Products: «Share on LinkedIn» və «Sign In with LinkedIn using OpenID Connect».
2. OAuth tokeni `w_member_social openid profile` icazəsi ilə alın. Müəllif nömrəsi `/v2/userinfo` cavabındakı `sub`-dır.
3. Secrets: `LINKEDIN_TOKEN`. Variables: `LINKEDIN_AUTHOR` = `urn:li:person:<sub>`.

LinkedIn şəxsi tokeni 60 gün işləyir, sonra yenilənməlidir.

## Tənzimləmə (Variables, istəyə bağlı)

- `SOCIAL_MIN_SOURCES`: neçə mənbə yazanda paylaşılsın (standart 4). Az yazsanız, post çoxalır.
- `SOCIAL_PER_RUN`: hər 20 dəqiqədə şəbəkəyə neçə post (standart 1).

## Yoxlama

GitHub → Actions → «Profillərdə paylaş» → son iş. Jurnalda hər şəbəkə üçün «paylaşıldı» və ya «alınmadı — səbəb» yazılır. Açar heç vaxt jurnala düşmür.
