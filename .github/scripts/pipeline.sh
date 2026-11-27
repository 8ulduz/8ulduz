#!/usr/bin/env bash
# QIRMIZI XƏTT 1 (docs/qirmizi-xetler.md): xəbər ən geci 60 saniyədən bir yenilənir və axın dayanmır.
#
# Üç axın, biri digərini gözləmir:
#   sürətli  hər CYCLE saniyə: lentlər, xəbər seçimi, status -> live budağı (tarixçəsiz, repo şişmir)
#   yavaş    arxa planda: məzənnə, şəkil, video, idman, bölmə arxivi, SEO səhifələri
#   main     hər MAIN_EVERY saniyə: tam lent və SEO -> GitHub Pages
#   sosial   hər SOCIAL_EVERY saniyə: rəsmi hesabların YouTube yazıları (social.json) -> növbəti dəqiqənin live faylı
#
# Bir iş bitməzdən əvvəl növbətisini başladır və onu görəndən sonra çıxır, ona görə növbə dəyişəndə boşluq olmur.
#
# raw.githubusercontent.com budaq adı ilə verilən faylı sorğu parametrindən asılı olmayaraq 5 dəqiqə keşləyir, yeni yolu
# isə dərhal verir (2026-10-30 ölçülüb). Ona görə hər dəqiqənin ayrı yolu var: m/<dəqiqə>/status.json. Yaranmamış yola
# sorğu 404-ü 55 saniyə keşə salır, ona görə dövrə dəqiqənin 5-ci saniyəsində başlayır və yazı dəqiqə içində bitir,
# sw.js isə dəqiqəni yalnız 45 saniyə keçəndən sonra istəyir (dövrə ölçüsü 10-37 saniyə).
set -uo pipefail

CYCLE="${CYCLE:-60}"
# Qəsdən 40-dan böyükdür: yavaş gündə gec gələn dövrə növbəti dəqiqədə görünür, kəsilən dövrə isə heç görünmür.
# Adi dövrəni qısa saxlayan updater.py-dakı FAST_BUDGET_S və PR-dakı 35 saniyəlik yoxlamadır.
FAST_LIMIT="${FAST_LIMIT:-50}"
SLOW_LIMIT="${SLOW_LIMIT:-280}"
SLOW_EVERY="${SLOW_EVERY:-240}"
LINKS_LIMIT="${LINKS_LIMIT:-55}"
LINKS_EVERY="${LINKS_EVERY:-30}"
OG_LIMIT="${OG_LIMIT:-25}"   # təzə xəbərin şəkli (--og): link yoxlamasından sonra, eyni 30 saniyəlik döngüdə
SOCIAL_LIMIT="${SOCIAL_LIMIT:-50}"
SOCIAL_EVERY="${SOCIAL_EVERY:-60}"
MAIN_EVERY="${MAIN_EVERY:-600}"
HANDOFF_AFTER="${HANDOFF_AFTER:-2820}"   # 47 dəq: növbəti işi başlat
MAX_RUN="${MAX_RUN:-3600}"               # 60 dəq: növbəti iş görünməsə də çıx (timeout-minutes-dən əvvəl)
STUCK_AFTER="${STUCK_AFTER:-240}"        # dövrə bu qədər irəliləməsə iş özünü dayandırır, növbətisi başlayır
PUSH_FAILS_MAX="${PUSH_FAILS_MAX:-15}"   # GitHub qısa kəsilsə iş gözləyir; bu qədər dövrə ardıcıl alınmasa yeni iş
BRANCH="${BRANCH:-main}"
LIVE_BRANCH="${LIVE_BRANCH:-live}"
# X növbəsi (oz_x.json) main-də deyil, bu budaqdadır (sahib 2026-11-27; docs/x-yazici.md «Növbə budağı»). Yazıcı yalnız oraya yazır.
NOVBE_BRANCH="${NOVBE_BRANCH:-x-novbe}"
RUN_ID="${GITHUB_RUN_ID:-0}"
GH="${GH:-gh}"
REPO_DIR="${REPO_DIR:-$PWD}"
PY="${PY:-$(command -v python || command -v python3)}"

WORK="$(mktemp -d)"      # məlumat: updater yalnız buraya yazır
CUR="$(mktemp -d)"       # cari kod
LKG="$REPO_DIR/.lkg"     # son uğurla işləmiş kod (actions/cache)
GOOD="$(mktemp -d)"      # son sağlam məlumat nüsxəsi
STATE="$(mktemp -d)"
NOVBE="$STATE/novbe"     # X növbəsinin son oxunan nüsxəsi (pull_reel_src); kod qovluğuna apply_queue qoyur
SLOTS="$STATE/m"         # son dəqiqələrin faylları
KEEP_SLOTS=5
export LATEST_LANG_FILES=1   # updater.py status.json-a "langs" yazır: bu pipeline dil fayllarını (latest.az.json və s.) live-ə göndərir
export SHARE_PAGES=1         # updater.py hər xəbərə x/<id>.html paylaşma səhifəsi (og etiketləri) yazır və lentin başlığına "sharePages" qoyur; publish_main x/ qovluğunu main-ə köçürür
export NEWS_LANG_FILES=1     # updater.py tam lenti dil üzrə yazır (news.json = azərbaycanca + xarici idman, news.en/ru/tr.json = o dil) və status.json-a "newsLangs" qoyur; hamısı main-ə gedir (publish_main data/-nı olduğu kimi köçürür)
export SOCIAL_LOOP=1         # updater.py rəsmi hesabların yazılarını yavaş dövrədə yığmır (social_loop --social hər dəqiqə), status.json-a "social" möhürü qoyur; push_live social.json-u da göndərir
export OZ_DERC=1             # updater.py 8ulduz-un öz xəbərlərini dərc edir (sahib 2026-11-12: «Bəli, yandır»): yavaş dövrədə dərc dövrəsi, lentə yalnız səhifəsi saytda olan sətirlər (own_rows_live). Söndürmək üçün bu sətir silinir: növbəti dövrədə öz sətirlər lentdən çıxır
CODE_FILES="updater.py reader_content.py content_policy.py assets/content-policy.js .github/scripts/check_outputs.py"
# Öz xəbərlərin dərc hissəsi və modulları (sahib 2026-11-12: «Sayta qoşmağa başla»): kod qovluğuna köçürülür ki, updater.py-ın
# yavaş addımı (update_own_news) onları oradan import edə bilsin; addım yalnız yuxarıdakı açarla işləyir.
# Köhnə .lkg nüsxəsində bu fayllar olmaya bilər: copy_code olmayan faylı buraxır, same_code «fərqli» deyir.
CODE_FILES="$CODE_FILES oz_derc.py oz_xeber.py oz_bazar.py oz_futbol_az.py oz_futbol_dunya.py oz_gundelik.py oz_hava.py oz_icmal.py oz_idman2.py oz_maliyye.py oz_medeniyyet.py oz_sema.py oz_teqvim.py oz_yer_kosmos.py oz_tixac.py oz_dunya.py oz_dunya.json oz_x.py oz_x.json"
SLOW_PID=""
PUBLISH_PID=""
WATCH_PID=""
LINKS_PID=""
SOCIAL_PID=""
EDITORIAL_PID=""
ROLLOUT_PID=""
TIXAC_PID=""
XYAZICI_PID=""
VIDEO_PID=""
ARXIV_PID=""

