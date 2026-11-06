# Oxu görünüşü — təsdiqlənmiş rənglər və şrift

Sahib 2026-11-06 tarixində önizləmələri təsdiqlədi: «bunları tətbiq et baxaq qiymətləndirək rəylər əsasında».

## Yekun görünüş

- Açıq rejim: çox açıq sarı fon #fff8d8, kart #fffcef, lacivərd mətn #172b4d, seçilmiş düymə #19385f.
- Tünd rejim: dərin mat lacivərd fon #15233b, kart #1c2c46, mətn #d5deeb; tünd rejimin parıldayan izləmə çərçivələri yoxdur.
- Məlumat səhifələri və brauzer rəng metadatası palitraya uyğunlaşdırılıb.
- Əsas ölçü əvvəlki iki A+ klikinin nəticəsidir: gövdə 18 px, ana slayd başlığı 22 px, Zuğulba kart mətni 18 px.
- Pillələr 15 / 17 / **18** / 20 / 22 px-dir. Mövcud saxlanmış 0/1/2 ölçüləri dəyişmir; yeni ziyarətçi əsas 18 px ölçünü görür. Hər ölçü yadda qalır, iki istiqamətdə dəyişir.
- Əsas telefon düzülüşü saxlanır. Planşetdə böyümüş əsas şriftə görə yuxarı zolaq lazım olduqda yeni sətrə keçir; lent daşmır.

## Yoxlama

- Python 274, Node 258 test keçir; şriftin ölçü dəyişənlərinin əvvəlki iki-klik halı ilə eyniliyi, sərhədlər və yaddaş testi var.
- Son yerli brauzer yoxlaması: hər iki rejimdə 393 / 412 / 768 / 1366 px, gövdə 18 px, üfüqi daşma yoxdur. Bu, fiziki POCO cihazı yox, brauzer ölçü yoxlamasıdır.
- Köhnə iki-klik və yeni əsas ölçü eyni 393 px sınaqda eynidir: Zuğulba kartı 330×110 px, ana slayd başlığı 22 px, kart mətni 18 px.
- Ümumi səthlərdə hesablanmış minimum kontrast: tünd əsas mətn 8,65:1, yardımçı 5,38:1; açıq əsas mətn 11,53:1, yardımçı 5,12:1. Bu, tam əlçatanlıq auditi və ya göz yorğunluğuna tibbi zəmanət deyil.
- Pages-dəki LF ilə ölçü: app.css 94710→94591 B (gzip 21526→21547), app.js 219996→219983 B (gzip 73844→73845), index.html 30392→30378 B (gzip 8376→8381). İlkin sıxılmış yük fərqi cəmi +27 baytdır; əlavə sorğu və asılılıq yoxdur.
- CSP hash və yaradılan bölmə/xəbər səhifələrinin erkən şrift seçimi yenilənib; hazır ana səhifə generatorla qurulub. sw v58.

## Qırmızı xətlər və geri qaytarma

Mənbə siyahısı, content_policy və sürətli xəbər dövrəsi dəyişmir; updater dəyişiklikləri yalnız yaradılan HTML-in şrift/rəng metadatasıdır. PR-də kod yoxlaması və real lentlərlə bir-deqiqe işi, main-də ayrıca sürət büdcəsi işləyir.

Bu PR ayrıca görünüş dəyişikliyidir. Narazılıq olarsa yalnız bu PR geri qaytarılmalıdır; main-in son xəbər məlumatı və sonrakı dəyişiklikləri saxlanmalıdır. Geri qaytarma yayımında service-worker versiyası yenidən artırılmalıdır. İstifadəçi rəyləri əsasında rənglər sonradan tənzimlənə bilər.
