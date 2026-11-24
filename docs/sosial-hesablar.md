# Sosial hesablarımızın profil mətnləri

Sahibin göstərişi (2026-11-24): «Sosial şəbəkə hesablarımızın hər birində digər hesablarımız görünsün (keçidli düymələr) və saytla bağlı məlumat olsun (e-mail və sairə)».

Profil mətnini və keçidləri API ilə dəyişmək olmur, yalnız tətbiqdə dəyişilir:
- **YouTube:** açarın kanal icazəsi yoxdur.
- **Instagram və TikTok:** bio API-si yoxdur.
- **Facebook:** səhifə açarına yalnız paylaşma icazələri verilib ([sosial-video.md](sosial-video.md)), səhifə məlumatını dəyişmək üçün `pages_manage_metadata` lazımdır.

Ona görə mətnlər burada hazırdır, kopyalayıb hər tətbiqdə yapışdırmaq kifayətdir. Simvol sayı hər şəbəkənin həddinə görə yoxlanıb.

## Hesablarımız

| Şəbəkə | Ünvan |
|---|---|
| Sayt | https://8ulduz.az |
| Telegram | https://t.me/sekkizulduz_az |
| Facebook | https://www.facebook.com/profile.php?id=61596264031461 |
| Instagram | https://www.instagram.com/8ulduz.az/ |
| TikTok | https://www.tiktok.com/@8ulduz.az |
| YouTube | https://www.youtube.com/@8ULDUZ |
| X | https://x.com/8ulduz |
| LinkedIn | https://www.linkedin.com/in/s%C9%99kkiz-ulduz-605537449/ |
| E-poçt | info@8ulduz.az |

## YouTube (Studio → Fərdiləşdirmə → Əsas məlumat)

- **Ad:** `8 Ulduz | Səkkiz Ulduz xəbər`.
- **Təsvir:**
  ```
  8 Ulduz (Səkkiz Ulduz, 8ulduz.az) — xəbər saytı: Azərbaycan və dünyadan son xəbərlər, hər dəqiqə yenilənir. 8ulduz, səkkizulduz.

  Sayt: https://8ulduz.az
  Telegram: https://t.me/sekkizulduz_az
  Instagram: https://www.instagram.com/8ulduz.az/
  TikTok: https://www.tiktok.com/@8ulduz.az
  Facebook: https://www.facebook.com/profile.php?id=61596264031461
  X: https://x.com/8ulduz

  Əlaqə: info@8ulduz.az
  ```
- **Keçidlər** (14-ə qədər, ilk 5-i banner üstündə görünür): Sayt, Telegram, Instagram, TikTok, Facebook, X, LinkedIn.
- **Əlaqə məlumatı → E-poçt:** `info@8ulduz.az`.
- **Açar sözlər** (Ayarlar → Kanal): [youtube.md «Kanal»](youtube.md#1-kanal).

## Instagram (Profili redaktə et)

- **Bio** (138/150):
  ```
  Azərbaycan və dünyadan son xəbərlər, hər dəqiqə 📰
  YouTube · TikTok · Telegram · Facebook — keçidlər aşağıda
  X: @8ulduz · ✉️ info@8ulduz.az
  ```
- **Keçidlər** (5-ə qədər): Sayt, YouTube, TikTok, Telegram, Facebook.
- **Əlaqə seçimləri** (peşəkar hesab): e-poçt `info@8ulduz.az` («E-poçt» düyməsi profildə görünür).

## Facebook (səhifə → Haqqında / Redaktə et)

- **Təqdimat** (85/101): `Azərbaycan və dünyadan son xəbərlər, hər dəqiqə yenilənir. 8ulduz.az · info@8ulduz.az`
- **Vebsayt:** `https://8ulduz.az`. **E-poçt:** `info@8ulduz.az`.
- **Sosial keçidlər:** Instagram, TikTok, YouTube, X, LinkedIn. Telegram keçidi «Vebsayt» kimi ikinci sətrə əlavə olunur.
- **Düymə:** «Mesaj göndər» əvəzinə «E-poçt göndər» (`info@8ulduz.az`) və ya «Sayta keç».

## X (Profili redaktə et)

- **Bio** (140/160):
  ```
  Azərbaycan və dünyadan son xəbərlər, hər dəqiqə yenilənir 📰 YouTube: youtube.com/@8ULDUZ · Telegram: t.me/sekkizulduz_az · ✉️ info@8ulduz.az
  ```
- **Vebsayt:** `https://8ulduz.az`. **Məkan:** Bakı, Azərbaycan.

## TikTok (Profili redaktə et)

- **Bio** (70/80): `Son xəbərlər hər dəqiqə 📰 8ulduz.az · YouTube @8ULDUZ · info@8ulduz.az`
- **Instagram və YouTube-u bağla:** profildə hər birinə düymə görünür.
- **Vebsayt:** biznes hesabında açılır. Yoxdursa, bio-dakı «8ulduz.az» yazısı kifayətdir.

## Telegram (kanal → Redaktə et → Təsvir)

- **Təsvir** (215/255):
  ```
  8ULDUZ (8ulduz.az) — Azərbaycan və dünyadan son xəbərlər, hər dəqiqə.
  YouTube: youtube.com/@8ULDUZ
  Instagram/TikTok: @8ulduz.az · X: @8ulduz
  Facebook: facebook.com/profile.php?id=61596264031461
  Əlaqə: info@8ulduz.az
  ```

## LinkedIn (Profil → Əlaqə məlumatı və Haqqında)

- **Vebsayt:** `https://8ulduz.az` («Xəbərlər» növü ilə). **E-poçt:** `info@8ulduz.az`.
- **Haqqında:** YouTube təsvirindəki mətn (keçidlər siyahısı ilə).

## Saytda

İzlə panelində bütün hesablar öz loqosu və rəngi ilə var, YouTube da daxil (`assets/config.js` → `follow`). Hesab ünvanı dəyişsə, əvvəl `config.js`, sonra bu səhifə və hər şəbəkənin profili yenilənir.
