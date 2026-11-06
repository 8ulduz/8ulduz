# Fərqli rənglər və təkrar izləmə bloklarının çıxarılması — 2026-11-06

Sahibin istəyi: valyuta kartları və altmenyular fərqlənsin; açılan altmenyular «toz qatılmış kimi» az doymuş rəngdə olsun; yuxarı izləmə düyməsinin yanıb-sönən çərçivəsi qayıtsın; hava səma mavisi, namaz daha yaşıl olsun; aşağı qoşulma və izləmə blokları silinsin.

- Kart rəngi alətin sabit data-fx identifikatoruna bağlıdır: USD yaşıl, EUR mavi, RUB100 bənövşəyi, TRY100 mis; qalan alətlərin də ayrıca tonu var. Sıra və alət sayı dəyişəndə rəng başqa alətə keçmir.
- Altmenyu pillələri: tozlu mavi / yaşıl / bənövşəyi; seçilmiş element həm fon, həm əvvəlki on sinfi ilə seçilir. Telefon sətirləri və kompüterdə açılan sütunlar eyni rəng sistemindən istifadə edir.
- Yuxarı izləmə düyməsi telefon və kompüterdə saxlanır; qızılı/mavi opacity animasiyası bərpa edilib. Hərəkəti dayandırma və reduced-motion seçimi qüvvədədir.
- Hava və namaz düymələri ilə açılan panellərin rəngləri birlikdə dəyişir.
- Aşağı kanal reklamı və altlıqdakı ikinci izləmə düyməsi statik və dinamik HTML-dən çıxarılıb; işlədilməyən CSS və render kodu silinib. Əlaqə və məlumat keçidləri, rəsmi kanalların yuxarı paneli saxlanır.
- Şrift ölçüləri, əsas açıq/tünd fonlar, mənbə qaydaları və dəqiqəlik dövrə dəyişmir. sw v59.

Yoxlama: Python 274, Node 258 test keçib. Aşağı blokların olmaması və yuxarı düymənin saxlanması reqressiya testində qorunur. 393/768/1366 px enlərində iki rejimdə daşma yoxdur; izləmə paneli, altmenyu və hava/namaz panelləri yerli brauzerdə açılıb yoxlanıb.

Sıxılmış ilkin fayllar: CSS 21547→21702 B, JS 73845→73519 B, HTML 8345→8218 B; cəmi −298 B. Yeni sorğu və asılılıq yoxdur. CSS LF 94508 B, JS LF 219230 B; ölçü limitləri qorunur.
