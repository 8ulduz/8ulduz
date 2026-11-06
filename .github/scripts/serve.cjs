// Sürət ölçüsü üçün yerli statik server, GitHub Pages kimi: gzip, max-age=600. node .github/scripts/serve.cjs [kök] [port]
"use strict";
const http = require("http"), fs = require("fs"), path = require("path"), zlib = require("zlib");
const root = path.resolve(process.argv[2] || "."), port = Number(process.argv[3] || 8080);
const types = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".png": "image/png", ".webp": "image/webp", ".xml": "application/xml", ".webmanifest": "application/manifest+json", ".svg": "image/svg+xml", ".txt": "text/plain" };
http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split("?")[0]);
  if (p.endsWith("/")) p += "index.html";
  const f = path.join(root, path.normalize(p));
  if (!f.startsWith(root)) { res.writeHead(403); res.end(); return; }
  fs.readFile(f, (e, d) => {
    if (e) { res.writeHead(404); res.end("404"); return; }
    const ext = path.extname(f), h = { "content-type": types[ext] || "application/octet-stream", "cache-control": "max-age=600" };
    if (/\.(html|js|css|json|xml|svg|webmanifest|txt)$/.test(ext)) d = Buffer.from(d.toString("utf8").replace(/\r\n/g, "\n")); // Windows nüsxəsi: Pages LF verir (CSP hash)
    if (/\.(html|js|css|json|xml|svg|webmanifest|txt)$/.test(ext) && /gzip/.test(req.headers["accept-encoding"] || "")) { h["content-encoding"] = "gzip"; d = zlib.gzipSync(d); }
    res.writeHead(200, h); res.end(d);
  });
}).listen(port, () => console.log(`listening ${port}`));