cleanup() {
  [ -n "$WATCH_PID" ] && kill "$WATCH_PID" 2>/dev/null
  [ -n "$SLOW_PID" ] && kill "$SLOW_PID" 2>/dev/null
  [ -n "$LINKS_PID" ] && kill "$LINKS_PID" 2>/dev/null
  [ -n "$SOCIAL_PID" ] && kill "$SOCIAL_PID" 2>/dev/null
  [ -n "$EDITORIAL_PID" ] && kill "$EDITORIAL_PID" 2>/dev/null
  [ -n "$ROLLOUT_PID" ] && kill "$ROLLOUT_PID" 2>/dev/null
  [ -n "$TIXAC_PID" ] && kill "$TIXAC_PID" 2>/dev/null
  [ -n "$XYAZICI_PID" ] && kill "$XYAZICI_PID" 2>/dev/null
  [ -n "$VIDEO_PID" ] && kill "$VIDEO_PID" 2>/dev/null
  [ -n "$ARXIV_PID" ] && kill "$ARXIV_PID" 2>/dev/null
  [ -n "$PUBLISH_PID" ] && wait "$PUBLISH_PID" 2>/dev/null
  return 0
}
trap cleanup EXIT

# Şəbəkə asılsa gh sonsuz gözləyə bilər: axın onu gözləməməlidir.
gh_t() { timeout -k 5 15 "$GH" "$@"; }
# Xəbər lentini oxuyan proses repo açarını görməsin.
py_t() { env -u GH_TOKEN -u GITHUB_TOKEN timeout -k 5 "$@"; }

copy_code() { # $1 mənbə, $2 hədəf, $3 köçürülməyən fayl (boşdursa hamısı köçür)
  local f
  for f in $CODE_FILES; do
    [ -n "${3:-}" ] && [ "$f" = "$3" ] && continue
    [ -f "$1/$f" ] || continue
    mkdir -p "$2/$(dirname "$f")"
    cp "$1/$f" "$2/$f"
  done
}

same_code() { # $1, $2: eyni koddur?
  local f
  for f in $CODE_FILES; do
    cmp -s "$1/$f" "$2/$f" || return 1
  done
}

# Daha gənc iş artıq işləyirsə (bu cron və ya dispatch-dir) və növbə dəyişmə vaxtı deyilsə, çıxırıq.
another_run_in_charge() {
  local now youngest
  now="$(date +%s)"
  youngest="$(gh_t run list --workflow update.yml --branch "$BRANCH" --status in_progress --limit 20 --json databaseId,createdAt \
    --jq "[.[] | select(.databaseId != ${RUN_ID}) | .createdAt | fromdateiso8601] | max // 0" 2>/dev/null || echo 0)"
  [ -n "$youngest" ] && [ "$youngest" != "0" ] && [ $((now - youngest)) -lt $((HANDOFF_AFTER - 180)) ]
}

newer_run_started() {
  local me count
  me="$(gh_t run view "$RUN_ID" --json createdAt --jq '.createdAt | fromdateiso8601' 2>/dev/null || echo 0)"
  # Öz vaxtımızı bilmiriksə «yeni iş var» deyə bilmərik: işləməyə davam.
  [ -n "$me" ] && [ "$me" != "0" ] || return 1
  count="$(gh_t run list --workflow update.yml --branch "$BRANCH" --status in_progress --limit 20 --json databaseId,createdAt \
    --jq "[.[] | select(.databaseId != ${RUN_ID} and (.createdAt | fromdateiso8601) > ${me:-0})] | length" 2>/dev/null || echo 0)"
  [ "${count:-0}" != "0" ]
}

# Cari kod işləməsə son işlək kodla davam edir. Cari kod updater və yoxlayıcı işləyəndən sonra yeni «işlək» olur (promote_code).
run_py() { # $1 rejim, $2 limit
  [ "$1" = "--fast" ] && CUR_RAN=0
  if UPDATER_ROOT="$WORK" py_t "$2" "$PY" "$CUR/updater.py" "$1"; then
    [ "$1" = "--fast" ] && CUR_RAN=1
    return 0
  fi
  if [ ! -f "$LKG/updater.py" ] || same_code "$CUR" "$LKG"; then
    return 1
  fi
  echo "::warning::updater.py ($1) xəta verdi — son işlək versiya ilə cəhd edilir"
  UPDATER_ROOT="$WORK" py_t "$2" "$PY" "$LKG/updater.py" "$1"
}

