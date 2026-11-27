# X xəbərlərinin yazıcısı

Sahibin qərarı (2026-11-18): X-in türk dilli rəsmi hesablarının videolu paylaşımlarından 8ULDUZ-un öz xəbərləri. Avtomatik
tərcümə GitHub-dan işləmir (`oz_dunya.py`-yə baxın), ona görə mətni yazıcı yazır və `oz_x.json` növbəsinə qoyur. Yazıcı
əvvəl bu kompüterdəki planlı Claude tapşırığı idi; sahibin həmin gün sonrakı göstərişi ilə («bunu avtomatlaşdır. claude nin
açıq bağlı olmasına bağlama») GitHub Actions-dadır: `.github/workflows/x-yazici.yml`, `.github/scripts/x_yazici.py`. Dərc
hissəsi (`oz_derc.py`, yavaş dövrə) növbəni oxuyur, qapılardan keçirir və hədlərlə dərc edir (gündə ən çox 8, saatda ən çox 4
öz xəbər). Növbə faylı main-də deyil, `x-novbe` budağındadır (aşağıda «Növbə budağı»). Aşağıdakı addımlar yazıcının
qaydalarıdır; əl ilə yazılsa da eyni qaydalar keçərlidir.

## Növbə budağı: `x-novbe` (sahib, 2026-11-27)

Sahibin göstərişi (2026-11-27): «bu təklifini daha dərindən araşdır … nələr etmək olar kodda? … tap və düzəlt». Qərar: yazıcı
`oz_x.json`-u **yalnız `x-novbe` budağına** yazır, main-ə heç nə yazmır. 2026-11-18-in icazəsi («yalnız `oz_x.json`, birbaşa
main») bununla əvəz olunub. İcazə başqa fayla və ya budağa genişlənmir.

**Niyə.** main-ə hər yazı ayrıca Pages yığımıdır (orta 44–46 s, 37–58 s). Yığım Fastly CDN-i təmizləyir və bütün faylların
ETag-ını dəyişir: təmizlənmədən sonra ilk açılış 100–220 ms yavaş olur, oxucunun service worker-i dəyişməmiş faylları yenidən
yükləyir. Üst-üstə düşən yığımlar ləğv olunur və ya düşür. Ölçü (GitHub API, UTC günləri):

| Gün | main-ə yazı | «Xəbərlər yeniləndi» | «X xəbərləri növbəyə əlavə edildi» | PR birləşməsi | Pages yığımı (ləğv / düşən) |
|---|---|---|---|---|---|
| 2026-11-22 | 230 | 120 | 90 | 20 | 223 (20 / 0) |
| 2026-11-23 | 209 | 112 | 80 | 17 | 202 (16 / 0) |
| 2026-11-24 | 214 | 117 | 81 | 16 | 212 (15 / 0) |
| 2026-11-25 | 203 | 99 | 89 | 15 | 200 (13 / 2) |
| 2026-11-26 | 220 | 116 | 87 | 17 | 219 (17 / 0) |

«main-ə yazı» = iki bot yazısı + birləşmə (PR-ın öz commit-ləri ayrıca yazı deyil). X yazıları bot yazılarının 43%-i idi
(2026-11-26: 87 / 203). Gözlənilən: X-in main yazısı gündə ~84 → 0; main-ə yazı və Pages yığımı gündə ~215 → ~130 (−40%);
xəbər axınının yazısı dəyişmir (10 dəqiqədən bir, gündə ≤ 144). Budağa yazı Pages yığımı başlatmır (Pages yalnız main-dən
yığılır) və heç bir iş axınını işə salmır (budaqda iş axını faylı yoxdur, `on: push` hamısı başqa budaqlara bağlıdır).

**Yazıcı** (`x-yazici.yml`): kod main-dən gəlir. `git ls-remote --exit-code --heads origin refs/heads/x-novbe`:
- budaq yoxdursa (çıxış kodu 2; keçiddən sonrakı ilk iş) main-in həmin andakı `oz_x.json`-u ilə valideynsiz commit yaradılır
  və göndərilir: keçiddə heç bir sətir itmir. Budaq bu arada yaranıbsa push rədd olunur və onun nüsxəsi oxunur;
- başqa xətada iş dayanır, heç nəyə toxunmur;
- budağın nüsxəsi (`git fetch --depth 1`, tam adla: eyni adlı teq qısa addan öndə gələ bilər) iş qovluğundakı `oz_x.json`-u
  əvəz edir, `x_yazici.py` onu oxuyub yazır. Dəyişiklik varsa budağa bir commit: `git pull --rebase` + push, 5 cəhd.
  Toqquşmada və ya birləşmə JSON-u pozanda heç nə yazılmır: budaqdakı sətirlər qalır, bu işin videoları növbəti işdə yenidən
  namizəd olur. `--force` yoxdur.

