# Şəkil keşi: img.8ulduz.az (Cloudflare Worker + R2)

Sahibin qərarı (2026-11-27): «Bəli, qur».

## Nə üçündür

Saytın bütün xəbər şəkilləri wsrv.nl xidməti ilə kiçildilir (`?url=…&w=…&we&output=webp&q=70`). Şəkil wsrv.nl-in keşindədirsə Bakıdan (Cloudflare-in GYD düyünü) 44–70 ms-də gəlir, yoxdursa 230–3 400 ms-də (ölçü: [qirmizi-xetler.md](qirmizi-xetler.md) §3, 2026-11-27 qeydi). Gündə ~1 100 təzə şəkil var (~13 MB), hər birinin ilk oxucusu soyuq cavabı gözləyirdi; wsrv.nl-in keşi isə pillələnir və GitHub Actions-dan isidilə bilmir.

Həll: öz domenimizdə kiçik server (Cloudflare Worker, kod: [`.github/img-worker/worker.js`](../.github/img-worker/worker.js)). Hər şəkli bir dəfə wsrv.nl-dən alır və saxlayır:

1. **Düyünün keşi** (`caches.default`) — oxucunun Cloudflare düyünü, ~20–40 ms.
2. **R2** (Cloudflare-in fayl anbarı, bucket `8ulduz-sekil`, kodda `SEKIL` bağlaması) — bütün düyünlər üçün bir nüsxə, ~60–150 ms. Obyektlər 30 gündən sonra özü silinir (lifecycle qaydası).
3. Heç birində yoxdursa **wsrv.nl**, saytın eyni sorğusu ilə (6 s vaxt həddi). Şəkil gələn kimi oxucuya gedir, R2-yə və keşə arxa planda yazılır.

Cavabda `Cache-Control: public, max-age=31536000, immutable` var (şəkli ünvan müəyyən edir, dəyişmir) və `X-Sekil` başlığı şəklin haradan gəldiyini göstərir: `edge`, `r2` və ya `wsrv`.

## Sorğu və qaydalar

Ünvan saytın wsrv.nl sorğusunun eynisidir, yalnız host fərqlidir: `https://img.8ulduz.az/?url=<şəklin ünvanı>&w=<en>&we&output=webp&q=70`.

- Parametrlərin sırası fərq etmir: eyni şəkil bir dəfə saxlanır, wsrv.nl-ə həmişə saytın öz sırası ilə gedir.
- Sui-istifadəyə qarşı yalnız saytın sorğusu qəbul olunur: bu beş parametr, saytın işlətdiyi enlər (36, 40, 48, 96, 112, 168, 360, 480, 640, 720, 960), yalnız `output=webp` və `q=70`, şəklin ünvanı yalnız `http(s)`. Qalanı `400`. Cavab yalnız raster şəkildirsə (webp, jpeg, png, gif, avif; svg yox) və 2 MB-dan kiçikdirsə saxlanır.
- wsrv.nl xəta versə və ya 6 s-də cavab verməsə, şəkil yox, xəta statusu gedir (`404`/`429` olduğu kimi, qalanı `502`, vaxt bitəndə `504`; keşlənmir). Sayt onda eyni şəkli birbaşa wsrv.nl-dən, alınmasa mənbənin özündən götürür.
- Sirr, açar, parol yoxdur. Worker-ə yalnız R2 bağlaması lazımdır.
- Testlər: `tests/img-worker.test.cjs`, `tests/sekil-isit.test.cjs`.

## Saytın tərəfi (ayrı PR, Worker canlı olandan sonra birləşir)

`assets/app.js` (`sized`), `lent.js`, `vlent.js`, hazır ilk ekran (`prerender.cjs`) və `updater.py` şablonları şəkli `img.8ulduz.az`-dan istəyir; `preconnect` də ora. Hər şəklin ardıcıllığı: `img.8ulduz.az` → eyni wsrv.nl ünvanı → orijinal. Worker bir ziyarətdə iki dəfə alınmasa (məsələn, gündəlik limit dolub — Cloudflare xətası **1027** — və ya server dayanıb), sayt həmin ziyarətin qalanında şəkilləri birbaşa wsrv.nl-dən istəyir: oxucu şəkilsiz qalmır. Paylaşma kartlarının şəkli (`og:image`) wsrv.nl-də qalır — onu robotlar çəkir, oxucunun sürətinə təsiri yoxdur. PR yalnız aşağıdakı «Yoxlama» alınandan sonra birləşir.

