# Paylaşma keçidi serveri: x.8ulduz.az

Sahibin qeydi (2026-11-08): «Facebook-da paylaşanda başlıq çıxmır, xəbərə qayıtmır; tam düzəlt, WhatsApp kimi; tel, komp, planşetdə yoxla».

## Problem nə idi

Facebook, WhatsApp, Telegram və X önizləməni (başlıq, şəkil) keçidin `og:` etiketlərindən oxuyur. Saytda hər xəbərin belə səhifəsi var: `https://8ulduz.az/x/<nömrə>` (`updater.py`, `write_share_pages`). Amma bu səhifələr `main`-ə 10 dəqiqədən bir yazılır, Pages də bir neçə dəqiqə sonra yayımlayır. Xəbər saytda görünən kimi paylaşılanda (ən çox paylaşılan an) səhifə hələ yoxdur: Facebook saytın ümumi kartını və ya boş kart göstərirdi, keçid də xəbərə deyil baş səhifəyə düşürdü. Telefonun sistem paylaşma pəncərəsi isə `#/xeber/` keçidini göndərirdi — hash serverə getmir, önizləmə heç vaxt olmur.

## Həll

Bütün paylaşma keçidləri bir ünvana gedir: `https://x.8ulduz.az/<nömrə>?h=<il-ay-gün-saat>`. Orada Cloudflare Worker (kiçik server, kod: [`.github/x-worker/worker.js`](../.github/x-worker/worker.js)) hər sorğunu həmin anda cavablandırır:

1. `https://8ulduz.az/x/<nömrə>` səhifəsi varsa — onu olduğu kimi verir (og etiketləri hazırdır).
2. Yoxdursa xəbərin sətrini lentdən tapır: əvvəl dəqiqəlik kanal (`live` budağı, `m/<dəqiqə>/latest.json`, cari və əvvəlki 3 dəqiqə — `sw.js` ilə eyni qayda), sonra saytın `data/latest.json`, `data/first.json`, `data/news.json`. Tapanda `updater.py`-dakı səhifənin eynisini qurur: `og:title`, `og:description`, `og:image` (wsrv.nl proksisindən 1200×630, WhatsApp limiti üçün), xəbərin sətri `sessionStorage`-a və dərhal saytın `#/xeber/<nömrə>?b=&h=` ünvanına keçid. Botlara (facebookexternalhit, WhatsApp, Twitterbot, TelegramBot) 200 və og etiketləri gedir, oxucu isə saytda xəbəri gözləmədən görür.
3. Heç yerdə tapılmasa (25 saatdan köhnə xəbər, və ya server xəta versə) 302 ilə `https://8ulduz.az/#/xeber/<nömrə>?h=…`: sayt xəbəri arxiv budağından açır. Keçid heç vaxt ölmür.

Tapılan səhifə Cloudflare keşində 10 dəqiqə qalır (bot bir keçidi bir neçə dəfə soruşur). Qırmızı xətt 2: Worker yalnız lentdə olan sətirləri verir (onlar `content_policy.enforce`-dan keçib), redaksiyanın çıxardığı xəbər (`removed`) verilmir, heç nə uydurulmur. Sirr, açar, parol yoxdur: Worker yalnız açıq faylları oxuyur. Testlər: `tests/x-worker.test.cjs`.

Saytın tərəfi (ayrı PR, Worker canlı olandan sonra birləşir): `assets/app.js`-də `shareUrl` hər 16 rəqəmli xəbərə `https://x.8ulduz.az/<nömrə>?h=…` verir — dəqiqəlik kanaldan gələn təzə xəbərə də, telefonun sistem pəncərəsinə də. `updater.py`-ın `/x/` səhifələri qalır: Worker-in birinci mənbəyidir.

## Vəziyyət (2026-11-08): qurulub

Worker **x** Cloudflare-in **V.z.muradov@gmail.com** hesabındadır (8ulduz.az zonası oradadır, hesab ID `0e1ad7c5…`); `x.8ulduz.az` custom domain kimi bağlıdır, `workers.dev` ünvanı söndürülüb (`wrangler.toml`). Yükləmə `npx wrangler deploy` ilə oldu: sahib brauzerdə Wrangler-ə birdəfəlik icazə verdi (yalnız `account:read user:read workers:write workers_scripts:write workers_routes:write zone:read ssl_certs:write`), iş bitən kimi `npx wrangler logout` ilə icazə ləğv edildi; bu kompüterdə həmin hesabın açarı qalmır.

