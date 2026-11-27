"""X növbəsi x-novbe budağında (sahib, 2026-11-27: «bu təklifini daha dərindən araşdır … nələr etmək olar kodda? … tap və düzəlt»).

Yazıcı (x-yazici.yml) oz_x.json-u yalnız x-novbe budağına yazır, main-ə heç nə: main-ə hər yazı ayrıca Pages yığımı, CDN təmizlənməsi
və bütün faylların yeni ETag-ı idi. Xəbər axını (pipeline.sh) növbəni budaqdan oxuyur; main-in oz_x.json-u keçid anında donur.

Burada iş axınının öz addımları yerli «origin» reposu ilə (şəbəkəsiz) və pipeline.sh-ın öz növbə funksiyaları saxta gh ilə işlədilir:
- ilk iş budağı main-in nüsxəsi ilə yaradır (heç bir sətir itmir), sonrakı iş budağın nüsxəsini oxuyur, main heç vaxt dəyişmir;
- budaq tarixçəsizdir: hər yazı içində yalnız oz_x.json olan valideynsiz commit, yalnız oxunan uca qarşı --force-with-lease;
- budaq oxunmasa iş dayanır; budaq oxunandan sonra dəyişibsə başqasının nüsxəsinin üstünə yazılmır;
- axın main-ə yalnız budaq yoxdursa (404) keçir; budaq bir dəfə oxunandan sonra main-in donmuş nüsxəsi kod qovluğuna qayıtmır."""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
WF = ROOT / ".github" / "workflows" / "x-yazici.yml"
SH = (ROOT / ".github" / "scripts" / "pipeline.sh").read_text(encoding="utf-8")


def doc(reels, items=()):
    """Növbə faylı yazıcının yazdığı kimi (2 boşluqlu girinti)."""
    return json.dumps({"v": 1, "items": [{"id": i} for i in items], "reels": [{"id": r} for r in reels]}, ensure_ascii=False, indent=2) + "\n"


def steps():
    """x-yazici.yml-in çoxsətirli run addımları: {ad: skript}."""
    text = WF.read_text(encoding="utf-8")
    found = re.finditer(r"^      - name: (.+)\n(?:(?!      - ).*\n)*?        run: \|\n((?:(?:          .*)?\n)+)", text, re.M)
    return {m.group(1): textwrap.dedent(m.group(2)) for m in found}


def step(prefix):
    names = [n for n in steps() if n.startswith(prefix)]
    assert len(names) == 1, (prefix, list(steps()))
    return steps()[names[0]]


def git(*args, cwd=None, check=True):
    run = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=60,
                         env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1"})
    if check and run.returncode:
        raise AssertionError(f"git {' '.join(args)}: {run.stderr}")
    return run.stdout.strip()


