# 8ulduz oxucu yoxlaması — 29 oktyabr 2026

Canlı sayt brauzerdə, dəyişikliklər yerli serverdə 320, 390 və 430 CSS piksel enində yoxlanılıb. Telefon sınağı iframe-in həqiqi dar görünüş sahəsində aparılıb; fiziki Android/iPhone və virtual klaviatura sınağı deyil.

## Təsdiqlənmiş problemlər və düzəlişlər

| Prioritet | Təkrar ssenarisi | Düzəliş |
| --- | --- | --- |
| P1 | Köməkçi → Son xəbərlər. Cavab yalnız Oxu.az-dandır: “oxu” əmri mənbə adı sayılır. | Oxu.az yalnız açıq adlandırılanda seçilir; ümumi oxu əmrləri bütün uyğun mənbələrdən gəlir. |
| P1 | Video → Ceyhun Bayramovun jesti → 9 mənbə. Alternativlərdə Tramp–Ərdoğan telefon danışığı da var. | Saxlanmış alternativlər başlıq və vaxtla yenidən yoxlanır. Başlığı olmayan köhnə alternativlərə kor-koranə etibar edilmir. Yeni alternativlər başlıq və dilini saxlayır; zidd şəxslər və zəif başlıq uyğunluğu olan hadisələr ayrılır. |
| P2 | Tıxac səhifəsi: İspaniyada qatar qəzası, helikopter qəzası və başsağlığı mesajları Bakı yol vəziyyəti kimi göstərilir. | Yerli başlıq və iki saatlıq təzəlik şərti; aviasiya, dəmir yolu və başsağlığı çıxarılır. Eyni seçim köməkçiyə tətbiq olunur. Boş siyahı “tıxac yoxdur” kimi təqdim edilmir. |
| P2 | Telefon görünüşündə əlavə sətirə düşən menyu, təkrarlanan Tıxac keçidi və köməkçi/alt panel yaxınlığı. | Bir sətir bölmə menyusu, yığcam üst panel, alt panelin üstündə köməkçi, təhlükəsiz ekran kənarı, 44 px düymələr və 16 px form şrifti. |
| P2 | Altlıqda 72, mənbə vəziyyətində 83 mənbə. | Altlıq və Haqqımızda səhifəsi xəbər kartlarının sayından deyil, izlənilən mənbələr reyestrindən istifadə edir. |
| P2 | Azərbaycan dili seçiləndə ingiliscə “Why President…” başlığı görünür. | Azərbaycan dilində xülasəyə baxmayaraq ingiliscə başlığın dili müəyyənləşdirilir; köhnə az etiketləri də yenidən yoxlanır. |
| P2 | Köməkçinin tarixləri “M10 29” kimi çıxır. | Bakı saat qurşağı və açıq Azərbaycan ay adları; cihazın az-AZ dəstəyindən asılı deyil. |
| P2 | Sistem “hərəkəti azalt” seçsə də xəbər lenti hərəkət edir. | JavaScript animasiyası həmin seçimi nəzərə alır. |
| P3 | Səhifə yüklənərkən boş Telegram kanalına çağırış görünür. | Çağırış ilkin HTML-də gizlidir; yalnız kanal təyin ediləndə açılır. |

## İcra olunmuş yoxlamalar

- Canlı saytda nəticəsiz axtarış və aydın boş vəziyyət; seçilmişlərə əlavə, yeniləmə sonrası yadda qalma və çıxarma.
- Mənbə vəziyyəti, valyuta çeviricisinin açılması və 100 USD → 170 AZN göstərməsi, namaz və bölgələr üzrə hava panellərinin açılması.
- Köməkçinin “Son xəbərlər” cavabı, səs mövcud olmayanda mətnlə cavab; video siyahısı və alternativ mənbələrin açılması.
- Yerli telefona uyğun görünüşdə 320/390/430 px başlıq, əlavə menyunun açılması, alt naviqasiya və köməkçi aralığı.
- Python unittest: 51 test. Node test runner: 46 test. JavaScript sintaksisi və git diff whitespace yoxlaması.

## Qalan məhdudiyyətlər

- Oxu.az lentində 403 cavabı canlıda görünür. Bu, xarici xidmətin bloklamasıdır; icazəsiz qoruma keçidi tətbiq edilmir.
- Xəritənin iframe-i açılır; Waze-in daxili yol məlumatının doğruluğu və bütün xarici xəbər keçidləri bu yoxlama ilə təsdiqlənmir.
- Mikrofon icazəsi verilməsi, real səs tanıma, bildiriş icazəsi, fiziki telefonda klaviatura və bütün video yayımlar ayrıca cihaz sınağı tələb edir.
- Eyni hadisənin avtomatik qruplaşdırılması evristikdir. Başlığı olmayan köhnə alternativlər çıxarıldıqdan sonra mənbə sayı növbəti RSS yenilənmələrində yenidən formalaşır.
- Yerli yol filtri dəqiq məkan qeyd etməyən xəbəri buraxa bilər; canlı ölçü əvəzinə xəbər siyahısı olduğu açıq yazılır.
- Avtomatik data faylları bu PR-də dəyişdirilmir. Dil və qruplaşdırma düzəlişləri updater-in növbəti uğurlu işləməsində tətbiq olunur.
