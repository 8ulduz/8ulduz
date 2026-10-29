// Sayt ilə Android tətbiqinin bir-birini tanıması üçün faylların uyğunluğu (Digital Asset Links).
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const root = path.join(__dirname, "..");
const read = (p) => fs.readFileSync(path.join(root, p), "utf8");
const gradle = read("android/app/build.gradle");
const appId = gradle.match(/applicationId "([^"]+)"/)[1];

test("assetlinks.json tətbiqin paketini və düzgün formatlı barmaq izlərini göstərir", () => {
  const links = JSON.parse(read(".well-known/assetlinks.json"));
  const app = links.find((l) => l.target.namespace === "android_app");
  assert.ok(app, "android_app hədəfi yoxdur");
  assert.deepStrictEqual(app.relation, ["delegate_permission/common.handle_all_urls"]);
  assert.strictEqual(app.target.package_name, appId);
  assert.ok(app.target.sha256_cert_fingerprints.length > 0);
  for (const fp of app.target.sha256_cert_fingerprints) assert.match(fp, /^([0-9A-F]{2}:){31}[0-9A-F]{2}$/);
});

test(".nojekyll var (yoxsa GitHub Pages .well-known qovluğunu dərc etmir)", () => {
  assert.ok(fs.existsSync(path.join(root, ".nojekyll")));
});

test("tətbiqin açdığı ünvanlar saytın öz domenindədir", () => {
  const strings = read("android/app/src/main/res/values/strings.xml");
  const host = strings.match(/name="hostName"[^>]*>([^<]+)</)[1];
  assert.strictEqual(host, read("CNAME").trim());
  for (const url of [...strings.matchAll(/https:\/\/[^<"\\\s]+/g)].map((m) => m[0])) assert.strictEqual(new URL(url).host, host, url);
  for (const url of [...read("android/app/src/main/res/xml/shortcuts.xml").matchAll(/android:data="([^"]+)"/g)].map((m) => m[1])) {
    assert.strictEqual(new URL(url).host, host, url);
  }
});

test("veb manifest Play tətbiqinə istinad edir", () => {
  const m = JSON.parse(read("manifest.webmanifest"));
  assert.ok(m.related_applications.some((a) => a.platform === "play" && a.id === appId));
  assert.strictEqual(m.prefer_related_applications, false);
});

test("Android resurslarının adları etibarlıdır", () => {
  const res = path.join(root, "android/app/src/main/res");
  for (const dir of fs.readdirSync(res)) {
    for (const f of fs.readdirSync(path.join(res, dir))) assert.match(f, /^[a-z][a-z0-9_]*\.(png|xml)$/, `${dir}/${f}`);
  }
});
