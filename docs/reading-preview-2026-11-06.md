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
- Böyük şriftlə planşetin yuxarı zolağı lazım olduqda yeni sətrə keçir.

## Yoxlama

- Python 274 test, Node 254 test keçdi; əlavə olaraq məlumat səhifələrinin 6 testi son rəng uyğunlaşdırmasından sonra keçdi.
- Real brauzer düymələri ilə 18→20→22 və geriyə keçid yoxlanıb; yuxarı həddə A+ söndürülür. Yaddaş və aşağı hədd testi var.
- 18/20/22 px ölçülərinin hər birində 320/390/768/1366 enlərində sənəd daşmır.
- LF ilə ölçü (Pages): app.css 94710→94794 bayt, gzip 21526→21593 (+67); app.js 219996→219983, gzip −1; index.html 29966→29946, gzip dəyişmir. Yeni asılılıq və şəbəkə sorğusu yoxdur.
- Yayım yoxdur; yayım sonrası avtomatik sürət büdcəsi hələ işlədilməyib.

Mənbə qaydaları və sürətli dövrə dəyişmir.
