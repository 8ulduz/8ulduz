// Mənbədən geri qayıdış (sahib, 2026-11-07: «mənbələrə get gəl də gözqırpımında olsun»): Facebook/WhatsApp daxili brauzeri
// saytı yenidən açanda oxucu qaldığı yerə qayıdır; paylaşılan keçid xəbəri heç bir yükləməni gözləmədən göstərir.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path");
const js = fs.readFileSync(path.join(__dirname, "..", "assets/app.js"), "utf8").replace(/\r\n/g, "\n");
const html = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");

test("qayıdış: the scroll position is saved on leaving and restored only on a back navigation", () => {
  assert.ok(js.includes(`addEventListener("pagehide", () => { try { sessionStorage.setItem("8y:" + location.hash, scrollY | 0); } catch {} });`));
  assert.ok(/function backY\(\) \{[\s\S]*?type === "back_forward" && scrollY < 50\) requestAnimationFrame\(\(\) => scrollTo\(0, y\)\)/.test(js));
  assert.ok(js.includes("    if (!partial) backY();\n"), "tam lent göstəriləndən sonra");
});

test("paylaşılan keçid: the row handed over by the share page opens the story without waiting for any download", () => {
  assert.ok(js.includes(`sessionStorage.getItem("x:" + r0.id)`) && js.includes("!policyViolation(w)"), "açılışda sətir götürülür, qaydadan keçir");
  assert.ok(js.includes("if (S.data || S.sharedStory?.id === id ||"), "sətir varsa paylaşma siyahısı yüklənmir");
  assert.ok(js.includes(`if (r0.name === "article") { if (S.sharedStory) setTimeout(renderView); else loadShared(r0.id);`), "xəbər lenti gözləmədən dərhal çəkilir");
  assert.ok(html.includes(`got = !!(art && sessionStorage.getItem("x:" + art[1]))`) && html.includes("if (got) files = []; else if (art) files.unshift("), "erkən sorğu da edilmir");
});
