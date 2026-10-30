#!/usr/bin/env bash
# QIRMIZI XƏTT 1 (docs/qirmizi-xetler.md): xəbər ən geci 60 saniyədən bir yenilənir və axın dayanmır.
#
# Üç axın, biri digərini gözləmir:
#   sürətli  hər CYCLE saniyə: lentlər, xəbər seçimi, status -> live budağı (tarixçəsiz, repo şişmir)
#   yavaş    arxa planda: məzənnə, şəkil, səs mətni, video, idman, SEO səhifələri
#   main     hər MAIN_EVERY saniyə: tam lent və SEO -> GitHub Pages
#
# Bir iş bitməzdən əvvəl növbətisini başladır və onu görəndən sonra çıxır, ona görə növbə dəyişəndə boşluq olmur.
set -uo pipefail

CYCLE="${CYCLE:-60}"
FAST_LIMIT="${FAST_LIMIT:-50}"
SLOW_LIMIT="${SLOW_LIMIT:-280}"
SLOW_EVERY="${SLOW_EVERY:-240}"
MAIN_EVERY="${MAIN_EVERY:-600}"
HANDOFF_AFTER="${HANDOFF_AFTER:-2820}"   # 47 dəq: növbəti işi başlat
MAX_RUN="${MAX_RUN:-3600}"               # 60 dəq: növbəti iş görünməsə də çıx (timeout-minutes-dən əvvəl)
BRANCH="${BRANCH:-main}"
LIVE_BRANCH="${LIVE_BRANCH:-live}"
RUN_ID="${GITHUB_RUN_ID:-0}"
GH="${GH:-gh}"
REPO_DIR="${REPO_DIR:-$PWD}"
PY="${PY:-$(command -v python || command -v python3)}"

WORK="$(mktemp -d)"      # məlumat: updater yalnız buraya yazır
CUR="$(mktemp -d)"       # cari kod
LKG="$REPO_DIR/.lkg"     # son uğurla işləmiş kod (actions/cache)
GOOD="$(mktemp -d)"      # son sağlam məlumat nüsxəsi
STATE="$(mktemp -d)"
CODE_FILES="updater.py reader_content.py content_policy.py assets/content-policy.js .github/scripts/check_outputs.py"
SLOW_PID=""
PUBLISH_PID=""

cleanup() { [ -n "$SLOW_PID" ] && kill "$SLOW_PID" 2>/dev/null; [ -n "$PUBLISH_PID" ] && wait "$PUBLISH_PID" 2>/dev/null; return 0; }
trap cleanup EXIT

copy_code() { # $1 mənbə, $2 hədəf
  local f
  for f in $CODE_FILES; do
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
  youngest="$("$GH" run list --workflow update.yml --branch "$BRANCH" --status in_progress --limit 20 --json databaseId,createdAt \
    --jq "[.[] | select(.databaseId != ${RUN_ID}) | .createdAt | fromdateiso8601] | max // 0" 2>/dev/null || echo 0)"
  [ -n "$youngest" ] && [ "$youngest" != "0" ] && [ $((now - youngest)) -lt $((HANDOFF_AFTER - 180)) ]
}

newer_run_started() {
  local me count
  me="$("$GH" run view "$RUN_ID" --json createdAt --jq '.createdAt | fromdateiso8601' 2>/dev/null || echo 0)"
  count="$("$GH" run list --workflow update.yml --branch "$BRANCH" --status in_progress --limit 20 --json databaseId,createdAt \
    --jq "[.[] | select(.databaseId != ${RUN_ID} and (.createdAt | fromdateiso8601) > ${me:-0})] | length" 2>/dev/null || echo 0)"
  [ "${count:-0}" != "0" ]
}

# Cari kod işləməsə son işlək kodla davam edir. Uğurlu cari kod yeni «işlək» olur.
run_py() { # $1 rejim, $2 limit
  if UPDATER_ROOT="$WORK" timeout "$2" "$PY" "$CUR/updater.py" "$1"; then
    if [ "$1" = "--fast" ] && ! same_code "$CUR" "$LKG"; then
      copy_code "$CUR" "$LKG" && touch "$LKG/.yeni"
    fi
    return 0
  fi
  if [ ! -f "$LKG/updater.py" ] || same_code "$CUR" "$LKG"; then
    return 1
  fi
  echo "::warning::updater.py ($1) xəta verdi — son işlək versiya ilə cəhd edilir"
  UPDATER_ROOT="$WORK" timeout "$2" "$PY" "$LKG/updater.py" "$1"
}

# Zədəli fayl son sağlam nüsxə ilə əvəz olunur; qaydanı pozan xəbər fayldan çıxarılır.
guard_outputs() {
  local f checker="$CUR/.github/scripts/check_outputs.py"
  for f in $("$PY" "$checker" "$WORK" 2>/dev/null); do
    echo "::warning::$f zədəlidir — son sağlam nüsxə saxlanılır"
    if [ -f "$GOOD/$f" ]; then cp "$GOOD/$f" "$WORK/$f"; else rm -f "$WORK/$f"; fi
  done
  mkdir -p "$GOOD/data"
  cp -a "$WORK/data/." "$GOOD/data/" 2>/dev/null
  cp -a "$WORK/sitemap.xml" "$WORK/feed.xml" "$GOOD/" 2>/dev/null
  return 0
}

