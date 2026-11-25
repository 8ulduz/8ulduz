# Öz videolarımızın veb nüsxəsi (Cloudflare R2)

Sahib, 2026-11-25: «ən vacib qırmızı cizgi-gözqırpımı sürətidir», «video xəbərlərdə bəzi videolar (əsasən azərbaycan) 1-2 saniyəyə açılır».

## Nə üçün

Ana səhifənin «Video xəbərlər» zolağı (`assets/vlent.js`) öz videolarımızı YouTube oynadıcısı ilə oynadırdı. Ölçü (2026-11-25, kompüter brauzeri):

- basışdan ilk kadra 2,4 s, oynadıcı əvvəlcədən açılıbsa 1,7 s;
- növbəti kart əvvəlcədən hazırlananda (PR 330) 0,4–0,5 s;
- telefonda qara ekran, fırlanan dairə, ⏸ işarəsi və «Shorts» yazısı görünürdü.

X videoları adi `<video>` ilə oynayır və 0,2–0,5 s-də başlayır. Öz videomuzun da kiçik MP4 nüsxəsi olsa, zolaq onu X videosu kimi oynada bilər.

Telekanalların YouTube videoları (ARB 24, Real TV və s.) YouTube oynadıcısında qalır. Onların faylını götürmək olmaz.

## Necə işləyir

1. `sosial-video.yml` «video» işi videonu hazırlayıb yoxlayandan sonra «Veb nüsxə» addımı ffmpeg ilə kiçik nüsxə qurur (`veb-video.cjs hazirla`):
   - 720×1280, H.264, AAC 64 kb/s;
   - ≤ 2,8 MB (bitreyt müddətə görə hesablanır);
   - moov faylın əvvəlindədir (`+faststart`).

   Fayl artefaktda `veb.mp4` adı ilə qalır. TikTok və YouTube yükləyicisi onu götürmür, çünki cütü olan `.json` yoxdur.
2. YouTube işi videonu yükləyir və nömrəsini çıxışa yazır (`video_id`).
3. «veb-video» işi faylı R2-yə `<YouTube nömrəsi>.mp4` adı ilə yazır (`veb-video.cjs yukle`). Sonra açıq ünvanı Range sorğusu ilə yoxlayır: cavab 206 olmalı, növü `video/mp4` olmalı, yönləndirmə olmamalıdır. Yoxlamadan keçən fayl `index.json` siyahısına düşür. 30 gündən köhnə fayllar silinir.
4. `updater.py` (`update_video`, yavaş dövrə) `https://video.8ulduz.az/index.json`-u oxuyur. Siyahıdakı öz videomuza `data/video.json`-da `mp4` sahəsi yazır.
5. `vlent.js` `mp4` sahəsi olan öz videonu adi `<video>` ilə oynadır:
   - yalnız növbəti kart əvvəlcədən yüklənir;
   - qənaət rejimində və «hərəkəti azalt» seçiləndə heç nə əvvəlcədən yüklənmir.

   Sahə yoxdursa (köhnə video, R2 qurulmayıb, siyahı oxunmayıb) video əvvəlki kimi YouTube-dan oynayır.

Açarlar olmayanda «veb-video» işi heç nə etmir və yaşıl qalır. Sayt dəyişmir, zolaq YouTube ilə işləyir.

## Saxlama yerinin seçimi (2026-11-25, curl ilə yoxlanıb)

| Namizəd | Range | MIME | Yönləndirmə | Nəticə |
|---|---|---|---|---|
| Cloudflare R2 + öz domen | 206 | `video/mp4` (yükləyəndə verilir) | yoxdur | **seçildi**: pulsuz (10 GB, çıxış trafiki pulsuz), Bakı kənarı (GYD), main-ə yazılmır |
| raw.githubusercontent.com (tarixçəsiz budaq) | 206 | `application/octet-stream` + `nosniff` | yoxdur | rədd: iPhone Safari-də risk; tələb `video/mp4`-dür |
| GitHub Pages (8ulduz.az) | 206 | düzgün | yoxdur | rədd: fayl main-ə düşür, tarixçə şişir |
| GitHub Release | — | — | 302 → release-assets | rədd: 3xx bfcache-i söndürür |
| jsDelivr (/gh/) | 206 | `video/mp4` | yoxdur | rədd: budaq 12 saat keşlənir, üçüncü tərəfdir |