# Son işlək yoxlayıcı: cari yoxlayıcı sınıq olanda.
check_lkg() { # $1 qovluq
  echo "::warning::check_outputs.py işləmədi — son işlək yoxlayıcıya keçilir" >&2
  [ -f "$LKG/.github/scripts/check_outputs.py" ] || return 1
  UPDATER_ROOT="$WORK" py_t 20 "$PY" "$LKG/.github/scripts/check_outputs.py" "$1"
}

# Zədəli fayl son sağlam nüsxə ilə əvəz olunur; qaydanı pozan xəbər fayldan çıxarılır.
# Heç bir yoxlayıcı işləməsə axın dayanmır, updater.py-ın öz qapısı qalır.
guard_outputs() {
  local f bad
  CUR_CHECKED=0
  if bad="$(UPDATER_ROOT="$WORK" py_t 20 "$PY" "$CUR/.github/scripts/check_outputs.py" "$WORK")"; then
    CUR_CHECKED=1
  elif ! bad="$(check_lkg "$WORK")"; then
    # Yoxlanmamış məlumat «sağlam nüsxə» olmur.
    echo "::error::Çıxış faylları yoxlanmadı, son sağlam nüsxə yenilənmir"
    return 0
  fi
  for f in $bad; do
    echo "::warning::$f zədəlidir — son sağlam nüsxə saxlanılır"
    if [ -f "$GOOD/$f" ]; then cp "$GOOD/$f" "$WORK/$f"; else rm -f "$WORK/$f"; fi
  done
  mkdir -p "$GOOD/data"
  cp -a "$WORK/data/." "$GOOD/data/" 2>/dev/null
  cp -a "$WORK/sitemap.xml" "$WORK/feed.xml" "$GOOD/" 2>/dev/null
  [ -f "$WORK/sitemap-news.xml" ] && cp -a "$WORK/sitemap-news.xml" "$GOOD/"
  return 0
}

promote_code() {
  [ "${CUR_RAN:-0}" = 1 ] && [ "${CUR_CHECKED:-0}" = 1 ] || return 0
  same_code "$CUR" "$LKG" || { copy_code "$CUR" "$LKG" && touch "$LKG/.yeni"; }
  return 0
}