# live: bir commit, valideynsiz. Tarixçə saxlanmır, ona görə dəqiqəlik yazı repo-nu şişirtmir.
push_live() {
  local rows="" name blob tree root commit
  for name in status latest markets; do
    [ -f "$WORK/data/$name.json" ] || continue
    blob="$(git -C "$REPO_DIR" hash-object -w "$WORK/data/$name.json")" || return 1
    rows+="100644 blob $blob	$name.json"$'\n'
  done
  [ -n "$rows" ] || return 1
  tree="$(printf '%s' "$rows" | git -C "$REPO_DIR" mktree)" || return 1
  root="$(printf '040000 tree %s\tdata\n' "$tree" | git -C "$REPO_DIR" mktree)" || return 1
  commit="$(git -C "$REPO_DIR" commit-tree "$root" -m "Canlı lent")" || return 1
  timeout 25 git -C "$REPO_DIR" push -q --force origin "$commit:refs/heads/$LIVE_BRANCH"
}

publish_main() {
  local i name
  for i in 1 2 3 4 5; do
    timeout 90 git -C "$REPO_DIR" fetch -q origin "$BRANCH" || { sleep 4; continue; }
    git -C "$REPO_DIR" reset -q --hard "origin/$BRANCH"
    mkdir -p "$REPO_DIR/data"
    cp -a "$GOOD/data/." "$REPO_DIR/data/"
    for name in sitemap.xml feed.xml robots.txt; do
      [ -f "$WORK/$name" ] && cp -a "$WORK/$name" "$REPO_DIR/"
    done
    if [ -d "$WORK/bolme" ]; then rm -rf "$REPO_DIR/bolme"; cp -a "$WORK/bolme" "$REPO_DIR/bolme"; fi
    # GOOD yenilənərkən oxunmuş ola bilər: commit-dən əvvəl yenidən yoxla.
    for name in $("$PY" "$CUR/.github/scripts/check_outputs.py" "$REPO_DIR" 2>/dev/null); do
      git -C "$REPO_DIR" checkout -q HEAD -- "$name" 2>/dev/null || rm -f "$REPO_DIR/$name"
    done
    git -C "$REPO_DIR" add data sitemap.xml feed.xml robots.txt bolme 2>/dev/null
    if git -C "$REPO_DIR" diff --cached --quiet; then
      touch "$STATE/code-sync"
      return 0
    fi
    git -C "$REPO_DIR" commit -q -m "Xəbərlər yeniləndi"
    if timeout 90 git -C "$REPO_DIR" push -q origin "HEAD:$BRANCH"; then
      touch "$STATE/code-sync"
      return 0
    fi
    echo "main push alınmadı, yenidən cəhd ($i)"
    sleep 4
  done
  return 1
}

slow_loop() {
  while :; do
    local began=$SECONDS left
    run_py --slow "$SLOW_LIMIT" || echo "yavaş dövrə xəta verdi"
    left=$((SLOW_EVERY - (SECONDS - began)))
    [ "$left" -gt 0 ] && sleep "$left"
  done
}

# --------------------------------------------------------------------- başlanğıc
if another_run_in_charge; then
  echo "Başqa iş lenti yeniləyir, bu iş lazım deyil."
  exit 0
fi

git -C "$REPO_DIR" config user.name "8ulduz-bot"
git -C "$REPO_DIR" config user.email "bot@8ulduz.az"
copy_code "$REPO_DIR" "$CUR"
mkdir -p "$WORK/data"
cp -a "$REPO_DIR/data/." "$WORK/data/" 2>/dev/null
[ -f "$REPO_DIR/CNAME" ] && cp "$REPO_DIR/CNAME" "$WORK/"
for name in sitemap.xml feed.xml robots.txt; do
  [ -f "$REPO_DIR/$name" ] && cp "$REPO_DIR/$name" "$WORK/"
done
[ -d "$REPO_DIR/bolme" ] && cp -a "$REPO_DIR/bolme" "$WORK/bolme"
guard_outputs
rm -f "$LKG/.yeni"

slow_loop &
SLOW_PID=$!

START=$SECONDS
last_main=$SECONDS
last_handoff=-9999
while :; do
  began=$SECONDS
  if [ -e "$STATE/code-sync" ]; then
    rm -f "$STATE/code-sync"
    copy_code "$REPO_DIR" "$CUR"
  fi
  run_py --fast "$FAST_LIMIT" || echo "sürətli dövrə xəta verdi"
  guard_outputs
  push_live || echo "::warning::live budağına yazılmadı"
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
      "$GH" workflow run update.yml --ref "$BRANCH" || echo "Dispatch alınmadı"
    fi
    if [ "$ran" -ge "$MAX_RUN" ]; then
      echo "::warning::Növbəti iş görünmədi. Cron və nəzarətçi davam etdirəcək."
      exit 1
    fi
  fi
  left=$((CYCLE - (SECONDS - began)))
  [ "$left" -gt 0 ] && sleep "$left"
done
