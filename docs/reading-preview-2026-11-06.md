# Rəng və şrift önizləməsi — 2026-11-06

Vəziyyət: yalnız yerli önizləmə. Sahib canlıya tətbiqdən əvvəl görmək istəyir; budaq göndərilmir, PR və yayım yoxdur.

## Rənglər

- Tünd: qrafit fon #20252b, kart #292f36, mətn #e1e3e6.
- Açıq: isti kağız fon #eae7df, kart #f3f0e8, mətn #30343a.
- Başlıq, altlıq və yardımçı səthlər həmin palitraya uyğunlaşdırılıb; şəkillərin üzərindəki ağ mətn saxlanır.
- «Haqqımızda» və məxfilik səhifələrinin rəngləri də uyğunlaşdırılıb.
- Ümumi səthlərdə hesablanmış minimum kontrast: tünd əsas mətn 8,96:1, yardımçı mətn 5,19:1; açıq əsas mətn 9,23:1, yardımçı mətn 4,63:1. Vurğu keçidləri minimum 4,8:1. Bu, bütün saytın əlçatanlıq auditi və ya göz yorğunluğunun aradan qalxması zəmanəti deyil.

## Şrift

- Yeni əsas ölçü əvvəlki iki A+ klikinin nəticəsidir: gövdə 18 px, xəbər başlığı 21 px, kart başlığı 22 px.
- Pillələr: 15 / 17 / **18** / 20 / 22 px. Əsas ölçüdən iki pillə hər istiqamətdə dəyişir.
- Köhnə 0/1/2 seçimlərinin görünən ölçüsü dəyişmir; yeni seçimlər də eyni yaddaş açarında saxlanır.
- CSS-in öz əsas ölçüsü də 18 px-dir: JavaScript gözlənilmir və yaddaş bağlananda kiçik şriftə qayıtmır.
- İlk HTML skripti və yaradılan bölmə/paylaşma səhifələri yeni 0–4 aralığını tanıyır; CSP hash yenilənib. Hazır ilk ekran generatorla yenilənib.
- Yalnız yeni 3/4-cü pillələrdə planşetin yuxarı zolağı lazım olduqda yeni sətrə keçir. Əsas (əvvəlki 2) ölçünün düzülüş qaydası dəyişmir.

## Yoxlama

- Python 274 test, Node 254 test keçdi; əlavə olaraq məlumat səhifələrinin 6 testi son rəng uyğunlaşdırmasından sonra keçdi.
- Real brauzer düymələri ilə 18→20→22 və geriyə keçid yoxlanıb; yuxarı həddə A+ söndürülür. Yaddaş və aşağı hədd testi var.
- 18/20/22 px ölçülərinin hər birində 320/390/768/1366 enlərində sənəd daşmır.
- LF ilə ölçü (Pages): app.css 94710→94794 bayt, gzip 21526→21593 (+67); app.js 219996→219983, gzip −1; index.html 29966→29946, gzip dəyişmir. Yeni asılılıq və şəbəkə sorğusu yoxdur.
- Yayım yoxdur; yayım sonrası avtomatik sürət büdcəsi hələ işlədilməyib.

Mənbə qaydaları və sürətli dövrə dəyişmir.

## Şəkil üzrə düzəliş

Sahib POCO X5 Pro telefonundan iki A+ klikindən sonrakı ana səhifəni göndərdi. Əvvəlki təqdimat Gündəm bölməsindən və daha dar brauzer enindən idi; onu telefonun ana səhifəsi ilə birbaşa müqayisə etmək düzgün deyildi.

Eyni 393 px enli yerli brauzerdə köhnə nüsxənin iki A+ klikindən sonrakı halı ilə yeni əsas ölçü tutuşduruldu: hər ikisində gövdə 18 px, ana slayd başlığı 22 px, Zuğulba kart mətni 18 px, kart 330×110 px, başlıq sahəsi 221,33 px, slaydın yuxarı koordinatı 314,875 px. Bütün əvvəlki 2-ci pillə şrift və sətir hündürlüyü dəyişənlərinin qorunması üçün reqressiya testi əlavə edildi.

Yeni göstərilən önizləmə ana səhifədir; mobil ölçü yoxlaması fiziki POCO cihazında yox, kompüter brauzerində aparılıb. Sistem şriftinin forması və toxunma rejiminə aid elementlər fiziki telefondan fərqlənə bilər. Canlıya tətbiq edilməyib.

## Sahibin yeni rəng təklifi — çox açıq sarı və lacivərd

Əvvəlki yayım göstərişi rəng barədə yeni mesajla dayandırıldı; yalnız git fetch icra olunmuşdu, heç bir push, PR və merge edilməmişdi.

Açıq rejimin yeni önizləməsi: fon #fff8d8, kart #fffcef, mətn #172b4d, seçilmiş düymə #19385f, düymə mətni #fff8d8. Loqo altlığı, məzənnə səthləri, altlıq və məlumat səhifələri palitraya uyğunlaşdırılıb. Bu düzəlişdə şrift və həndəsə qaydaları dəyişməyib.

Hesablanmış minimum kontrast: əsas mətn 11,53:1, yardımçı mətnlər 5,12:1 və yuxarı. Şriftin əvvəlki iki-klik ölçüsünü və böyütmə/kiçiltmə davranışını qoruyan iki test keçib. Brauzerdə 412 px enli ana səhifə yoxlanıb: üfüqi daşma yoxdur. Bu rəng variantı da yalnız önizləmədir; canlıya yayımlanmayıb.