class WorkflowStepsTest(unittest.TestCase):
    """İş axınının «götür» və «göndər» addımları GitHub-dakı kimi (bash -e), yazıcının özü yerinə fayl dəyişikliyi."""

    READ = "Növbəni x-novbe budağından götür"
    PUSH = "Növbəni x-novbe budağına göndər"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name)
        self.home = self.tmp / "home"
        self.bin = self.tmp / "bin"   # sleep: təkrar döngüsü testi gözlətməsin
        for d in (self.home, self.bin):
            d.mkdir()
        (self.bin / "sleep").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (self.bin / "sleep").chmod(0o755)
        self.origin = self.tmp / "origin.git"
        git("init", "-q", "--bare", str(self.origin))
        seed = self.tmp / "seed"
        git("init", "-q", str(seed))
        (seed / "oz_x.json").write_text(doc(["0"]), encoding="utf-8")
        (seed / "oz_x.py").write_text("# kod\n", encoding="utf-8")
        git("add", "-A", cwd=seed)
        git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "main", cwd=seed)
        git("push", "-q", str(self.origin), "HEAD:refs/heads/main", cwd=seed)
        self.main = self.rev("refs/heads/main")
        self.n = 0

    def rev(self, ref):
        return git("--git-dir", str(self.origin), "rev-parse", "-q", "--verify", ref, check=False)

    def show(self, ref):
        return git("--git-dir", str(self.origin), "show", f"{ref}:oz_x.json") + "\n"

    def job(self):
        """Yeni işin iş qovluğu: main-in dayaz klonu (actions/checkout, ref: main)."""
        self.n += 1
        ws, temp = self.tmp / f"ws{self.n}", self.tmp / f"rt{self.n}"
        temp.mkdir()
        git("clone", "-q", "--depth", "1", "--branch", "main", "file://" + str(self.origin), str(ws))
        return ws, temp

    def run_step(self, name, ws, temp):
        env = {"PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}", "HOME": str(self.home), "NOVBE": "x-novbe",
               "RUNNER_TEMP": str(temp), "GITHUB_WORKSPACE": str(ws), "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_NOSYSTEM": "1"}
        return subprocess.run(["bash", "-e", "-c", step(name)], cwd=ws, env=env, capture_output=True, text=True, timeout=120)

    def ok(self, run):
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        return run

    def test_first_run_seeds_the_branch_from_main_later_runs_read_the_branch_and_main_never_moves(self):
        self.assertEqual(self.rev("refs/heads/x-novbe"), "", "başlanğıcda budaq yoxdur")
        ws, temp = self.job()
        self.ok(self.run_step(self.READ, ws, temp))
        seed = self.rev("refs/heads/x-novbe")
        self.assertTrue(seed, "ilk iş budağı yaradır")
        self.assertEqual(self.show("refs/heads/x-novbe"), doc(["0"]), "budaq main-in indiki nüsxəsi ilə başlayır: heç bir sətir itmir")
        self.assertEqual(git("--git-dir", str(self.origin), "ls-tree", "--name-only", "refs/heads/x-novbe"), "oz_x.json", "budaqda yalnız növbə faylı")
        self.assertEqual(git("--git-dir", str(self.origin), "rev-list", "--parents", "-n", "1", seed), seed, "valideynsiz: main-in tarixçəsi gəlmir")
        self.assertEqual((ws / "oz_x.json").read_text(encoding="utf-8"), doc(["0"]))

        (ws / "oz_x.json").write_text(doc(["0", "1"]), encoding="utf-8")   # yazıcı (x_yazici.py) növbəyə əlavə etdi
        (ws / "oz_x.py").write_text("# iş qovluğunda dəyişən başqa fayl\n", encoding="utf-8")
        (ws / "artiq.txt").write_text("budağa düşməməli\n", encoding="utf-8")
        self.ok(self.run_step(self.PUSH, ws, temp))
        tip = self.rev("refs/heads/x-novbe")
        self.assertNotEqual(tip, seed)
        self.assertEqual(self.show("refs/heads/x-novbe"), doc(["0", "1"]))
        self.assertEqual(git("--git-dir", str(self.origin), "ls-tree", "--name-only", tip), "oz_x.json", "yalnız oz_x.json, başqa fayl yox")
        self.assertEqual(git("--git-dir", str(self.origin), "rev-list", "--count", tip), "1", "tarixçəsiz: valideynsiz bir commit")
        self.assertEqual(git("--git-dir", str(self.origin), "log", "-1", "--format=%s", tip), "X xəbərləri növbəyə əlavə edildi")
        self.assertEqual(self.rev("refs/heads/main"), self.main, "main-ə heç nə yazılmır")

        # Növbəti iş: main-in oz_x.json-u donub (köhnədir), yazıcı budağın nüsxəsini oxuyur.
        ws, temp = self.job()
        self.assertEqual((ws / "oz_x.json").read_text(encoding="utf-8"), doc(["0"]))
        self.ok(self.run_step(self.READ, ws, temp))
        self.assertEqual((ws / "oz_x.json").read_text(encoding="utf-8"), doc(["0", "1"]), "main-in köhnə nüsxəsi budağınkını əvəz etmir")
        self.assertIn("dəyişiklik yoxdur", self.ok(self.run_step(self.PUSH, ws, temp)).stdout)
        self.assertEqual(self.rev("refs/heads/x-novbe"), tip, "dəyişiklik yoxdursa commit yoxdur")
        (ws / "oz_x.json").write_text(doc(["0", "1", "2"]), encoding="utf-8")
        self.ok(self.run_step(self.PUSH, ws, temp))
        self.assertEqual(self.show("refs/heads/x-novbe"), doc(["0", "1", "2"]))
        self.assertEqual(git("--git-dir", str(self.origin), "rev-list", "--count", "refs/heads/x-novbe"), "1", "tarixçə yığılmır")
        self.assertEqual(self.rev("refs/heads/main"), self.main)
        self.assertEqual(git("--git-dir", str(self.origin), "for-each-ref", "--format=%(refname)"),
                         "refs/heads/main\nrefs/heads/x-novbe", "başqa budaq yaranmır")

    def test_a_branch_that_cannot_be_read_stops_the_job_and_nothing_is_written(self):
        ws, temp = self.job()
        git("remote", "set-url", "origin", "file://" + str(self.tmp / "yoxdur.git"), cwd=ws)
        run = self.run_step(self.READ, ws, temp)
        self.assertNotEqual(run.returncode, 0, "budaq oxunmasa (yox deyil, xəta) iş dayanır")
        self.assertIn("::error::x-novbe budağı oxunmadı", run.stdout)
        self.assertEqual(self.rev("refs/heads/x-novbe"), "")
        self.assertEqual(self.rev("refs/heads/main"), self.main)

    def test_a_writer_that_lost_the_race_never_overwrites_the_other_copy(self):
        a, at = self.job()
        self.ok(self.run_step(self.READ, a, at))
        b, bt = self.job()
        self.ok(self.run_step(self.READ, b, bt))
        (a / "oz_x.json").write_text(doc(["0", "a"]), encoding="utf-8")
        self.ok(self.run_step(self.PUSH, a, at))
        tip = self.rev("refs/heads/x-novbe")
        (b / "oz_x.json").write_text(doc(["0", "b"]), encoding="utf-8")   # b köhnə ucu oxuyub: onun nüsxəsində «a» yoxdur
        run = self.ok(self.run_step(self.PUSH, b, bt))   # lease tutmur: heç nə yazılmır, iş uğurla bitir
        self.assertIn("x-novbe bu iş oxuyandan sonra dəyişib", run.stdout)
        self.assertEqual(self.rev("refs/heads/x-novbe"), tip, "budaqdakı sətirlər qalır")
        self.assertEqual(self.show("refs/heads/x-novbe"), doc(["0", "a"]))
        self.assertEqual(self.rev("refs/heads/main"), self.main)

    def test_a_broken_queue_file_or_a_network_error_writes_nothing_and_fails(self):
        ws, temp = self.job()
        self.ok(self.run_step(self.READ, ws, temp))
        seed = self.rev("refs/heads/x-novbe")
        for bad in ('{"v": 1, "reels": [', '{"v": 2, "reels": []}\n'):   # yarımçıq JSON və başqa forma
            (ws / "oz_x.json").write_text(bad, encoding="utf-8")
            run = self.run_step(self.PUSH, ws, temp)
            self.assertNotEqual(run.returncode, 0, bad)
            self.assertIn("::error::növbə faylı pozulub", run.stdout)
            self.assertEqual(self.rev("refs/heads/x-novbe"), seed)
        # Şəbəkə kəsilib: budağın dəyişdiyi bilinmir — «dəyişib» sayılmır, iş qırmızı bitir, heç nə yazılmır.
        (ws / "oz_x.json").write_text(doc(["0", "1"]), encoding="utf-8")
        git("remote", "set-url", "origin", "file://" + str(self.tmp / "yoxdur.git"), cwd=ws)
        run = self.run_step(self.PUSH, ws, temp)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("push alınmadı", run.stdout)
        self.assertNotIn("dəyişib", run.stdout)
        self.assertEqual(self.rev("refs/heads/x-novbe"), seed)
        self.assertEqual(self.rev("refs/heads/main"), self.main)