# live: bir commit, valideynsiz. Tarixçə saxlanmır, ona görə dəqiqəlik yazı repo-nu şişirtmir.
file_tree() { # $1 qovluq: içindəki *.json-dan git ağacı
  local rows="" file blob
  for file in "$1"/*.json; do
    [ -f "$file" ] || continue
    blob="$(git -C "$REPO_DIR" hash-object -w "$file")" || return 1
    rows+="100644 blob $blob	$(basename "$file")"$'\n'
  done
  [ -n "$rows" ] || return 1
  printf '%s' "$rows" | git -C "$REPO_DIR" mktree
}

push_live() {
  local slot name dir data tree rows="" m root commit
  slot=$(( $(date +%s) / 60 ))
  dir="$SLOTS/$slot"
  mkdir -p "$dir"
  # Dil faylları (latest.az.json və s.) yalnız buradadır: hər dəqiqə dəyişən 4 kiçik fayl main-in tarixçəsini şişirtməsin
  # (publish_main onları silir). Sayt onları status.json-dakı "langs" ilə tanıyır, alınmasa ümumi latest.json-a qayıdır.
  # social: rəsmi hesabların yazıları (social_loop) dəqiqəlik kanalda; main-də də qalır (publish_main data/-nı köçürür).
  # reels: Videolent (sahib 2026-11-20: «tiktokdan geri qalmasın») — yeni video 10 dəqiqəlik main yayımını və Pages-i gözləməsin.
  for name in status latest latest.az latest.en latest.ru latest.tr markets social; do
    [ -f "$WORK/data/$name.json" ] && cp "$WORK/data/$name.json" "$dir/"
  done
  for name in reels canli; do   # canli: bu günün oyunları və canlı hesab (update_live_scores)
    [ -f "$WORK/data/$name.json" ] && cp "$WORK/data/$name.json" "$dir/"
  done
  # Oyunu gedən liqanın cədvəli və oyunları (updater.write_live_leagues; sahib 2026-11-26: «oyunlar bitdi, 1 dəq keçdi, cədvəl
  # dəyişmədi»): 10 dəqiqəlik main yayımını, Pages-i gözləmir. Qovluq data/-dan kənardadır: main-ə getmir. Yalnız yerli köçürmə.
  for name in "$WORK"/canli/*.json; do
    [ -f "$name" ] && cp "$name" "$dir/liqa-$(basename "$name")"
  done
  for old in $(ls "$SLOTS" | sort -n | head -n -"$KEEP_SLOTS"); do
    rm -rf "${SLOTS:?}/$old"
  done
  data="$(file_tree "$dir")" || return 1
  for name in $(ls "$SLOTS" | sort -n); do
    tree="$(file_tree "$SLOTS/$name")" || return 1
    rows+="040000 tree $tree	$name"$'\n'
  done
  m="$(printf '%s' "$rows" | git -C "$REPO_DIR" mktree)" || return 1
  root="$(printf '040000 tree %s\tdata\n040000 tree %s\tm\n' "$data" "$m" | git -C "$REPO_DIR" mktree)" || return 1
  commit="$(git -C "$REPO_DIR" commit-tree "$root" -m "Canlı lent")" || return 1
  timeout 25 git -C "$REPO_DIR" push -q --force origin "$commit:refs/heads/$LIVE_BRANCH"
}

# Əvvəlki işin son dəqiqələri qalsın: növbə dəyişəndə sayt 404 görməsin.
seed_slots() {
  mkdir -p "$SLOTS"
  timeout 30 git -C "$REPO_DIR" fetch -q --depth=1 origin "$LIVE_BRANCH" 2>/dev/null || return 0
  git -C "$REPO_DIR" archive FETCH_HEAD m 2>/dev/null | tar -x -C "$STATE" 2>/dev/null
  return 0
}

# Növbəti dövrə növbəti dəqiqənin 5-ci saniyəsində. CYCLE dəyişdirilibsə (sınaq) sadə gözləmə.
wait_next_cycle() {
  local left
  if [ "$CYCLE" = 60 ]; then
    left=$(( (65 - $(date +%s) % 60) % 60 ))
  else
    left=$(( CYCLE - (SECONDS - began) ))
  fi
  [ "$left" -gt 0 ] && sleep "$left"
  return 0
}

# Sürət (qırmızı xətt 3): baş səhifənin ilk ekranı index.html-də hazır gəlir (.github/scripts/prerender.cjs, cari main-dəki
# app.js və first.json ilə). Alınmasa və ya node yoxdursa index.html olduğu kimi qalır: sayt app.js ilə yenə dolur.
prerender_home() {
  command -v node >/dev/null 2>&1 || { echo "node yoxdur, ilk ekran hazırlanmır"; return 0; }
  if ! env -u GH_TOKEN -u GITHUB_TOKEN timeout -k 5 60 node "$REPO_DIR/.github/scripts/prerender.cjs" "$REPO_DIR"; then
    echo "::warning::İlk ekran hazırlanmadı, index.html dəyişmir"
    git -C "$REPO_DIR" checkout -q HEAD -- index.html 2>/dev/null
  fi
  return 0
}

# Rayon və idman mövzu səhifələri (rayon/<slug>/, idman/<slug>/, sitemap-movzu.xml; sahib 2026-11-06, Google üçün həqiqi ünvanlar).
# Seçim app.js-in clubMatches()-i ilə; alınmasa əvvəlki səhifələr qalır.
topic_pages() {
  command -v node >/dev/null 2>&1 || return 0
  if ! env -u GH_TOKEN -u GITHUB_TOKEN timeout -k 5 60 node "$REPO_DIR/.github/scripts/topics.cjs" "$REPO_DIR"; then
    echo "::warning::Mövzu səhifələri yazılmadı, əvvəlkilər qalır"
    git -C "$REPO_DIR" checkout -q HEAD -- rayon idman sitemap-movzu.xml 2>/dev/null
  fi
  return 0
}

# Öz xəbərlər (yalnız açarla yaranır; açarsız fayl yoxdur və bu funksiya heç nə etmir): main-ə çatmış sətir faylının nüsxəsi.
# Sürətli dövrə lentə yalnız bu nüsxədəki sətirləri qatır (updater.read_own_rows): kart birbaşa xəbərin səhifəsinə aparır, səhifə
# isə sayta yalnız main yazılışı və Pages yayımı ilə çatır. $1: nüsxənin görünməsinə qədər gözləmə, saniyə (Pages yayımı).
own_rows_live() {
  local src="$REPO_DIR/data/oz/xeberler.json" dst="$WORK/.cache/oz-yayimda.json"
  [ -f "$src" ] || return 0
  mkdir -p "$WORK/.cache" && cp "$src" "$dst.yeni" || return 0
  if [ "${1:-0}" -gt 0 ]; then ( sleep "$1"; mv -f "$dst.yeni" "$dst" ) & else mv -f "$dst.yeni" "$dst"; fi
  return 0
}

publish_main() {
  local i name
  for i in 1 2 3 4 5; do
    # --depth=1: iş fetch-depth 1 ilə başlayır (dayaz klon). PR main-ə birləşəndə ucda iki valideynli commit olur və adi fetch
    # PR budağının köklü olduğu bütün tarixçəni (repo 1,2 GB) çəkməyə başlayırdı: 90 saniyədə bitmir, 5 cəhd səssiz düşür və
    # iş bitənə qədər (~45 dəq) main-ə heç nə yazılmırdı (2026-11-25: 13:44, 19:22, 21:41 birləşmələrindən sonra; ÇL cədvəli
    # oyun bitəndən 35 dəqiqə sonra dəyişdi). Dayaz fetch yalnız ucu gətirir, push valideyni serverdə olduğu üçün işləyir.
    timeout 90 git -C "$REPO_DIR" fetch -q --depth=1 origin "$BRANCH" || { echo "main fetch alınmadı ($i)"; sleep 4; continue; }
    git -C "$REPO_DIR" reset -q --hard "origin/$BRANCH"
    mkdir -p "$REPO_DIR/data"
    cp -a "$GOOD/data/." "$REPO_DIR/data/"
    rm -f "$REPO_DIR/data/reader.json"   # səsli oxu söndürülüb: tam mətnlər yayımlanmır
    rm -f "$REPO_DIR"/data/latest.??.json   # dil faylları yalnız live budağındadır (push_live): main-in tarixçəsi şişməsin
    for name in sitemap.xml sitemap-news.xml feed.xml robots.txt; do
      [ -f "$WORK/$name" ] && cp -a "$WORK/$name" "$REPO_DIR/"
    done
    if [ -d "$WORK/bolme" ]; then rm -rf "$REPO_DIR/bolme"; cp -a "$WORK/bolme" "$REPO_DIR/bolme"; fi
    if [ -d "$WORK/x" ]; then rm -rf "$REPO_DIR/x"; cp -a "$WORK/x" "$REPO_DIR/x"; fi   # paylaşma səhifələri (updater.write_share_pages)
    if [ -d "$WORK/xeber" ]; then rm -rf "$REPO_DIR/xeber"; cp -a "$WORK/xeber" "$REPO_DIR/xeber"; fi   # Google üçün xəbər səhifələri (updater.write_story_pages)
    if [ -d "$WORK/icmal" ]; then rm -rf "$REPO_DIR/icmal"; cp -a "$WORK/icmal" "$REPO_DIR/icmal"; fi   # günün icmalı (updater.write_digest)
    prerender_home
    topic_pages
    # GOOD yenilənərkən oxunmuş ola bilər: commit-dən əvvəl yenidən yoxla.
    for name in $(py_t 20 "$PY" "$CUR/.github/scripts/check_outputs.py" "$REPO_DIR" || check_lkg "$REPO_DIR"); do
      git -C "$REPO_DIR" checkout -q HEAD -- "$name" 2>/dev/null || rm -f "$REPO_DIR/$name"
    done
    git -C "$REPO_DIR" add data sitemap.xml sitemap-news.xml feed.xml robots.txt bolme index.html 2>/dev/null
    if [ -d "$REPO_DIR/x" ]; then git -C "$REPO_DIR" add x 2>/dev/null; fi
    if [ -d "$REPO_DIR/xeber" ]; then git -C "$REPO_DIR" add xeber 2>/dev/null; fi
    if [ -d "$REPO_DIR/icmal" ]; then git -C "$REPO_DIR" add icmal 2>/dev/null; fi   # ayrıca: qovluq yoxdursa yuxarıdakı add pozulmasın
    for name in rayon idman sitemap-movzu.xml; do [ -e "$REPO_DIR/$name" ] && git -C "$REPO_DIR" add "$name" 2>/dev/null; done   # mövzu səhifələri (topic_pages)
    if git -C "$REPO_DIR" diff --cached --quiet; then
      touch "$STATE/code-sync"
      return 0
    fi
    git -C "$REPO_DIR" commit -q -m "Xəbərlər yeniləndi"
    if timeout 90 git -C "$REPO_DIR" push -q origin "HEAD:$BRANCH"; then
      touch "$STATE/code-sync"
      # «Profillərdə paylaş» işi: GitHub cron-u saatlarla gecikir, Pages yayımı isə workflow_run başlatmır.
      # Pages yeni /x/ səhifələrini yayımlasın deyə 90 s sonra, arxa planda; xəta nəzərə alınmır, dövrə gözləmir.
      ( sleep 90; gh_t workflow run social.yml --ref "$BRANCH" >/dev/null 2>&1 ) &
      own_rows_live 90   # öz xəbərlərin təzə səhifələri də həmin yayımla sayta çatır: sətirləri lentə ondan sonra
      return 0
    fi
    echo "main push alınmadı, yenidən cəhd ($i)"
    sleep 4
  done
  echo "::warning::main-ə yazılmadı (5 cəhd): sayt bu dövrəni main yayımı ilə almır"
  return 1
}

# Milli komandaların yarışları (sahib 2026-11-07): Vikipediyadan data/futbol/ml-*.json, asiya-kuboku.json (.github/scripts/milli.cjs).
# Skript özü 6 saatda bir (oyun günü 30 dəqiqədə bir) soruşur, dövrədə ən çox 2 sorğu; alınmasa əvvəlki fayl qalır.
milli_step() {
  command -v node >/dev/null 2>&1 || return 0
  env -u GH_TOKEN -u GITHUB_TOKEN timeout -k 5 60 node "$REPO_DIR/.github/scripts/milli.cjs" "$WORK" || echo "milli komandalar xəta verdi"
  return 0
}

slow_loop() {
  while :; do
    local began=$SECONDS left
    run_py --slow "$SLOW_LIMIT" || echo "yavaş dövrə xəta verdi"
    milli_step
    left=$((SLOW_EVERY - (SECONDS - began)))
    [ "$left" -gt 0 ] && sleep "$left"
  done
}

# Ölü linkləri tapır. Xəbər dövrəsindən ayrıdır: asılsa və ya düşsə xəbər axınına təsiri yoxdur.
# run_py işlədilmir: köhnə kod ehtiyatı --links bilmir və tam yeniləməyə keçərdi.
links_loop() {
  while :; do
    local began=$SECONDS left
    UPDATER_ROOT="$WORK" py_t "$LINKS_LIMIT" "$PY" "$CUR/updater.py" --links || echo "link yoxlaması xəta verdi"
    # Sahib (2026-11-06): şəkilsiz kart olmasın. Təzə xəbərin şəkli 30 saniyədə tapılır, yavaş dövrəni (4-5 dəq) gözləmir.
    UPDATER_ROOT="$WORK" py_t "$OG_LIMIT" "$PY" "$CUR/updater.py" --og || echo "təzə şəkil yoxlaması xəta verdi"
    left=$((LINKS_EVERY - (SECONDS - began)))
    [ "$left" -gt 0 ] && sleep "$left"
  done
}

# Rəsmi hesabların YouTube yazıları (sahib 2026-11-08: «1 dəq öncə Mehriban Əliyeva Youtubda paylaşımı bizdə yoxdur»): yavaş
# dövrəni (4-5 dəq) gözləmir, hər dəqiqə RSS + kanal səhifəsi (updater.merge_yt). social.json növbəti push_live ilə saytdadır.
# run_py işlədilmir: köhnə kod ehtiyatı --social bilmir və tam yeniləməyə keçərdi; kod bilmirsə döngü heç nə etmir.
social_loop() {
  while :; do
    local began=$SECONDS left
    if grep -q -- '"--social"' "$CUR/updater.py" 2>/dev/null; then
      UPDATER_ROOT="$WORK" py_t "$SOCIAL_LIMIT" "$PY" "$CUR/updater.py" --social || echo "sosial yoxlama xəta verdi"
    fi
    left=$((SOCIAL_EVERY - (SECONDS - began)))
    [ "$left" -gt 0 ] && sleep "$left"
  done
}

# Tıxac ölçüsü (sahib 2026-11-17: «tıxac xəbərlərimiz niyə Googla getmir»): GitHub cron-u tixac.yml-in «*/6»-nı saatda bir işlədirdi,
# öz pik saat bülletenimizə 6 ölçü lazımdır, 2 gəlirdi — bülleten heç dərc olunmurdu. Ölçünü bu iş başladır: pik saatda
# (Bakı 07–10, 17–20) 6 dəqiqədən, qalan vaxt (10–17, 20–22) 30 dəqiqədən bir. Yalnız dispatch: Mapbox açarı bu işə gəlmir, şəbəkə
# sorğusu xəbər dövrəsində deyil; cron ehtiyat qalır, təkrarı tixac.cjs (tooSoon) buraxır.
tixac_loop() {
  local last=-99999 every h
  while :; do
    h=$((10#$(date -u +%H)))
    case "$h" in 3|4|5|13|14|15) every=360 ;; 6|7|8|9|10|11|12|16|17) every=1800 ;; *) every=0 ;; esac
    if [ "$every" -gt 0 ] && [ $((SECONDS - last)) -ge "$every" ]; then
      gh_t workflow run tixac.yml --ref "$BRANCH" >/dev/null 2>&1 && last=$SECONDS
    fi
    sleep 30
  done
}