`r2.dev` ünvanı istifadə olunmur. Cloudflare-in sənədinə görə həmin ünvanın sürəti məhdudlaşdırılıb və o, yalnız sınaq üçündür. Keş də yalnız öz domendə işləyir.

## Sahibin addımları (bir dəfə)

Parol və açar heç kimə göndərilmir. Açarlar yalnız GitHub-ın «Secrets» bölməsinə yazılır.

1. **R2-ni açın.** [dash.cloudflare.com](https://dash.cloudflare.com)-a daxil olun. `8ulduz.az` zonasının olduğu hesabı seçin və **R2 Object Storage** bölməsinə keçin.
   R2-ni ilk dəfə açanda Cloudflare ödəniş üsulu (kart) istəyir. Pulsuz həddə pul tutulmur: ayda 10 GB saxlama, 1 milyon yazma və 10 milyon oxuma əməliyyatı. Bizə lazım olan ~0,7 GB-dır.
2. **Bucket yaradın.** **Create bucket** düyməsini basın:
   - ad: `8ulduz-video`;
   - Location: Automatic;
   - Storage class: Standard.

   **Create bucket**-i basın.
3. **Öz domeni qoşun.** Bucket-də **Settings** → **Custom Domains** → **Add** bölməsinə keçin və `video.8ulduz.az` yazın, sonra **Continue** → **Connect domain**. DNS yazısını Cloudflare özü əlavə edir. Bir neçə dəqiqə sonra vəziyyət **Active** olmalıdır.
   «Public Development URL» (r2.dev) bağlı qalsın.
4. **Açar yaradın.** R2 Object Storage → **Overview** bölməsində sağda **API Tokens** → **Manage**, sonra **Create Account API token**:
   - Token name: `github-veb-video`;
   - Permissions: **Object Read & Write**;
   - Specify bucket(s): **Apply to specific buckets only** → `8ulduz-video`;
   - TTL: Forever.

   **Create API Token**-i basın. Növbəti səhifədə üç dəyər bir dəfə göstərilir: **Access Key ID**, **Secret Access Key** və S3 ünvanı (`https://<hesab nömrəsi>.r2.cloudflarestorage.com`).
5. **GitHub-a yazın.** [github.com/8ulduz/8ulduz](https://github.com/8ulduz/8ulduz) → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**. Üç sirr əlavə edin:
   - `R2_ENDPOINT` — S3 ünvanı (`https://….r2.cloudflarestorage.com`);
   - `R2_ACCESS_KEY_ID` — Access Key ID;
   - `R2_SECRET_ACCESS_KEY` — Secret Access Key.

   Bucket adını dəyişmisinizsə, **Variables** bölməsinə `R2_BUCKET` əlavə edin.
6. **Yoxlayın.** YouTube-a növbəti video yüklənəndə «Video xəbər» işinin «veb-video» addımının jurnalında «yazıldı — https://video.8ulduz.az/….mp4» sətri görünməlidir. Sonra bu ünvan 200 cavabı və video siyahısını verməlidir: <https://video.8ulduz.az/index.json>. ~10 dəqiqə sonra video zolaqda adi video kimi oynayır.

   Jurnalda «açıq ünvan 404 verdi» yazılırsa, 3-cü addımı yoxlayın (domen Active olmalıdır). «R2-yə yazılmadı (403 AccessDenied)» yazılırsa, 4-cü addımdakı icazəni və bucket adını yoxlayın.

Söndürmək üçün `R2_ACCESS_KEY_ID` sirrini silmək kifayətdir. Siyahı yenilənmir və zolaqdakı öz videolar ~1 gün ərzində YouTube oynadıcısına qayıdır. Dərhal söndürmək üçün bucket-dəki `index.json` faylını silin.

## Bilinən hədlər

- Dəyişiklikdən əvvəl yüklənmiş videoların veb nüsxəsi yoxdur. Artefakt 3 gün saxlanır, YouTube-dan fayl götürülmür. Zolaq kanalın son 10 videosunu göstərir, gündə ~8 video yüklənir. Ona görə R2 qurulandan ~1 gün sonra zolaqdakı öz videoların hamısı adi video olacaq.
- Video səhifəsi (`#/videolent?v=`) və iOS/Android tətbiqləri əvvəlki kimi YouTube oynadıcısını işlədir.