Budaqda yalnız `oz_x.json` var, tarixçəsi qalır (hər yazı bir commit). Bir günün 83 nüsxəsi git-də sıxılanda ~1 MB-dır
(2026-11-26-nın nüsxələri ilə ölçülüb; xam 97 MB). main-in dayaz klonlarına (`fetch-depth: 1`) budaq gəlmir.

**main-in `oz_x.json`-u keçid anında donur.** Xəbər axınının 10 dəqiqəlik yazısı onu main-ə aparmır: struktur qaydası (b)
(sahib, 2026-11-07; [qirmizi-xetler.md](qirmizi-xetler.md) «Məlum risk») böyük və tez dəyişən faylı main-ə yazmağı qadağan edir.
Bu fayl 1,3 MB-dır, gündə ~80 dəfə dəyişir, oxucu onu oxumur. Donmuş nüsxə yalnız başlanğıcdır: budaq yoxdursa yazıcı ondan
başlayır, xəbər axını isə budaq hələ yaranmayıbsa onu oxuyur. Növbəni əl ilə düzəltmək lazım olsa `x-novbe`-də edin; main-in
nüsxəsini dəyişmək heç nəyə təsir etmir. Budağı silməyin: silinsə yazıcı onu main-in donmuş nüsxəsi ilə yenidən yaradar və
keçiddən sonra yazılan sətirlər (son 7 günün videoları, 4 günün xəbərləri) itər; yazıcı yeni videoları yenə yığar.

**Xəbər axını** (`pipeline.sh`; kod siyahısı `CODE_FILES` modulu və növbəni birlikdə kod qovluğuna köçürür):
- işin əvvəlində `copy_code` main-in donmuş nüsxəsini qoyur, yavaş dövrə başlamazdan əvvəl `pull_reel_src` budağın
  nüsxəsini gətirir (API: `contents/oz_x.json?ref=refs/heads/x-novbe`, bir-iki sorğu, hər biri ≤ 15 s) və `apply_queue` onu
  kod qovluğuna atomik qoyur (yavaş dövrə yarımçıq fayl oxumur: boş növbə boş Videolent olardı);
- yazıcının hər işi bitəndə `xyazici_loop` növbəni yenə soruşur; alınmasa dəqiqədə bir təkrarlayır. Əsas döngü yeni nüsxəni
  növbəti dövrənin əvvəlində koda qoyur (yerli fayl işi, sürətli dövrəyə şəbəkə düşmür);
- main yalnız budaq yoxdursa (HTTP 404) və bu işdə budaq heç görünməyibsə oxunur. Budaq bir dəfə oxunandan sonra
  (`$STATE/novbe-budaq`) şəbəkə xətası, vaxt bitməsi və ya budağın 404-ü son nüsxəni saxlayır, main-ə keçmir; main yazısından
  sonrakı `copy_code` main-in nüsxəsini kod qovluğuna köçürmür (növbə faylı buraxılır);
- `same_code` və son işlək kod (`.lkg`) cari kod qovluğu ilə müqayisə olunur, main ilə yox: `.lkg`-yə budağın nüsxəsi gedir.

**Kim oxuyur** (2026-11-27 axtarışı):

| Oxuyan | Necə |
|---|---|
| `x-yazici.yml`, `x_yazici.py` | budağın nüsxəsi iş qovluğuna (`ROOT/oz_x.json`), yazı yalnız budağa |
| `pipeline.sh` (`pull_reel_src`, `apply_queue`, `copy_code`, `same_code`, `.lkg`) | yuxarıda |
| `oz_x.py` (`NOVBE`: modulun yanındakı fayl), `oz_derc.py`, `updater.py` (`update_own_news`, `write_reels`) | kod qovluğundakı nüsxə, şəbəkəsiz; qısa videolar `content_policy.enforce`-dan keçib `data/reels.json`-a, xəbərlər dərc qapılarından və lentin son qapısından |
| `check_outputs.py` | yalnız `oz_x.ADLAR` cədvəli; növbə faylını oxumur |
| sayt (`assets/lent.js`), `video-dunya.cjs`, `tiktok.cjs`, `youtube.cjs`, `sosial-video.yml`, `tiktok.yml`, `youtube.yml` | növbəni oxumur: `data/reels.json` (xəbər axını yazır: dəqiqədə bir `live`-a, 10 dəqiqədə bir main-ə) |
| testlər | `tests/test_oz_x.py` main-in nüsxəsinin sətirlərini qapıdan keçirir; `tests/test_x_novbe.py` iş axınının addımlarını yerli repo ilə, axının növbə funksiyalarını saxta gh ilə işlədir; `tests/test_x_yazici.py`, `tests/lent.test.cjs` mətni yoxlayır |