# Videolent (sahib 2026-11-20: «ən önəmli olan videoların daima yenilənməsidir», «çox sayda olmasıdır»): GitHub cron-u
# x-yazici.yml-in «20 dəqiqədən bir»ini 2026-11-19 17:26 – 11-20 03:57 arası heç işlətmədi, lent 11 saat dayandı. İşi bu döngü
# başladır: hər 20 dəqiqəlik pəncərədə (UTC dəqiqə 5, 25, 45-dən sonra) bir dəfə; əvvəlki iş hələ gedirsə və ya növbədədirsə yox.
# Yalnız dispatch: açar və X sorğusu bu işə gəlmir, xəbər dövrəsində şəbəkə sorğusu yoxdur; cron ehtiyat qalır.
#
# X növbəsi (kod siyahısındakı *_x.json, yəni oz_x.json). Sahib, 2026-11-27 («bu təklifini daha dərindən araşdır … nələr etmək olar
# kodda? … tap və düzəlt»): yazıcı növbəni main-ə yox, yalnız NOVBE_BRANCH budağına yazır. main-ə hər yazı ayrıca Pages yığımı
# (37–58 s), Fastly CDN-in təmizlənməsi və bütün faylların yeni ETag-ı idi: 2026-11-26-da (UTC) main-ə 87 belə yazı (bot yazılarının 43%-i).
# Növbə API ilə gəlir (git deyil: publish_main ilə toqquşmur), JSON yoxlanır, əsas döngü onu növbəti dövrənin əvvəlində koda qoyur
# (apply_queue: yerli fayl işi, şəbəkə yoxdur). main-in oz_x.json-u keçid anında donur (docs/x-yazici.md «Növbə budağı»):
# - budaq yoxdursa (HTTP 404; yazıcının ilk işi onu main-in nüsxəsi ilə yaradır) main oxunur;
# - bu işdə budaq bir dəfə oxunubsa (novbe-budaq) main heç vaxt mənbə deyil: şəbəkə xətası, vaxt bitməsi və ya budağın 404-ü
#   son nüsxəni saxlayır, main-in köhnə nüsxəsinə keçmir; main yazısından sonrakı copy_code da onu kod qovluğuna qaytarmır.
novbe_file() {
  local f
  for f in $CODE_FILES; do case "$f" in *_x.json) printf '%s' "$f" ;; esac; done
}