Diqqət: bu kompüterdəki daimi wrangler girişi **8ulduz.az@gmail.com** hesabınadır («Dinlə» serveri, `.github/ses-worker`). O hesabda 8ulduz.az zonası yoxdur: `x` ora yüklənsə `x.8ulduz.az` bağlanmır. Panel yolu da eyni hesab məsələsinə baxır: domen hansı hesabdadırsa, Worker orada.

Kod dəyişəndə (`worker.js`) iki yol var: sahib Cloudflare panelində **Edit code** ilə yapışdırır (aşağıda 4-cü addım), ya da yenidən birdəfəlik giriş (müvəqqəti qovluqda, daimi girişə toxunmadan):

```bash
cd .github/x-worker
WRANGLER_HOME=/tmp/wr XDG_CONFIG_HOME=/tmp/wr npx wrangler login --browser=false --scopes account:read user:read workers:write workers_scripts:write workers_routes:write zone:read ssl_certs:write
# çap olunan keçidi sahib V.z.muradov hesabı ilə açıb «Authorize» basır (2 dəqiqə ərzində)
WRANGLER_HOME=/tmp/wr XDG_CONFIG_HOME=/tmp/wr npx wrangler deploy
WRANGLER_HOME=/tmp/wr XDG_CONFIG_HOME=/tmp/wr npx wrangler logout && rm -rf /tmp/wr
```

2026-11-08 axşam (canlı jurnal: Workers & Pages → x → Observability → Live): sahibin telefonu yeni keçidi göndərir, Facebook robotu (`facebookexternalhit`, Meta şəbəkəsi, «Page Preview») hər keçidə 3 dəfə gəlir və 200 alır, amma kartda yenə baş səhifə çıxırdı: robot səhifədəki `<meta http-equiv="refresh">`-i izləyib `8ulduz.az/#/…` → baş səhifənin og etiketlərini götürür (WhatsApp və Telegram izləmir). Düzəliş: səhifədə meta refresh yoxdur, `canonical` səhifənin özüdür; köhnə statik səhifələrdən Worker refresh-i özü atır. Facebook bir keçidin kartını keşləyir: yoxlamanı həmin gün paylaşılmamış (təzə) xəbərlə edin və ya Sharing Debugger-də **Scrape Again** basın.

2026-11-08 yoxlaması: `/saglam` → `ok`; Facebook botu kimi təzə xəbərdə `og:title`, `og:description`, `og:image` (wsrv.nl) və `og:url` (`x.8ulduz.az`) gəldi, 0,75 s; olmayan nömrə `302 → https://8ulduz.az/#/xeber/<nömrə>?h=…`.

## Qurulum (sahib edir, 5 dəqiqə)

Vacib: Worker **8ulduz.az domeninin olduğu Cloudflare hesabında** yaradılmalıdır (2026-11-03-də DNS-i köçürdüyünüz hesab, `sage`/`gemma.ns.cloudflare.com`). Başqa hesabda `x.8ulduz.az` ünvanı qoşulmur.