Qırmızı xətt 2 dəyişmir: növbənin yeri dəyişib, qapılar yox.

**Keçid** (hansı əvvəl olsa da sətir itmir):
1. PR birləşəndə gedən köhnə yazıcı işi varsa, o son dəfə main-ə yazır. Yeni işlər eyni `concurrency` qrupunda (`x-yazici`)
   onu gözləyir: köhnə iş bitmədən yeni iş başlamır.
2. Yeni işlərin ilki budağı main-in son nüsxəsi ilə yaradır. Ondan sonra main-ə X yazısı yoxdur.
3. Yeni xəbər axını işi budaq yoxdursa main-dən, varsa budaqdan oxuyur; budaq yaranandan sonrakı ilk sorğuda keçir.
4. Birləşmə anında işləyən köhnə xəbər axını işi növbəni hələ main-dən oxuyur. Ona yeni videolar növbə dəyişənə qədər
   (ən çox ~47 dəq) gəlmir, Videolent boşalmır. Dərhal keçmək üçün birləşmədən sonra Actions → «Xəbərləri yenilə» →
   Run workflow → `rollout` ([editorial-removal.md](editorial-removal.md)).

## Hər işə salınmada

1. Kod main-dən (`git switch main`, `git pull --rebase -q`), növbə `x-novbe` budağından (`git fetch origin refs/heads/x-novbe`,
   `oz_x.json`-u oradan götürün). Yerli dəyişiklik varsa toxunmayın, dayanın və səbəbini yazın (`miss.tmp.txt`-ə heç vaxt
   toxunmayın).
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
6. Yalnız `oz_x.json`-u, yalnız `x-novbe` budağına commit edin (main-ə heç nə; sahib, 2026-11-27): mesaj
   «X xəbərləri növbəyə əlavə edildi». `git pull --rebase -q origin refs/heads/x-novbe`, sonra
   `git push -q origin HEAD:refs/heads/x-novbe` (yalnız `8ulduz/8ulduz`; `--force` yox). Push alınmasa yenidən pull + push;
   toqquşma olsa dayanın, budaqdakı nüsxənin üstünə yazmayın.
7. Yeni uyğun paylaşım yoxdursa heç nə commit etməyin.

## Videolent mənbələri: 2026-11-26 ölçüsü

Sahibin göstərişi (2026-11-26): «X qoş və yeni yanaşmaya uyğun mənbələr tap. həm sayt həmdə sos şəbəkələrdə "çox baxılan" videolar
verilməsini təmin et», «instagramda müəyyən etdiyimiz çox baxılan istiqamətlərini X ə tətbiq et. buna uyğun kifayət qədərdən artıq
sayda mənbələr tap qoş». İstiqamətlər (Instagram auditoriyasının təhlili, ən çox baxılandan): insan hekayələri; hadisə yerindən kadr
(xilasetmə, qəza, yanğın, sel, ekstremal hava, şahid videosu), xüsusən Azərbaycan və Türkiyə; məşhurlar, mədəniyyət, əyləncə (treyler
və klip yox); heyvanlar, təbiət; elm, kosmos, texnologiya; oyun yayımı olmayan idman anları. İstənməyən: liqa və yayımçı oyun klipləri,
zirvə, diplomatiya, nitq, mərc və kazino, böyüklər üçün məzmun, Azərbaycan haqqında müxalifət mənbəyi, əsasən mətn və keçid paylaşan hesab.

Həmin gün sonra (sahib: «nə heyvan nə təbiət nə kosmos», sonra «hamısına bəli»; [sosial-video.md](sosial-video.md) «Video mövzuları»):
qısa video seçicisinin (`x_yazici.py` `REELS_PROMPT`) «hadise» sinfindən «heyvanlar» və «təbiət hadisəsi» çıxdı. Heyvan faktı, təbiət
və kosmos sənədli kadrı «hadise» sayılmır, heyvan yalnız insan hadisəsinin içində olur. Önə qəzalar, ekstremal anlar (təbii fəlakətin
anı da), xarici futbol, avto yarışlar və yarış qəzaları keçir. Sonra 15 istiqamətin qalanı gəlir. Heyvan və təbiət hesabları
Videolentdə qalır. Gemini-siz ehtiyat yolu və hesab siyahısı dəyişmir. «Çox baxılan» sosial videoya isə bu qrup (`tebiet`) artıq düşmür. Ekstremal hava hesabları (Hava Forum, Colin McCarthy, Ryan Hall, Max Velocity) eyni gün `tebiet`-dən `xeber` qrupuna köçdü (sahib: «ekstremal hadisələrə də»): onların fırtına, sel, dalğa içində xilasetmə və son anda qurtulma kadrları sosial videoya düşə bilir; izahında heyvan, təbiət və ya kosmos sözü olan video yenə yalnız insan hadisəsi kimi keçir (`x.cixar`).

