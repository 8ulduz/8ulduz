// Qırmızı xətt 1: sayt yenilənir. 2026-11-05 gecə GitHub-da bir Pages yayımı «davam edir» vəziyyətində dondu,
// sonrakı bütün yayımlar «əvvəlcə onu ləğv edin» xətası ilə rədd olundu, sayt 40 dəqiqə köhnə qaldı.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const wd = fs.readFileSync(path.join(__dirname, '../.github/workflows/watchdog.yml'), 'utf8');

test('watchdog cancels a Pages deployment stuck «in progress» for over 10 minutes and asks for a new build', () => {
  assert.ok(/^\s+pages: write$/m.test(wd), 'ləğv etmək üçün icazə');
  assert.ok(wd.includes('deployments?environment=github-pages') && wd.includes('(now - (.created_at | fromdateiso8601)) > 600'), 'yalnız 10 dəqiqədən köhnə yayımlar');
  assert.ok(wd.includes('*queued*|*progress*|syncing_files|finished_file_sync|updating_pages)'), 'yalnız davam edən vəziyyət (bitmişə toxunmur)');
  assert.ok(wd.includes('gh api -X POST "repos/$GH_REPO/pages/deployments/$sha/cancel"') && wd.includes('gh api -X POST "repos/$GH_REPO/pages/builds"'), 'ləğv və yeni yığım');
  const step = wd.slice(wd.indexOf('İlişmiş Pages yayımı'), wd.indexOf('site="https://'));
  assert.ok(step.length > 0 && step.length < 1200, 'təzəlik yoxlamasından əvvəl, hər dövrədə');
});
