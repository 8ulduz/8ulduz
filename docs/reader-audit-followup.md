# Təkrar oxucu auditi — ardıcıl iş siyahısı

Əvvəlki auditdən sonra canlı sayt və cari main yenidən yoxlanılır. Telefon yenilənməsi istifadəçinin göstərişi ilə birinci prioritetdir.

| ID | Prioritet | Təsdiqlənmiş problem / yoxlama | Vəziyyət |
| --- | --- | --- | --- |
| R01 | P1 | Telefonda dayanan fetch/json/şəkil sorğusu xəbər yenilənməsini müddətsiz saxlaya bilər. Qayıdış yalnız eyni status faylını yoxlayır. | Düzəliş hazırlanır: müddət limiti, köhnə sorğunun ləğvi, qayıdışda məcburi yoxlama, əl ilə ↻. |
| R02 | P1 | Azərbaycan qəzeti RSS-i bütün yazılara sorğu vaxtını və yanlış +0000 zonasını yazır. Canlı RSS nümunələri və məqalə ünvanındakı sabit vaxt müqayisə edildi. | Düzəliş hazırlanır: bu mənbə üçün sabit URL tarixindən ehtiyat vaxt, köhnə qeydlərin də bərpası. |
| R03 | P2 | Mənbə axtarışında nəticə olmayanda boş sahə və dəyişməyən 83 sayı qalır. | Növbədə. |
| R04 | P2 | Çevirici açıq ikən marşrut dəyişəndə və Escape basılanda panel qalır. | Növbədə. |
| R05 | P2 | Bitcoin çevirməsinin ilkin/yenidən render çıxışı ilə girişdən sonrakı çıxış dəqiqliyi fərqlənir. | Növbədə. |
| R06 | P2 | Bölmə seçimlərinin checkbox və yuxarı/aşağı düymələri bölməni adlandırmır; yenidən render fokusunu itirir. | Növbədə. |
| R07 | P2 | Namazın növbəti vaxtı cihazın saat qurşağında hesablanır; gün dəyişməsi üçün yenidən sorğu yoxdur. | Növbədə. |
| R08 | P2 | Sürücü rejimi mətn sorğusunu səhifə ömrü boyu saxlayır; yeni doldurulan mətnlər yenidən alınmır. | Növbədə. |
| R09 | Məhdudiyyət | Azərbaycan səsi olmayan cihazda bütün telefonlar üçün audio zəmanəti yoxdur. | Ödənişli TTS xidməti hələ seçilməyib; avtomatik hesab və ödəniş açılmır. |

Yoxlama sərhədi: görünüş sınaqları CSS 320/390/430 px enindədir; fiziki telefona uzaqdan giriş yoxdur. Mikrofon/bildiriş icazələri və maliyyə/abunə əməliyyatları yaradılmır. Mənbə mətni səhifədə göstərilmir.