**Ölçü.** Yazıcının öz yolu: `https://api.fxtwitter.com/2/profile/<hesab>/statuses` — açarsız, girişsiz, bot qorumasından yan
keçmədən; sorğular arası ən azı 2 saniyə (eyni anda ən çox iki-üç proses, cəmi saniyədə 1 sorğudan az), 404 verən hesab 3 dəfə, sonra
ayrıca keçiddə 5 saniyə ara ilə yenə 3 dəfə. 2026-11-26 06:45–08:05 UTC, hər hesabın 3 səhifəyədək (60 paylaşım) lenti. Sayılan: son
72 saatın öz videoları (təkrar paylaşım və cavab deyil, müəllif hesabın özüdür). 392 hesab ölçüldü, hamısı `oz_x.py`-də yox idi.

**Hədd** (kodla uyğun):
1. son 72 saatda ≥ 3 öz video;
2. onlardan ≥ 3-ü ölçü anında `REEL_MIN_VIEWS`-u keçib (yaşına görə 8 / 15 / 40 min baxış), yəni lentə «boş» sayılmadan düşə bilir;
3. median baxış ≥ 15 000 (`REEL_MIN_VIEWS`-un 3–12 saat həddi);
4. öz paylaşımlarının ≥ 10%-i video (əsasən keçid paylaşan xəbər lenti deyil: BBC World 9%), mərc və ağır kadr nişanı (`unsafe_text`,
   «possibly_sensitive») videoların 20%-dən az;
5. videoların mətni əl ilə oxundu: treyler, tok-şou danışığı, oyun yayımı, dava və tərəfli siyasi şərh üstündürsə hesab qoşulmur.

`VIDEOLENT_ONDE`-nin həddi: median ≥ 150 000 və ≥ 5 video. Öndəki hesablar hər işdə yoxlanır və `x_yazici.VL_PER_RUN`-dan (70) yer
tutur: indi 25 hesab, mövzu başına 5 yer qalır; 26-cı hesab mövzu başına yeri 4-ə endirir və bütün mövzuların dövrü 20% yavaşlayır.
Ona görə həddi keçən dörd hesabdan (FearBuck, TMZ, Sawyer Merritt, Pop Base) yalnız TMZ və Sawyer Merritt öndədir; FearBuck-ın videoları
internet məşhurlarının dramıdır, Pop Base həddin sərhədindədir (153 min).

**Qoşulan 16 hesab** («Video / 3 gün» — ölçülən aralıq 72 saatdan qısa olanda təxmini say; «həddi keçən» — 2-ci şərt):

| Hesab | Mövzu | Video (72 saat, ölçülən) | Video / 3 gün (təxmini) | Median baxış | Həddi keçən | Video payı |
|---|---|---|---|---|---|---|
| FearedBuck | maraqli | 17 | 17 | 513 min | 17 | 65% |
| TMZ | kino, öndə | 8 | 19 | 223 min | 8 | 14% |
| SawyerMerritt | texnika, öndə | 7 | 7 | 200 min | 7 | 27% |
| BNONews | xeber | 3 | 3 | 173 min | 3 | 33% |
| PopBase | kino | 11 | 21 | 153 min | 11 | 19% |
| HavaForum | tebiet | 5 | 5 | 124 min | 5 | 23% |
| PopCrave | kino | 14 | 26 | 121 min | 14 | 25% |
| bosunatiklama | xeber | 17 | 77 | 87 min | 17 | 28% |
| darkwebhaber | xeber | 26 | 106 | 58 min | 24 | 46% |
| US_Stormwatch | tebiet | 8 | 8 | 52 min | 7 | 89% |
| RyanHallYall | tebiet | 17 | 17 | 50 min | 14 | 63% |
| ScooterCasterNY | xeber | 17 | 17 | 49 min | 11 | 94% |
| ntv | xeber | 14 | 27 | 36 min | 6 | 19% |
| TheInsiderPaper | xeber | 10 | 19 | 31 min | 4 | 19% |
| MaxVelocityWX | tebiet | 6 | 6 | 27 min | 5 | 16% |
| ABC | xeber | 26 | 122 | 23 min | 17 | 46% |