1. [dash.cloudflare.com](https://dash.cloudflare.com) → daxil olun.
2. Sol menyuda **Compute (Workers)** → **Workers & Pages**. Sağ yuxarıda **Create** düyməsi.
3. **Workers** tabında **Start with Hello World!** → **Get started**. Ad yerinə `x` yazın → **Deploy**.
4. Açılan səhifədə **Edit code** düyməsi. Redaktorda nümunə kodu tam silin, [`.github/x-worker/worker.js`](../.github/x-worker/worker.js) faylının bütün məzmununu yapışdırın (GitHub-da faylı açın → **Raw** → hamısını seçin, kopyalayın). Sağ yuxarıda **Deploy** → **Save and deploy**.
5. Sol yuxarıdakı **←** ilə Worker-in səhifəsinə qayıdın → **Settings** tabı → **Domains & Routes** → **+ Add** → **Custom domain** → `x.8ulduz.az` yazın → **Add domain**. DNS yazısını Cloudflare özü yaradır (bu alt domen üçün narıncı bulud düzgündür; `8ulduz.az`-ın GitHub yazıları boz qalır, onlara toxunmayın). Sertifikat 1–5 dəqiqəyə hazır olur.
6. Brauzerdə [https://x.8ulduz.az/saglam](https://x.8ulduz.az/saglam) açın → `ok` yazısı görünməlidir.

Alternativ (kompüterdən, Node ilə): `.github/x-worker` qovluğunda `npx wrangler login`, sonra `npx wrangler deploy` — `wrangler.toml` ünvanı özü qoşur.

Kod dəyişəndə (repoda `worker.js` yenilənəndə) 4-cü addım təkrarlanır: **Edit code** → köhnəni sil → yenisini yapışdır → **Deploy**.

## Yoxlama (deploy-dan sonra)

Xəbər nömrəsi: saytda istənilən xəbərdə **Paylaş** → **Keçidi kopyala**; keçiddəki 16 simvollu nömrə (`0`–`9`, `a`–`f`). Ya da terminalda:

```bash
curl -s https://8ulduz.az/data/latest.json | grep -o '"id":"[0-9a-f]*"' | head -3
```

Windows-da `curl` yerinə `curl.exe` yazın.

1. Facebook botu kimi — başlıq və şəkil gəlməlidir, status 200:

```bash
curl -sS -A "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)" "https://x.8ulduz.az/<nömrə>?h=26110812" | grep -o '<meta property="og:[a-z:_]*" content="[^"]*"'
```

Gözlənən: `og:title` xəbərin başlığı, `og:image` `wsrv.nl` (və ya şəkilsiz xəbərdə `og-default.png`), `og:url` `https://x.8ulduz.az/<nömrə>`.

2. Təzə xəbər (saytda yenicə çıxan, `/x/` səhifəsi hələ yoxdur): «Son xəbərlər»dən ən yenisinin nömrəsi ilə eyni əmr. Başlıq yenə gəlməlidir — bu, əsas məqsəddir.

3. Olmayan nömrə sayta yönəlməlidir (302):

```bash
curl -sS -o /dev/null -w "%{http_code} %{redirect_url}\n" "https://x.8ulduz.az/0000000000000000?h=26110812"
```

Gözlənən: `302 https://8ulduz.az/#/xeber/0000000000000000?h=26110812`.

4. Facebook-un öz yoxlayıcısı: [developers.facebook.com/tools/debug](https://developers.facebook.com/tools/debug/) → keçidi yapışdırın → **Debug**. Köhnə kart görünsə **Scrape Again**. Başlıq, təsvir və şəkil görünməlidir. Telegram-da köhnə önizləməni təzələmək üçün keçidi [@WebpageBot](https://t.me/WebpageBot)-a göndərin. WhatsApp-da keçidi özünüzə göndərin: kart 1–2 saniyəyə çıxır.

5. Oxucu kimi: keçidi brauzerdə açın (telefon, planşet, kompüter) — sayt həmin xəbərin səhifəsini açmalıdır, ünvan `8ulduz.az/#/xeber/<nömrə>…` olur, geri düyməsi işləyir.

Yoxlama alınandan sonra saytın PR-ı (`shareUrl` → `x.8ulduz.az`) birləşdirilir. Ona qədər sayt köhnə keçidləri verir, heç nə pozulmur.

## Limit və pul

Cloudflare Workers pulsuz planı: gündə 100 000 sorğu, sorğuya 10 ms prosessor vaxtı. Bir paylaşma keçidinə bot 1–3 sorğu edir, Worker özü lentə ən çox 7 sorğu göndərir (keşdə olanda 0). Saytın paylaşma sayı bundan qat-qat azdır; limit dolsa Cloudflare həmin gün «1027» xətası verir və növbəti gün sıfırlanır. İstifadəni panel göstərir: **Workers & Pages** → `x` → **Metrics**. Pullu plan lazım deyil.

## Problem olsa

- `x.8ulduz.az/saglam` açılmır: Custom domain eyni hesabda deyil və ya sertifikat hələ hazır deyil (5 dəqiqə gözləyin). DNS-də `x` yazısının olduğunu **DNS → Records**-da yoxlayın.
- Facebook köhnə kartı göstərir: Sharing Debugger-də **Scrape Again**.
- Başlıq gəlir, şəkil gəlmir: mənbənin şəkli böyükdür və ya silinib; wsrv.nl saytın şəklini qoyur. Facebook ilk dəfə şəkli gec yükləyə bilər — ikinci **Scrape Again**.
- Worker tamam dayansa (silinsə): keçidlər 522/1016 xətası verər. Bu halda saytın PR-ındakı `shareUrl` geri alınır (`8ulduz.az/x/`), köhnə yol işləyir.