def function(name):
    found = re.search(rf"^{name}\(\) \{{[^\n]*\n.*?^\}}\n", SH, re.M | re.S)
    assert found, name
    return found.group(0)


class PipelineQueueTest(unittest.TestCase):
    """pipeline.sh-ın öz növbə funksiyaları və əsas döngünün növbə sətirləri; gh saxtadır: $FAKE/<ref>/<fayl>."""

    FAKE_GH = r'''
gh_t() {   # saxta «gh api»: $FAKE/<ref>/<fayl>; $FAKE/down varsa şəbəkə xətası (içində ref yazılıbsa yalnız o ref üçün); yoxdursa gh kimi 404
  local url="${@: -1}" file ref
  file="${url#*/contents/}"; file="${file%%\?*}"; ref="${url##*\?ref=}"
  if [ -e "$FAKE/down" ] && { [ ! -s "$FAKE/down" ] || [ "$(cat "$FAKE/down")" = "$ref" ]; }; then
    echo "gh: Get \"https://api.github.com/\": context deadline exceeded" >&2; return 1
  fi
  [ -f "$FAKE/$ref/$file" ] || { echo "gh: No commit found for the ref $ref (HTTP 404)" >&2; return 1; }
  cat "$FAKE/$ref/$file"
}
'''

    def script(self):
        loop = SH[SH.index('\nwhile :; do\n  began=$SECONDS'):]
        start = loop.index('  if [ -e "$STATE/code-sync" ]; then\n')
        end = loop.index("apply_queue; fi", start)
        cycle = loop[start:loop.index("\n", end) + 1]
        first = SH.index("\npull_reel_src || { sleep 5; pull_reel_src; }\n")
        startup = SH[first:SH.index("\napply_queue\n", first) + len("\napply_queue\n")]
        py_t = re.search(r"^py_t\(\) \{.*\}\n", SH, re.M).group(0)
        return ("set -u\nCODE_FILES='oz_x.py oz_x.json'\nNOVBE_BRANCH=x-novbe\nNOVBE=\"$STATE/novbe\"\n" + self.FAKE_GH + py_t
                + "".join(function(n) for n in ("copy_code", "novbe_file", "pull_reel_src", "apply_queue"))
                + "cycle_start() {\n" + cycle + "}\nstartup() {\n" + startup + "}\n" + textwrap.dedent(self.SCENARIO))

    SCENARIO = r'''
    fail() { echo "$1"; exit 1; }
    same() { cmp -s "$1" "$2" || fail "$3"; }
    put() { mkdir -p "$(dirname "$1")"; printf '%s\n' "$2" > "$1"; }
    BR="$FAKE/refs/heads/x-novbe/oz_x.json"; MAIN="$FAKE/refs/heads/main/oz_x.json"
    put "$MAIN" '{"v": 1, "reels": [{"id": "m0"}]}'                # main-in nüsxəsi (keçiddən əvvəl yazıcı buraya yazırdı)
    cp "$MAIN" "$REPO_DIR/oz_x.json"; put "$REPO_DIR/oz_x.py" kod1
    copy_code "$REPO_DIR" "$CUR"                                     # işin əvvəli: main-in kodu və növbəsi

    # Budaq hələ yoxdur (yazıcının ilk işindən əvvəl): main oxunur, budaq sayılmır.
    startup
    same "$CUR/oz_x.json" "$MAIN" "budaq yoxdursa main-in nüsxəsi"
    [ ! -e "$STATE/novbe-budaq" ] || fail "main budaq sayılmır"
    # Köhnə yazıcının son yazısı main-ə (keçid anı): main yazısından sonra kod qovluğuna gəlir.
    put "$REPO_DIR/oz_x.json" '{"v": 1, "reels": [{"id": "m0"}, {"id": "m1"}]}'; cp "$REPO_DIR/oz_x.json" "$MAIN"
    touch "$STATE/code-sync"; cycle_start
    same "$CUR/oz_x.json" "$REPO_DIR/oz_x.json" "budaq yoxdursa main yazısı növbəni gətirir"
    # Budağın sorğusu vaxtında cavab vermir (404 deyil), main isə cavab verir: main-ə keçilmir, heç nə dəyişmir.
    printf refs/heads/x-novbe > "$FAKE/down"; rm -f "$STATE/novbe.yeni"
    pull_reel_src && fail "xəta uğur sayılmır"
    [ ! -e "$STATE/novbe.yeni" ] || fail "budaq cavab verməyəndə main-in nüsxəsi götürülmür"
    : > "$FAKE/down"; pull_reel_src && fail "şəbəkə yoxdur"
    rm "$FAKE/down"

    # Yazıcı budağı main-in nüsxəsi ilə yaratdı və yazdı.
    put "$BR" '{"v": 1, "reels": [{"id": "m0"}, {"id": "m1"}, {"id": "b1"}]}'
    pull_reel_src || fail "budaq oxunur"
    [ -e "$STATE/novbe-budaq" ] || fail "budaq görüldü"
    cycle_start
    same "$CUR/oz_x.json" "$BR" "əsas döngü budağın nüsxəsini koda qoyur"
    [ ! -e "$STATE/novbe.yeni" ] || fail "bayraq götürülür"

    # main yazısından sonra (code-sync): kod yenilənir, main-in donmuş oz_x.json-u budağınkının üstünə yazılmır.
    put "$REPO_DIR/oz_x.py" kod2
    touch "$STATE/code-sync"; cycle_start
    [ "$(cat "$CUR/oz_x.py")" = kod2 ] || fail "kod main-dən gəlir"
    same "$CUR/oz_x.json" "$BR" "main-in köhnə nüsxəsi budağınkını əvəz etmir"

    # Budaq 404 verir (məsələn silinib) və ya şəbəkə yoxdur: son budaq nüsxəsi qalır, main-ə keçilmir.
    mv "$FAKE/refs/heads/x-novbe" "$FAKE/silinib"
    pull_reel_src && fail "budaq görünəndən sonra 404 main-ə keçirmir"
    mv "$FAKE/silinib" "$FAKE/refs/heads/x-novbe"
    touch "$FAKE/down"; pull_reel_src && fail "şəbəkə xətası"; rm "$FAKE/down"
    same "$STATE/novbe/oz_x.json" "$BR" "son nüsxə qalır"

    # Pozulmuş və ya başqa formalı fayl qəbul olunmur.
    cp "$BR" "$FAKE/b1.json"
    printf '{"v": 1, "reels": ' > "$BR"; pull_reel_src && fail "yarımçıq JSON"
    put "$BR" '{"v": 2, "reels": []}'; pull_reel_src && fail "başqa versiya"
    put "$BR" '{"v": 1, "reels": {}}'; pull_reel_src && fail "reels siyahı deyil"
    same "$STATE/novbe/oz_x.json" "$FAKE/b1.json" "pozulmuş fayl son nüsxəni əvəz etmir"
    cp "$FAKE/b1.json" "$BR"
    rm -f "$STATE/novbe.yeni"; pull_reel_src || fail "eyni nüsxə"
    [ ! -e "$STATE/novbe.yeni" ] || fail "eyni nüsxədə bayraq yoxdur"

    # Yazıcının növbəti işi: yeni nüsxə növbəti dövrədə kod qovluğundadır.
    put "$BR" '{"v": 1, "reels": [{"id": "b2"}]}'
    pull_reel_src || fail "yeni nüsxə"
    cycle_start
    same "$CUR/oz_x.json" "$BR" "yeni nüsxə koda keçir"

    # Növbəti iş başlayır: copy_code main-in donmuş nüsxəsini qoyur, startup budağınkını yavaş dövrədən əvvəl gətirir.
    STATE="$STATE2"; CUR="$CUR2"; NOVBE="$STATE/novbe"
    copy_code "$REPO_DIR" "$CUR"
    startup
    same "$CUR/oz_x.json" "$BR" "işin əvvəlində budağın nüsxəsi"
    [ -e "$STATE/novbe-budaq" ] || fail "budaq görüldü"
    ls "$STATE" "$CUR" | grep -q -e '\.tmp$' -e '\.err$' -e '\.yeni$' && fail "müvəqqəti fayl qalır"
    # Növbəti iş başlayanda GitHub cavab vermir: main-in nüsxəsi ilə başlayır, xyazici_loop sonra yenə soruşur.
    STATE="$STATE3"; CUR="$CUR3"; NOVBE="$STATE/novbe"
    copy_code "$REPO_DIR" "$CUR"
    touch "$FAKE/down"; startup; rm "$FAKE/down"
    same "$CUR/oz_x.json" "$REPO_DIR/oz_x.json" "şəbəkəsiz başlanğıcda main-in nüsxəsi qalır"
    [ ! -e "$STATE/novbe-budaq" ] || fail "budaq görülməyib"
    exit 0
    '''

    def test_queue_comes_from_the_branch_and_main_is_only_a_fallback_before_the_branch_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            dirs = {k: pathlib.Path(tmp, k) for k in ("REPO_DIR", "CUR", "STATE", "CUR2", "STATE2", "CUR3", "STATE3", "FAKE", "bin")}
            for d in dirs.values():
                d.mkdir()
            (dirs["bin"] / "sleep").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            (dirs["bin"] / "sleep").chmod(0o755)
            env = {**os.environ, **{k: str(v) for k, v in dirs.items() if k != "bin"}, "PY": sys.executable,
                   "PATH": f"{dirs['bin']}{os.pathsep}{os.environ['PATH']}"}
            run = subprocess.run(["bash", "-c", self.script()], env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual((run.returncode, run.stdout.strip()), (0, ""), run.stderr)

    def test_the_loop_retries_a_failed_pull_and_only_dispatches(self):
        loop = function("xyazici_loop")
        self.assertIn('if [ "$was" = 1 ] && pull_reel_src; then was=0; fi', loop, "növbə alınmasa növbəti dəqiqə yenə soruşulur")
        self.assertIn("gh_t workflow run x-yazici.yml --ref main", loop)
        self.assertNotRegex(loop, r"git |contents/", "döngü özü yazmır və oxumur")
        # Qırmızı xətt 2: X məzmunu lentə yenə yalnız content_policy.enforce ilə düşür (növbənin yeri dəyişib, qapı yox).
        up = (ROOT / "updater.py").read_text(encoding="utf-8")
        reels = up[up.index("def write_reels("):up.index("\n\n", up.index("def write_reels("))]
        self.assertIn("content_policy.enforce(probe)", reels)


if __name__ == "__main__":
    unittest.main()