Mövzu üzrə: xeber 7 (Türkiyə: Boşuna Tıklama, DarkWeb Haber, NTV; hadisə anı: BNO News, Insider Paper, ABC News, Oliya Scootercaster),
tebiet 4 (ekstremal hava: Hava Forum, Colin McCarthy, Ryan Hall, Max Velocity; həmin gün `xeber`-ə köçdü), kino 3 (məşhurlar: TMZ, Pop Base, Pop Crave),
maraqli 1 (FearBuck), texnika 1 (Sawyer Merritt). Hesablar xəbər hesabı (`HESABLAR`) deyil: onlardan xəbər yazılmır, yalnız Videolent.

**Rəqəmlə keçib, məzmuna görə qoşulmayan 10 hesab:**

| Hesab | Video (72 saat) | Median baxış | Səbəb |
|---|---|---|---|
| DiscussingFilm | 18 | 323 min | videoların çoxu treyler və tizer (sahib: treyler yox) |
| FilmUpdates | 16 | 110 min | treyler, tizer və müsahibə |
| CultureCrave | 5 | 198 min | treyler və oyun anonsu |
| FallonTonight | 28 | 27 min | tok-şou: danışıq kadrı |
| etnow | 16 | 17 min | müsahibə və şou danışığı |
| FutbolArena | 21 | 30 min | oyun yayımından qol kadrı və müsahibə (liqa və yayımçı klipi istənmir) |
| Gabriele_Corno | 14 | 30 min | «sonra nə oldu» tipli heyvan hekayələri: uydurma və ya süni intellekt işi görünür |
| NYScanner | 6 | 20 min | küçə davası, yol qəzəbi, etiraz toqquşması |
| ViralNewsNYC | 3 | 21 min | etiraz toqquşması, tərəfli şərh, atışma xəbəri |
| DramaAlert | 11 | 22 min | internet dramı, süni intellekt və VR nümayişi |

**Rəqəmlə keçməyən 366 hesab** (mötərizədə median baxış):
- son 72 saatda öz videosu yoxdur — 149. Böyük xəbər saytlarının çoxu yalnız keçid paylaşır (Reuters, CNN, AFP, NBC News, BBC News,
  Daily Mail, New York Post, Guardian, euronews), fövqəladə xidmətlər video vermir (AFAD, İstanbul İtfaiyesi, LAFD, RNLI), «yaxşı xəbər»
  hesablarının çoxu yazmır və ya adı başqasınındır (BeAmazed, MadeMeSmile, restoringfaith_).
- median baxış 15 mindən az — 102: Türkiyə kanalları (CNN Türk 9 min, NOW Haber 13 min, Habertürk TV 8 min, A Haber 3 min, TV100 3 min,
  TGRT 1 min, Sabah 1 min), 23 Derece 9 min (həm də siyasi şərh), Onedio 7 min, Mynet 2 min; xarici kanallar (ABC World News 7 min,
  The Sun 8 min, AJ+ 7 min, Brut 0,4–14 min, Fox Weather 2 min, AccuWeather 14,7 min).
- 72 saatda 1–2 video — 35 (məs. Neuralink, The Boring Company, Cmdr Hadfield, Page Six, USCG).
- həddi keçən video 3-dən az — 11 (Brett Adcock 52 min, T.C. İçişleri 40 min, Webtekno 35 min, Meteoroloji 26 min, Emniyet 23 min).
- paylaşımların 10%-dən azı video — 1 (BBC World).
- cavab vermədi (iki keçiddə 404/500; çoxu hesab yoxdur, ad dəyişib və ya bağlanıb) — 49; lent boşdur — 19 (Ajans Muhbir, Ahbap, Haytap).

**Azərbaycan.** 34 Azərbaycan mediası və dövlət qurumu hesabı ölçüldü (APA, Report, Trend, AZƏRTAC, Oxu.Az, AzTV, CBC, FHN və s.; müxalifət
mənbəyi yoxdur). Video verən 14 hesabın median baxışı 1 mindən azdır (AzTV 452, APA 159, Oxu.Az 117), videoların çoxunda Azərbaycan mövzusu
keçir və `reel_check` onları onsuz da lentə buraxmır. X Azərbaycan hadisə kadrı üçün mənbə deyil: heç biri qoşulmadı.

**Nəticə.** İstənən 30–60 hesaba çatılmadı: X-də son 3 gündə real video verən və baxışı olan hesab azdır. Həddi aşağı salmaq
(məs. median 10 min) əsasən televiziya kanallarının danışıq kadrını gətirir, onların videoları da `REEL_MIN_VIEWS`-dan keçmir.