pull_reel_src() {
  local tmp="$STATE/reel-src.tmp" err="$STATE/reel-src.err" src ref="refs/heads/$NOVBE_BRANCH"
  src="$(novbe_file)"
  [ -n "$src" ] || return 0
  if ! gh_t api -H "Accept: application/vnd.github.raw" "repos/${GITHUB_REPOSITORY:-8ulduz/8ulduz}/contents/$src?ref=$ref" > "$tmp" 2> "$err"; then
    if [ -e "$STATE/novbe-budaq" ] || ! grep -q "(HTTP 404)" "$err"; then rm -f "$tmp" "$err"; return 1; fi
    ref="refs/heads/main"
    gh_t api -H "Accept: application/vnd.github.raw" "repos/${GITHUB_REPOSITORY:-8ulduz/8ulduz}/contents/$src?ref=$ref" > "$tmp" 2>/dev/null \
      || { rm -f "$tmp" "$err"; return 1; }
  fi
  rm -f "$err"
  py_t 10 "$PY" -c 'import json,sys; d=json.load(open(sys.argv[1], encoding="utf-8")); assert d.get("v") == 1 and isinstance(d.get("items", []), list) and isinstance(d.get("reels", []), list)' "$tmp" \
    || { rm -f "$tmp"; return 1; }
  [ "$ref" = "refs/heads/main" ] || touch "$STATE/novbe-budaq"
  mkdir -p "$NOVBE"
  if cmp -s "$tmp" "$NOVBE/$src"; then rm -f "$tmp"; else mv -f "$tmp" "$NOVBE/$src" && touch "$STATE/novbe.yeni"; fi
  return 0
}

# Son oxunan növbə kod qovluğuna (oz_x.py onu öz yanından oxuyur). Atomik: yavaş dövrə yarımçıq fayl oxumur (boş növbə = boş Videolent).
apply_queue() {
  local src
  src="$(novbe_file)"
  [ -n "$src" ] && [ -f "$NOVBE/$src" ] || return 0
  cmp -s "$NOVBE/$src" "$CUR/$src" && return 0
  cp "$NOVBE/$src" "$CUR/$src.yeni" && mv -f "$CUR/$src.yeni" "$CUR/$src"
}

