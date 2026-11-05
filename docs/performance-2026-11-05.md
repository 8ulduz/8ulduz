# Açılış yükünün yoxlanması — 5 noyabr 2026

Baza: `d73e9549b1489c1505898a20242400cc72ec3c90`. Düzəliş mövcud görünüşü, 30 saniyəlik yoxlamanı, dəqiqəlik canlı kanalı və mənbə qaydalarını saxlayır. Domen və Cloudflare ayarları dəyişdirilməyib.

## Dəyişiklik

- Axtarış mikrofonu bütün `assistant.js` əvəzinə ayrıca `voice-search.js` yükləyir. Mövcud funksiyalar dəyişdirilmədən köçürülüb; köməkçi eyni funksiyanı import edir və əvvəlki ixracları saxlayır.
- Service worker v47 ilk quraşdırmada əsas qabığı və mikrofon modulunu saxlayır. Sönülü köməkçi/sürücü modulları, iri quraşdırma ikonları və paylaşım şəkli ilk quraşdırmada əvvəlcədən istənmir. Bu fayllar istifadə olunanda əvvəlki `cachedShell` / `cacheFirst` qaydası ilə saxlanır.

| Yük | Əvvəl | Sonra |
| --- | ---: | ---: |
| Mikrofon üçün ilkin modul, gzip | 9 830 B | 1 573 B |
| İlkin keş siyahısındakı resursların cəmi | 316 057 B | 152 166 B |

Keş cəmi mətn fayllarını gzip, PNG fayllarını öz ölçüsü ilə hesablayır. Bu, siyahının çəkisidir; faktiki əlavə şəbəkə ötürülməsi HTTP keşindən və brauzerin hansı faylları artıq yükləməsindən asılıdır. Quraşdırma şəkilləri, paylaşım şəkli və funksiyalar silinməyib.

## Ölçmə

Lighthouse 12.8.2, yalnız performance, standart telefon/CPU modeli; planşet 768×1024, kompüter desktop profili. Lokal A/B eyni gzip serveri və eyni məlumat faylları ilə aparılıb. Hər ölçü təmiz brauzer profili ilə başlayır. Lokal müqayisədə dəyişən canlı kanal, statistika, hava və namaz xidmətləri bloklanıb; şəkillər eyni xarici ünvanlardan gəlib. Bu rəqəmlər Azərbaycan mobil operatorunda cihaz ölçməsi deyil.

İlk canlı telefon ölçüsü: 81 bal, FCP 1,49 s, LCP 2,92 s, TBT 514 ms, yük 786 720 B. Ayrı curl sorğusunda DNS/TCP/TLS daxil ilk bayt 0,616 s idi; həmin Lighthouse ölçüsündə sənədin server gözləməsi 109 ms-dir. Bu iki rəqəm fərqli hissələri ölçür, hamısını server məsafəsi kimi izah etmək düzgün deyil.

Yekun kodla ardıcıl nəzarət cütləri, əlavə sınaq vərəqləri bağlandıqdan sonra:

| Profil | Bal əvvəl → sonra | FCP əvvəl → sonra | LCP əvvəl → sonra | TBT əvvəl → sonra |
| --- | ---: | ---: | ---: | ---: |
| Telefon | 85 → 85 | 1,15 → 1,08 s | 3,19 → 3,20 s | 362 → 347 ms |
| Planşet | 85 → 82 | 1,16 → 1,23 s | 3,20 → 3,06 s | 361 → 476 ms |

Digər ölçülər geniş dəyişib: baza telefon 76–85 bal, yekun variant 74–85; baza planşet 77–85, yekun variant 68–82. Yekun kompüter yoxlaması 95 bal / LCP 1,05 s, baza 90 / 1,15 s idi (hərəsi bir ölçü). Platformalar üzrə bal artımı və ya tam vizual sürətlənmə təsdiqlənmiş nəticə kimi təqdim edilmir; planşetin TBT fərqi də nəzərə alınmalıdır. Dəyişikliyin müəyyən nəticəsi ilkin tələb olunan kodun və keş siyahısının həcminin azalmasıdır.

`first.json` sorğusunun prioritetinin azaldılması ayrıca yoxlanıb və saxlanılmayıb. `index.html` və CSP əvvəlki vəziyyətdədir.

## Yoxlama

- `node --test tests/*.test.cjs`: 205 test keçib.
- `python -X utf8 -m unittest discover -s tests -v`: 260 test keçib.
- Yeni service worker sınağı: köməkçi resursların əlçatmazlığı əsas qabığın quraşdırılmasına mane olmur; sonradan istifadə olunan modul oflayn da açılır.
- Modul və service worker sintaksis yoxlamaları, CSP yoxlaması keçib.
- 390 px brauzer yoxlaması: üfüqi daşma yoxdur; axtarış, idman bölməsi və baş səhifəyə qayıdış işləyir. Mikrofon düyməsi göstərilir; real səs tanıma xidməti açılmayıb, davranışı mövcud avtomatik sınaqlarla yoxlanıb.

Əsas repoya birbaşa yazma hüququ olmadığı üçün nəticə baxış sorğusu ilə təqdim olunur. Canlı dərc və Cloudflare keçidi bu işdə edilməyib.
