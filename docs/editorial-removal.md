# Xəbər çıxarma paneli

Ünvan: `https://8ulduz.az/idare/`. Telefon və kompüter üçün ayrıca səhifədir; adi oxucuya panel kodu, GitHub kitabxanası və giriş sorğusu yüklənmir.

## İstifadə

1. Sayt sahibi GitHub hesabı ilə yalnız `8ulduz/8ulduz` reposuna `Contents: Read and write` icazəsi olan məhdud giriş açarı yaradır. Paneldə həmin açarla giriş edilir. Açar çatda göndərilmir, repo və brauzer yaddaşına yazılmır; yalnız açıq səhifənin yaddaşında saxlanır. Səhifədən çıxanda və ya «Çıxış» basanda təmizlənir.
2. Xəbərin başlığı/mənbəsi ilə axtarılır və ya mənbədəki / 8ULDUZ-dakı xəbər keçidi daxil edilir. Mənbə keçidi ilə köhnə arxiv xəbəri də çıxarıla bilər.
3. «Sil» seçilir, tam başlıq və keçid yoxlanır, «Saytdan sil» basılır. Eyni xəbərin birləşdirilmiş alternativləri də qərara daxildir. Uğur yalnız GitHub yazını təsdiqləyəndən sonra göstərilir. İcazəsiz hesab və ya qorunan budaq yazını rədd edərsə silinmiş kimi təqdim edilmir.

Qərarlar `assets/content-policy.js` faylının `removedArticles` bölməsindədir: xəbər nömrəsi, keçidlər, paylaşma ID-ləri, başlıq, tarix və giriş edən hesab. Silinmə əlavə olunur və köhnə cavab onu ləğv etmir. Lent yenilənəndə, slug/başlıq dəyişəndə, arxivdən və seçilmişlərdən oxunanda xəbər geri qayıtmır. Digər xəbərlərə təsir etmir. Köhnə paylaşma önizləməsinin faylı da növbəti tam yayımda çıxır; üçüncü tərəf platformaların artıq saxladığı önizləməni sayt məcburi təmizləyə bilmir.

## Yayılma və ilk aktivləşdirmə

`editorial_sync.py` etibarlı arxa prosesdə GitHub API-dən qərarları 15 saniyədən bir alır. Xəbər dövrəsi yalnız kiçik lokal faylı oxuyur, şəbəkəni gözləmir. Qərarlar bütün `latest.<dil>.json` fayllarına `removed` ilə daxil olur; sayt öz mövcud 30 saniyəlik yoxlamasında köhnə kartı oxuma/«yeni xəbər» gözləməsinə salmadan gizlədir. Sürətli dövrənin dəqiqə yolları və vaxt rəqəmləri dəyişmir. Adətən növbəti 1–2 dəqiqəyə yayılır; GitHub və ya şəbəkə dayananda dərhal yayılma zəmanəti yoxdur. Panel qərarın saxlanmasını və canlı axına çatmasını ayrı göstərir.

**İlk yayımda** yeni `pipeline.sh` ilə işləyən yeniləyici işi lazımdır: artıq başlamış köhnə shell yeni arxa prosesi özbaşına başlatmır. Normal növbə dəyişməsi yeni versiyanı işə salır; dərhal aktivləşdirmək üçün repo sahibi yeni versiyanın işə düşməsini nəzarətlə təmin etməlidir. İşlək xəbər axını kəsilməməlidir. Yeni işin loqunda «Redaksiya silinmə siyahısı yeniləndi» sətri və canlı faylda `removed` görünmədən funksiyanı canlıda işlək saymayın.

## Bu tapşırıqda çıxarılan xəbər

Nocomment.az №555222, paylaşma ID-si `5e6cc2e84ced07dd`. Sayt sahibinin şəkillə verdiyi qərar əsasında qadağa əlavə olunub və statik paylaşma önizləməsi çıxarılıb. Brauzer bu xəbəri köhnə `data/arxiv/sosial.json` və `data/paylas/11.json` nüsxələrindən də göstərmir; dərc qapısı həmin faylların növbəti yazılışından qeydi çıxarır. Avtomatik xəbər JSON-ları PR-da əl ilə dondurulmur ki, normal xəbər yenilənməsi birləşdirmə konflikti yaratmasın. Rəqəmli sabit mənbə açarı slug variantlarını da tutur. Mənbədəki mətnin doğruluğu barədə nəticə çıxarılmır.

## Yoxlama

Testlər: icazəsiz giriş, uğursuz yazının uğur sayılmaması, eyni vaxtda dəyişmiş faylı yeni SHA ilə birləşdirmə, təkrar silinmənin sabitliyi, qruplaşmış xəbərin bütün keçidləri, dəyişən slug, arxiv/seçilmiş/paylaşılmış keçid, arxa sinxronun xətada son sağlam siyahını saxlaması. Real sahib açarı ilə istehsal yazısı bu iş mühitində yoxlanmayıb: qoşulu hesabın əsas repoya yazma icazəsi yoxdur.