xyazici_loop() {
  local last=-1 slot busy was=1
  while :; do
    slot=$(( ($(date +%s) - 300) / 1200 ))
    # yeni pəncərə gəlibsə və ya iş gedirsə (bitəndə növbə faylı dərhal götürülsün) dəqiqədə bir soruşulur
    if [ "$slot" != "$last" ] || [ "$was" = 1 ]; then
      busy="$(gh_t run list --workflow x-yazici.yml --limit 5 --json status --jq '[.[] | select(.status != "completed")] | length' 2>/dev/null || echo "")"
      if [ "$busy" = 0 ]; then
        # növbə alınmasa (şəbəkə) was=1 qalır: növbəti dəqiqə yenə
        if [ "$was" = 1 ] && pull_reel_src; then was=0; fi
        if [ "$slot" != "$last" ]; then
          gh_t workflow run x-yazici.yml --ref main >/dev/null 2>&1 && { last=$slot; was=1; }
        fi
      elif [ -n "$busy" ]; then
        was=1
      fi
    fi
    sleep 60
  done
}

# Video xəbər (sosial-video.yml; sahib 2026-11-22: «Facebook-da video xəbərlər verilsin… İnstagramda videolar verilsin»): iş
# axınının cron-u («17,47») 2026-11-22-də bir dəfə də işləmədi — bütün işlər əl ilə və ya PR-dan idi. İşi bu döngü başladır: hər
# 30 dəqiqəlik pəncərədə (UTC dəqiqə 17 və 47-dən sonra) bir dəfə; main-də gedən, növbədə olan və ya bu pəncərədə artıq başlamış
# video işi varsa yox (2026-11-23: dövrə hər saat yenidən başlayanda yaddaşı sıfırlanırdı və 04:17 pəncərəsində 04:36-da ikinci iş
# getdi). Yalnız dispatch: açar, Gemini, video bankı bu döngüyə gəlmir. Vaxt (Bakı 08–23), 120 dəqiqəlik fasilə və gündəlik hədd
# sosial-video.cjs-dədir: vaxtı deyilsə iş ~20 saniyədə bitir. Cron ehtiyat qalır.
video_loop() {
  local last=-1 slot start busy
  while :; do
    slot=$(( ($(date +%s) - 1020) / 1800 ))
    if [ "$slot" != "$last" ]; then
      start=$(( slot * 1800 + 1020 ))   # pəncərənin başlanğıcı (epoch)
      busy="$(gh_t run list --workflow sosial-video.yml --branch main --limit 5 --json status,createdAt --jq '[.[] | select(.status != "completed" or (.createdAt | fromdateiso8601) >= '"$start"')] | length' 2>/dev/null || echo "")"
      if [ "$busy" = 0 ]; then
        gh_t workflow run sosial-video.yml --ref main >/dev/null 2>&1 && last=$slot
      elif [ -n "$busy" ]; then
        last=$slot   # bu pəncərənin işi artıq gedir və ya getdi (cron, əl ilə, əvvəlki dövrə)
      fi
    fi
    sleep 60
  done
}

# Xəbər arxivi (arxiv.yml; paylaşılan keçidin saatlıq faylı): iş axınının cron-u («7,37») GitHub tərəfindən 4–10 saatda bir işlədilirdi
# (2026-11-21 – 11-25: 4 gündə 10 iş). 2026-11-25 səhəri arxiv 6 saat geri qalmışdı: son saatların paylaşılan keçidləri tam lenti
# gözləyirdi və sürət ölçüsü düşdü (sahib: «düzəlt»). İşi bu döngü başladır: hər 15 dəqiqəlik pəncərədə (UTC dəqiqə 7, 22, 37, 52-dən
# sonra) bir dəfə; main-də gedən, növbədə olan və ya bu pəncərədə artıq başlamış arxiv işi varsa yox. Yalnız dispatch: arxivin yazısı
# bu döngüyə gəlmir. Cron ehtiyat qalır.
arxiv_loop() {
  local last=-1 slot start busy
  while :; do
    slot=$(( ($(date +%s) - 420) / 900 ))
    if [ "$slot" != "$last" ]; then
      start=$(( slot * 900 + 420 ))   # pəncərənin başlanğıcı (epoch)
      busy="$(gh_t run list --workflow arxiv.yml --branch main --limit 5 --json status,createdAt --jq '[.[] | select(.status != "completed" or (.createdAt | fromdateiso8601) >= '"$start"')] | length' 2>/dev/null || echo "")"
      if [ "$busy" = 0 ]; then
        gh_t workflow run arxiv.yml --ref main >/dev/null 2>&1 && last=$slot
      elif [ -n "$busy" ]; then
        last=$slot   # bu pəncərənin işi artıq gedir və ya getdi (cron, əl ilə, əvvəlki dövrə)
      fi
    fi
    sleep 60
  done
}

# Asılan dövrəni tutur: hər dövrə addımının öz limiti var, bu son ehtiyatdır. Yazının alınmaması bura aid deyil:
# GitHub kəsiləndə işlək işi öldürmək boşluğu uzadar (yeni işi başlatmaq da mümkün olmaya bilər).
self_watch() { # $1 əsas proses
  while sleep 20; do
    if [ $(( $(date +%s) - $(stat -c %Y "$STATE/heartbeat" 2>/dev/null || echo 0) )) -ge "$STUCK_AFTER" ]; then
      echo "::warning::Dövrə ${STUCK_AFTER} saniyədir irəliləmir, iş dayandırılır. Növbəti iş başlayacaq."
      [ -n "${2:-}" ] && kill "$2" 2>/dev/null
      [ -n "${3:-}" ] && kill "$3" 2>/dev/null
      [ -n "${4:-}" ] && kill "$4" 2>/dev/null
      kill -TERM "$1" 2>/dev/null
      sleep 10
      kill -KILL "$1" 2>/dev/null
      return 0
    fi
  done
}

# --------------------------------------------------------------------- başlanğıc
if [ "${ROLLOUT:-}" != 1 ] && another_run_in_charge; then
  echo "Başqa iş lenti yeniləyir, bu iş lazım deyil."
  exit 0
fi

