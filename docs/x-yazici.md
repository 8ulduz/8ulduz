# X xəbərlərinin yazıcısı (planlı Claude tapşırığı)

Sahibin qərarı (2026-11-18): X-in türk dilli rəsmi hesablarının videolu paylaşımlarından 8ULDUZ-un öz xəbərləri. Avtomatik
tərcümə GitHub-dan işləmir (`oz_dunya.py`-yə baxın), ona görə mətni bu kompüterdəki planlı Claude tapşırığı yazır və
`oz_x.json` növbəsinə qoyur. Dərc hissəsi (`oz_derc.py`, yavaş dövrə) növbəni oxuyur, qapılardan keçirir və hədlərlə
dərc edir (gündə ən çox 8, saatda ən çox 4 öz xəbər). Bu sənəd tapşırığın təlimatıdır.

## Hər işə salınmada

1. `C:\Users\user\8ulduz` qovluğunda `git switch main` və `git pull --rebase -q`. Yerli dəyişiklik varsa toxunmayın,
   dayanın və səbəbini yazın (`miss.tmp.txt`-ə heç vaxt toxunmayın).
2. `oz_x.py`-dəki `HESABLAR` cədvəlinin hər hesabı üçün `https://api.fxtwitter.com/2/profile/<hesab>/statuses` (açarsız,
   API-siz). Cavabın `results` siyahısından yalnız bunları götürün:
   - son 6 saatın paylaşımları, `media.videos` dolu, `reposted_by` boş, `replying_to` boş;
   - id-si `oz_x.json`-da artıq olmayanlar;
   - reklam, sponsor, bilet/mağaza, mərc, qəza və ya zorakılıq görüntüsü OLMAYANLAR.
3. Qırmızı xətt (docs/qirmizi-xetler.md): Azərbaycan, onun rəhbərliyi, Bakı, Qarabağ, azərbaycanlı oyunçu və ya klub keçən
   paylaşımı **götürməyin** (kod da rədd edir: `content_policy.AZ_TERMS`, `LEADER_TERMS`). Müxalifət mənbəyi yoxdur:
   yalnız cədvəldəki hesablar.
4. Ən maraqlı 1–4 paylaşımı seçin (idman, dünya, elm; oxucunun izləmək istəyəcəyi video). Hər biri üçün sətir:

```json
{"id": "<paylaşımın id-si>", "date": "<Bakı günü, YYYY-MM-DD>", "slot": "<Bakı vaxtı indi + 5 dəq, SS:DD, 07:00–22:00; sonra yazılan gün bitənədək dərc olunmur>",
 "kind": "x-idman | x-dunya | x-elm | x-maraqli", "handle": "<hesab, cədvəldəki kimi>",
 "post": "https://x.com/<hesab>/status/<id>",
 "video": "<formats-dan mp4, bitrate ≤ 1 000 000 olanların ən yaxşısı (adətən 480x852 və ya 640x360)>",
 "poster": "<media.videos[0].thumbnail_url>", "w": <media.videos[0].width>, "h": <media.videos[0].height>,
 "title": "...", "lead": "...", "body": ["..."], "src": ["<paylaşımın orijinal mətni, olduğu kimi>"]}
```

## Mətn qaydaları (`oz_x.check` yoxlayır; pozulsa xəbər dərc olunmur)

- Azərbaycan ədəbi dilində, türkcə söz və şəkilçi olmadan («yapıldı» yox, «edildi»; «maç» yox, «oyun»).
- Başlıq 25–110 hərf, sonunda nöqtə, sual, nida yoxdur. Giriş 60–420 hərf. Mətn 1–4 abzas, hər biri 40–800 hərf.
- Nida işarəsi, keçid, kiril hərfi yoxdur. «bu gün», «dünən», «sabah», «bu axşam» kimi nisbi gün sözləri yoxdur.
- Mətndəki hər rəqəm paylaşımın mətnində olmalıdır. Paylaşımda olmayan fakt əlavə etməyin; videoda görünən, amma mətndə
  yazılmayanı təsvir etməyin. Mənbəni adı ilə deyin: «Qalatasaray klubunun paylaşdığı videoda…».
- Prezident və rəhbərlik adları keçmir.

## Növbəni yazmaq

5. Yeni sətirləri `oz_x.json`-un `items` siyahısının sonuna əlavə edin; `date`-i 4 gündən köhnə sətirləri silin.
   Fayl `{"v": 1, "items": [...]}` formasında, UTF-8, 2 boşluqlu girinti ilə qalır.
6. Yalnız `oz_x.json`-u commit edin: müəllif `8ulduz <346370484+8ulduz@users.noreply.github.com>`, mesaj
   «X xəbərləri növbəyə əlavə edildi», sonda `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
   `git pull --rebase -q`, sonra `git push -q origin main` (yalnız `8ulduz/8ulduz`, yalnız `8ulduz` hesabı;
   `gh auth switch` işlətməyin). Push alınmasa bir dəfə yenidən pull + push; yenə alınmasa dayanın.
7. Yeni uyğun paylaşım yoxdursa heç nə commit etməyin.
