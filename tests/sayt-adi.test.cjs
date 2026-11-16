// Sayt adı axtarışda (2026-11-15, sahib: «düzəlt, hətta səkkiz ulduz və səkkizulduz da əlavə et»).
// Search Console-da sayta gələn yeganə sorğu «8 ulduz» idi, Google isə «namaz vaxtları 8ulduz»
// sorğusunda «8ulduz» sözünü tanımırdı. Baş səhifənin WebSite nişanı adın yazılışlarını Google-a deyir.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("fs"), path = require("path");

const HTML = fs.readFileSync(path.join(__dirname, "..", "index.html"), "utf8");

test("sayt adı: WebSite və təşkilat nişanı adın bütün yazılışlarını verir", () => {
  const m = HTML.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/);
  assert.ok(m, "baş səhifədə ld+json bloku var");
  const graph = JSON.parse(m[1])["@graph"];
  for (const type of ["WebSite", "NewsMediaOrganization"]) {
    const node = graph.find(n => n["@type"] === type);
    assert.ok(node, `${type} nişanı var`);
    assert.equal(node.name, "8ulduz");
    assert.equal(node.url, "https://8ulduz.az/");
    for (const alt of ["8 Ulduz", "Səkkiz Ulduz", "Səkkizulduz", "8ulduz.az"])
      assert.ok(node.alternateName.includes(alt), `${type}: «${alt}» yazılışı`);
  }
});