## İsitmə (IMG_HOST)

Yavaş dövrə (`pipeline.sh` → `sekil_isit`, hər ~5 dəqiqə) ilk ekranın təzə şəkillərini (slayd 640 və 480, «Son xəbərlər» 360, Zuğulba 168) Worker-dən bir dəfə soruşur: R2 dolur, Bakıdakı ilk oxucu şəkli wsrv.nl-dən yox, R2-dən alır. Skript: [`.github/scripts/sekil-isit.cjs`](../.github/scripts/sekil-isit.cjs). Ünvanlar app.js-in öz kodundan çıxır (saytın istədiyinin eynisi), 3 paralel sorğu, hər sorğuya 10 s, bütün işə 35 s; xəbər dövrəsi onu gözləmir (qırmızı xətt 1).

Repo dəyişəni `IMG_HOST` boşdursa isitmə heç nə etmir. Worker yoxlanandan sonra qoyulur: GitHub → repo **Settings** → **Secrets and variables** → **Actions** → **Variables** tabı → **New repository variable** → Name `IMG_HOST`, Value `img.8ulduz.az` → **Add variable**. Növbəti iş (≤ 1 saat) onu götürür. Söndürmək üçün dəyişən silinir.

## Qurulum (sahib edir, telefon və ya kompüter, ~15 dəqiqə)

Vacib: hamısı **8ulduz.az domeninin olduğu Cloudflare hesabında** edilir — `x` Worker-i olan hesab ([x-worker.md](x-worker.md) «Vəziyyət»). Başqa hesabda `img.8ulduz.az` ünvanı qoşulmur.

### 1. R2-ni açmaq (bir dəfə)

