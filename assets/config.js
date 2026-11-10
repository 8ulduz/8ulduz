// Ziyarət statistikası (GoatCounter, kuksuz): https://8ulduz.goatcounter.com
// ga4: Google Analytics 4 ölçmə ID-si (8ulduz.az@gmail.com, «8ulduz.az» mülkü). Yüngül göndərici assets/ga.js; boş sətir söndürür.
// Boş sətir sayğacı söndürür.
// Telegram kanalı: 8ULDUZ kanalı @sekkizulduz_az-dır. Boş olanda izləmə panelində göstərilmir.
// (xəbərləri .github/scripts/social.cjs göndərir); @sekkizulduz kanal deyil, şəxsi hesabdır.
// Əlaqə e-poçtu: "Haqqımızda" səhifəsində görünür; boş olanda yalnız GitHub keçidi qalır.
// assistant: mikrofonlu «Köməkçi» düyməsi; driver: «Sürücü rejimi». Hələlik söndürülüb, true yazanda geri qayıdır
// (onda mexfilik/index.html-ə mikrofon və sürücü rejimi mətnini də qaytarın).
// follow: yalnız 8ULDUZ-un öz rəsmi hesab/kanal ünvanları. Boş sətir paneldə göstərilmir.
// sesServer: «Dinlə» Babək səs serveri (.github/ses-worker, Cloudflare): hazır tam səs, yoxdursa Azure Babək (AZURE_KEY); boş olanda köhnə yol.
// sesWorker: «Dinlə» mətn serveri (.github/ses-worker/worker.js, Cloudflare Workers); boş olanda hazır səsi olmayan xəbər qısa oxunur.
// tgBot: «Telegram-da izlə» botu (.github/scripts/izle.cjs); boş olanda düymə gizlidir.
// WhatsApp üçün /channel/ keçidi, Google News üçün izlənə bilən /publications/ səhifəsi yazılır.
window.SITE_CONFIG = { sesServer: "https://dinle.8ulduz-az.workers.dev/ses", sesWorker: "https://dinle.8ulduz-az.workers.dev/", tgBot: "sekkizulduz_xeber_bot", goatcounter: "8ulduz", ga4: "G-NHSDLY61CD", telegram: "https://t.me/sekkizulduz_az", contact: "8ulduz.az@gmail.com", assistant: false, driver: false,
  follow: { whatsapp: "", facebook: "https://www.facebook.com/profile.php?id=61596264031461", instagram: "https://www.instagram.com/8ulduz.az/", linkedin: "https://www.linkedin.com/in/s%C9%99kkiz-ulduz-605537449/", googleNews: "", x: "https://x.com/8ulduz" }
};