git -C "$REPO_DIR" config user.name "8ulduz-bot"
git -C "$REPO_DIR" config user.email "bot@8ulduz.az"
copy_code "$REPO_DIR" "$CUR"
mkdir -p "$WORK/data"
cp -a "$REPO_DIR/data/." "$WORK/data/" 2>/dev/null
rm -f "$WORK/data/reader.json"
[ -f "$REPO_DIR/CNAME" ] && cp "$REPO_DIR/CNAME" "$WORK/"
for name in sitemap.xml sitemap-news.xml feed.xml robots.txt; do
  [ -f "$REPO_DIR/$name" ] && cp "$REPO_DIR/$name" "$WORK/"
done
[ -d "$REPO_DIR/bolme" ] && cp -a "$REPO_DIR/bolme" "$WORK/bolme"
[ -d "$REPO_DIR/x" ] && cp -a "$REPO_DIR/x" "$WORK/x"   # mövcud paylaşma səhifələri: təzədən yazılmasın, 25 saatdan sonra silinsin
[ -d "$REPO_DIR/icmal" ] && cp -a "$REPO_DIR/icmal" "$WORK/icmal"   # günün icmalı: yazılmış buraxılış təkrar yazılmır
[ -d "$REPO_DIR/xeber" ] && cp -a "$REPO_DIR/xeber" "$WORK/xeber"   # Google üçün xəbər səhifələri: 30 gün qalır (updater.write_story_pages)
own_rows_live 0   # götürülmüş main-dəki öz sətirlərin səhifələri artıq saytdadır
guard_outputs
seed_slots
# X növbəsi: yuxarıdakı copy_code main-in donmuş oz_x.json-unu qoydu. Yavaş dövrə onu oxumazdan əvvəl x-novbe-dəki nüsxə gəlir
# (bir-iki sorğu, hər biri ən çox 15 s; alınmasa xyazici_loop dəqiqədə bir yenə soruşur).
pull_reel_src || { sleep 5; pull_reel_src; }
rm -f "$STATE/novbe.yeni"
apply_queue
rm -f "$LKG/.yeni"

slow_loop &
SLOW_PID=$!
links_loop &
LINKS_PID=$!
social_loop &
SOCIAL_PID=$!
tixac_loop &
TIXAC_PID=$!
xyazici_loop &
XYAZICI_PID=$!
video_loop &
VIDEO_PID=$!
arxiv_loop &
ARXIV_PID=$!
# Etibarlı köməkçi yalnız sabit GitHub API ünvanından qayda faylını oxuyur. Mənbə/lent prosesləri açarı görmür.
UPDATER_ROOT="$WORK" "$PY" "$REPO_DIR/.github/scripts/editorial_sync.py" --watch &
EDITORIAL_PID=$!
touch "$STATE/heartbeat"
self_watch $$ "$SLOW_PID" "$LINKS_PID" "$SOCIAL_PID" &
WATCH_PID=$!

START=$SECONDS
last_main=$SECONDS
last_handoff=-9999
push_fails=0
while :; do
  began=$SECONDS
  touch "$STATE/heartbeat"
  if [ -e "$STATE/code-sync" ]; then
    rm -f "$STATE/code-sync"
    # main-in oz_x.json-u donub: x-novbe oxunubsa main-in nüsxəsi kod qovluğuna köçürülmür (növbəni apply_queue qoyur)
    if [ -e "$STATE/novbe-budaq" ]; then copy_code "$REPO_DIR" "$CUR" "$(novbe_file)"; else copy_code "$REPO_DIR" "$CUR"; fi
  fi
  if [ -e "$STATE/novbe.yeni" ]; then rm -f "$STATE/novbe.yeni"; apply_queue; fi   # xyazici_loop: Videolentin təzə videoları (yerli fayl)
  run_py --fast "$FAST_LIMIT" || echo "sürətli dövrə xəta verdi"
  touch "$STATE/heartbeat"
  guard_outputs
  promote_code
  if push_live; then
    push_fails=0
    if [ "${ROLLOUT:-}" = 1 ]; then
      # Yalnız ilk uğurlu canlı yazıdan sonra; API işi sürətli dövrəni gözlətmir.
      FIRST_LIVE_PUSH_OK=1 "$PY" "$REPO_DIR/.github/scripts/finish_rollout.py" &
      ROLLOUT_PID=$!
      ROLLOUT=""
    fi
  else
    push_fails=$((push_fails + 1))
    echo "::warning::live budağına yazılmadı ($push_fails)"
    if [ "$push_fails" -ge "$PUSH_FAILS_MAX" ]; then
      echo "::warning::${push_fails} dövrədir yazılmır, yeni iş başlayır."
      exit 1
    fi
  fi
  touch "$STATE/heartbeat"
  if [ $((SECONDS - last_main)) -ge "$MAIN_EVERY" ] && { [ -z "$PUBLISH_PID" ] || ! kill -0 "$PUBLISH_PID" 2>/dev/null; }; then
    last_main=$SECONDS
    publish_main &
    PUBLISH_PID=$!
  fi
  ran=$((SECONDS - START))
  if [ "$ran" -ge "$HANDOFF_AFTER" ]; then
    if newer_run_started; then
      # Yeni iş işləyir: main-i sonuncu dəfə yazıb çıxırıq.
      [ -n "$PUBLISH_PID" ] && wait "$PUBLISH_PID" 2>/dev/null
      echo "Növbəti iş işləyir, bu iş bitir (${ran}s)."
      exit 0
    fi
    if [ $((SECONDS - last_handoff)) -ge 120 ]; then
      last_handoff=$SECONDS
      gh_t workflow run update.yml --ref "$BRANCH" || echo "Dispatch alınmadı"
    fi
    if [ "$ran" -ge "$MAX_RUN" ]; then
      echo "::warning::Növbəti iş görünmədi. Cron və nəzarətçi davam etdirəcək."
      exit 1
    fi
  fi
  wait_next_cycle
done