1. [dash.cloudflare.com](https://dash.cloudflare.com) → daxil olun. Telefonda sol menyu yuxarıdakı **☰** düyməsindədir.
2. Sol menyuda **Storage & databases** → **R2 object storage** → **Overview**.
3. R2 hələ açılmayıbsa səhifə abunə addımını göstərir (**Purchase R2 Plan** / checkout). Addımı tamamlayın.

**Ödəniş barədə düzünü:** R2-nin pulsuz həddi var (ayda 10 GB yer, 1 milyon yazı, 10 milyon oxu; bizim təxmini istifadə ~0,4 GB, ayda ~100 000 yazı, bir neçə milyon oxu — 0 $). Amma Cloudflare R2-ni abunə (checkout) addımı ilə açır və bu addımda hesabda **ödəniş üsulu (bank kartı və ya PayPal)** istənir — pulsuz həddə qalanda da. Cloudflare-in sənədi yalnız «Complete the checkout flow to add an R2 subscription» yazır və kartı açıq demir; amma 2025-ci ilin sentyabrındakı Cloudflare status qeydi ödəniş üsulu olmayan hesablarda R2-nin açılmaması barədə idi, yəni kart bu addımın bir hissəsidir. Kart burada qəbul olunmasa: əvvəl **Manage Account** → **Billing** → **Payment info**-da kartı əlavə edin, sonra 2-ci addıma qayıdın. Pul yalnız pulsuz hədd aşılsa çıxır; Workers-in pullu planı (ayda 5 $) ayrıdır və yalnız gündəlik 100 000 sorğu həddi aşılanda lazımdır (aşağıda «Limit və pul»).

### 2. Bucket yaratmaq

1. **R2 object storage** → **Overview** → **Create bucket**.
2. **Bucket name**: `8ulduz-sekil` (dəqiq belə, kod bu adı gözləyir).
3. **Location**: **Provide a location hint** → **Eastern Europe (EEUR)** (Bakıya ən yaxın; seçim yoxdursa **Automatic** qalsın).
4. **Default storage class**: **Standard** (pulsuz hədd yalnız Standard-a aiddir).
5. **Create bucket**. Bucket ictimai (Public) edilmir: şəkilləri yalnız Worker oxuyur.

### 3. 30 gündən sonra silmə qaydası

1. Bucket-in səhifəsi (`8ulduz-sekil`) → **Settings** tabı.
2. **Object lifecycle rules** → **Add rule**.
3. **Rule name**: `30-gun`. Qayda bütün obyektlərə aiddir (prefiks boş qalır / «Apply to all objects in bucket»).
4. **Expire objects** (obyektləri sil) seçin → **30** gün.
5. **Save changes**. Siyahıda Cloudflare-in öz qaydası (yarımçıq yükləmələr 7 gündə) da görünə bilər — ona toxunmayın.

Komanda ilə eynisi (Wrangler girişi R2 icazəsi ilə olanda): `npx wrangler r2 bucket lifecycle add 8ulduz-sekil 30-gun --expire-days 30` (prefiks soruşulsa boş buraxın), yoxlama `npx wrangler r2 bucket lifecycle list 8ulduz-sekil`.

### 4. Worker-i yükləmək — iki yoldan biri

**Yol A (asan): birdəfəlik icazə, yükləməni Claude edir.** [x-worker.md](x-worker.md)-dəki kimi: kompüterdə müvəqqəti qovluqda giriş başlanır, ekranda keçid çıxır. Siz keçidi 8ulduz.az-ın Cloudflare hesabı ilə açıb **Allow / Authorize** basırsınız (2 dəqiqə ərzində). Sonra Worker yüklənir, ünvan və R2 bağlaması `wrangler.toml`-dan özü qoşulur, icazə dərhal ləğv edilir:

```bash
cd .github/img-worker
WRANGLER_HOME=/tmp/wr XDG_CONFIG_HOME=/tmp/wr npx wrangler login --browser=false --scopes account:read user:read workers:write workers_scripts:write workers_routes:write zone:read ssl_certs:write
# çap olunan keçidi sahib açıb «Authorize» basır
WRANGLER_HOME=/tmp/wr XDG_CONFIG_HOME=/tmp/wr npx wrangler deploy
WRANGLER_HOME=/tmp/wr XDG_CONFIG_HOME=/tmp/wr npx wrangler logout && rm -rf /tmp/wr
```

Bucket (2-ci addım) deploy-dan əvvəl olmalıdır, yoxsa `wrangler deploy` «bucket not found» deyir.

**Yol B: paneldə əl ilə.**

1. Sol menyuda **Compute (Workers)** → **Workers & Pages** → sağ yuxarıda **Create**.
2. **Workers** tabı → **Start with Hello World!** → **Get started**. Ad: `img` → **Deploy**.
3. **Edit code**. Nümunə kodu tam silin, [`.github/img-worker/worker.js`](../.github/img-worker/worker.js) faylının bütün məzmununu yapışdırın (GitHub-da faylı açın → **Raw** → hamısını seçin, kopyalayın). Sağ yuxarıda **Deploy**.
4. **←** ilə Worker-in səhifəsinə qayıdın → **Settings** tabı → **Bindings** → **+ Add** → **R2 bucket** → **Variable name**: `SEKIL`, **R2 bucket**: `8ulduz-sekil` → **Add Binding** (və ya **Deploy**). Ad dəqiq `SEKIL` olmalıdır (böyük hərflə).
5. Yenə **Settings** → **Domains & Routes** → **+ Add** → **Custom domain** → `img.8ulduz.az` → **Add domain**. DNS yazısını Cloudflare özü yaradır (narıncı bulud düzgündür; `8ulduz.az`-ın GitHub yazılarına toxunmayın). Sertifikat 1–5 dəqiqəyə hazır olur.
6. Həmin siyahıda `workers.dev` və **Preview URLs** sətirlərini **Disable** edin (ünvan yalnız `img.8ulduz.az` olsun).

Kod dəyişəndə (repoda `worker.js` yenilənəndə) Yol B-nin 3-cü addımı təkrarlanır və ya Yol A yenidən.

### 5. Yoxlama

1. Brauzerdə [https://img.8ulduz.az/saglam](https://img.8ulduz.az/saglam) → `ok` yazısı görünməlidir.
2. Nümunə şəkil (saytın öz loqosu): [https://img.8ulduz.az/?url=https%3A%2F%2F8ulduz.az%2Fassets%2Ficon-512.png&w=360&we&output=webp&q=70](https://img.8ulduz.az/?url=https%3A%2F%2F8ulduz.az%2Fassets%2Ficon-512.png&w=360&we&output=webp&q=70) → loqo görünməlidir. Görünmürsə 4-cü addımın R2 bağlamasını yoxlayın.
3. Bunu bildirin — sonrası (başlıqların yoxlanması, `IMG_HOST`, saytın PR-ı) Claude-dadır.

Terminalda (Windows-da `curl` yerinə `curl.exe`):

```bash
U='https://img.8ulduz.az/?url=https%3A%2F%2F8ulduz.az%2Fassets%2Ficon-512.png&w=360&we&output=webp&q=70'
curl -sS -o /dev/null -D - "$U" | grep -iE '^(HTTP|content-type|cache-control|x-sekil)'   # 200, image/webp, immutable, X-Sekil: wsrv (ilk dəfə) və ya r2
curl -sS -o /dev/null -D - "$U" | grep -i '^x-sekil'                                      # ikinci dəfə: edge
curl -sS -o /dev/null -w '%{http_code}\n' 'https://img.8ulduz.az/?url=ftp%3A%2F%2Fa&w=360&we&output=webp&q=70'   # 400
curl -sS -o /dev/null -w '%{http_code}\n' "${U/w=360/w=361}"                              # 400 (sayt bu eni işlətmir)
```

R2-də obyektlər: **R2 object storage** → `8ulduz-sekil` → **Objects** (`v1/…` adlı fayllar). İstifadə: **Workers & Pages** → `img` → **Metrics**.

## Limit və pul

- Workers pulsuz planı: gündə 100 000 sorğu (hər şəkil bir sorğudur), sorğuya 10 ms prosessor — Worker 1 ms-dən az işlədir. Limit dolanda Cloudflare həmin gün Worker əvəzinə **1027** xətası verir (UTC gecə yarısı sıfırlanır); sayt bunu görüb şəkilləri birbaşa wsrv.nl-dən götürür, oxucu yenə şəkil görür (yalnız keşsiz, əvvəlki kimi).
- Limit tez-tez dolursa **Workers & Pages** → **Plans** → **Workers Paid** (ayda 5 $, ayda 10 milyon sorğu daxildir). Sahib bunu 2026-11-27-də qəbul edib.
- R2: yuxarıdakı pulsuz hədd daxilində. 30 günlük qayda anbarı ~0,4 GB-da saxlayır.

## Problem olsa

- `img.8ulduz.az/saglam` açılmır: Custom domain eyni hesabda deyil və ya sertifikat hələ hazır deyil (5 dəqiqə gözləyin). **DNS → Records**-da `img` yazısını yoxlayın.
- `/saglam` `ok` verir, şəkil gəlmir (`502`/`504`): wsrv.nl həmin şəkli verə bilmir — başqa şəkillə yoxlayın. Hamısı belədirsə **Workers & Pages** → `img` → **Observability** → **Live** jurnalına baxın.
- `X-Sekil` heç vaxt `r2` olmur, R2-də `Objects` boşdur: R2 bağlaması yoxdur və ya adı `SEKIL` deyil (Yol B, 4-cü addım). Worker onsuz da işləyir (yalnız düyün keşi ilə).
- Worker tamam söndürülsə və ya silinsə: sayt hər şəkli bir dəfə uğursuz soruşur, sonra wsrv.nl-ə keçir. Daimi həll: saytın PR-ı geri alınır (host yenə `wsrv.nl`).
