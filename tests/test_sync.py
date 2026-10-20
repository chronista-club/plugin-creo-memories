import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FAKE_CURL = r'''#!/bin/sh
# 引数から atlasId を拾い、無い atlas なら 400 (creo の「atlas が無い」)、それ以外は 1 件返す。-w の末尾に status を添える
atlas=""
labels='{"labels":[{"id":"lbl-1","name":"cache:claude"}]}'
w=""
# 本物の curl と同じく、-w が付けば labels にも末尾の status を付ける
case "$*" in *api/labels*) printf '%s' "$labels"; case "$*" in *http_code*) printf '\n200' ;; esac; exit 0 ;; esac
while [ $# -gt 0 ]; do
  case "$1" in
    --data-urlencode) case "$2" in atlasId=*) atlas="${2#atlasId=}" ;; esac; shift ;;
    -w) w="$2"; shift ;;
  esac
  shift
done
if [ "$atlas" = "ghost-repo" ]; then
  printf '%s' '{"error":"atlas が無い: ghost-repo (id / slug / 表示名のどれでも)"}'
  [ -n "$w" ] && printf '\n400'
  exit 0
fi
long="$(printf 'あ%.0s' $(seq 1 120))"
printf '%s' '{"memories":[{"id":"mem_1","content":"# t\n\nbody","updated_at":"2026-09-08T00:00:00Z","kind":"context","metadata":{"cache":{"name":"note-'"$atlas"'","type":"project"}}},{"id":"mem_2","content":"# '"$long"'\n\nbody","updated_at":"2026-09-08T00:00:00Z","kind":"context","metadata":{"cache":{"name":"long-'"$atlas"'","type":"project"}}}],"total":2}'
[ -n "$w" ] && printf '\n200'
exit 0
'''


class Sync(unittest.TestCase):
    def test_missing_atlas_is_zero_not_failure(self):
        if subprocess.run(['sh', '-c', 'command -v jq || command -v jaq'], capture_output=True).returncode != 0:
            self.skipTest('jq が無い')
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / 'home'
            (home / '.config/creo-memories').mkdir(parents=True)
            (home / '.config/creo-memories/api-key').write_text('k')
            binary = Path(temp) / 'bin'
            binary.mkdir()
            curl = binary / 'curl'
            curl.write_text(FAKE_CURL)
            curl.chmod(0o755)
            # infer-atlas が repo 名 ghost-repo を出すよう、cwd を同名 dir に
            cwd = Path(temp) / 'ghost-repo'
            cwd.mkdir()
            # CI (ubuntu runner) は XDG_CONFIG_HOME を持つことがあり、api-key の探索先が HOME から外れて黙って skip する → 明示
            env = dict(os.environ, HOME=str(home), PATH=str(binary) + os.pathsep + os.environ['PATH'], CREO_SYNC_FORCE='1', XDG_CACHE_HOME=str(Path(temp) / 'cache'), XDG_CONFIG_HOME=str(home / '.config'))
            env.pop('CLAUDE_PLUGIN_ROOT', None)
            result = subprocess.run(['bash', str(ROOT / 'scripts/sync-local-cache.sh'), '--cwd', str(cwd)], text=True, env=env, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('ghost-repo は creo に無い', result.stderr, result.stdout + result.stderr)
            self.assertNotIn('取得に失敗', result.stdout + result.stderr)
            self.assertIn('件を写した', result.stdout)
            # claude / agent の分は写っている (atlas が無いことで全体を捨てない)
            mem_dirs = list((home / '.claude/projects').glob('*/memory'))
            self.assertEqual(len(mem_dirs), 1, mem_dirs)
            names = sorted(p.name for p in mem_dirs[0].glob('*.md'))
            self.assertIn('MEMORY.md', names)
            self.assertTrue(any(n.startswith('note-') for n in names), names)
            # index の 1 行は題を 40 字で切る (MEMORY.md は毎 session 読み込まれ、24.4KB の上限がある。
            # 2026-10-01 に 126 件で 20.9KB まで育ち hook に圧縮を促された)。file の description は全文
            # 1 行は `- <name>.md — <題>`。markdown のリンク `[name](name.md)` は名前を 2 回書き、1 行の約半分
            # (平均 64 バイト) を食っていた。index を読むのはモデルなので file 名が 1 回あれば足りる
            index = (mem_dirs[0] / 'MEMORY.md').read_text()
            long_line = next(l for l in index.splitlines() if l.startswith('- long-'))
            self.assertRegex(long_line, r'^- long-[^ ]+\.md — ' + 'あ' * 40 + '…$')
            self.assertNotIn('あ' * 41, long_line)
            self.assertFalse(any(l.startswith('- [') for l in index.splitlines()), index)
            long_file = next(mem_dirs[0].glob('long-*.md')).read_text()
            self.assertIn('description: ' + 'あ' * 120, long_file)


# labels の返りを env で変える版 (FAKE_LABELS = ok / 401 / 502 / fail)。-w が付けば末尾に status
FAKE_CURL_LABELS = r"""#!/bin/sh
w=""
for a in "$@"; do case "$prev" in -w) w="$a" ;; esac; prev="$a"; done
case "$*" in
  *api/labels*)
    case "${FAKE_LABELS:-ok}" in
      # 本物の curl は失敗しても -w の %{http_code} = 000 を stdout の最後に書く
      fail) echo 'curl: (7) Failed to connect to app.creo-memories.in port 443' >&2; [ -n "$w" ] && printf '\n000'; exit 7 ;;
      401) printf '%s' '{"error":"unauthorized"}'; [ -n "$w" ] && printf '\n401'; exit 0 ;;
      502) printf '%s' '<html>bad gateway</html>'; [ -n "$w" ] && printf '\n502'; exit 0 ;;
      none) printf '%s' '{"labels":[]}'; [ -n "$w" ] && printf '\n200'; exit 0 ;;
    esac
    printf '%s' '{"labels":[{"id":"lbl-1","name":"cache:claude"}]}'; [ -n "$w" ] && printf '\n200'; exit 0 ;;
esac
printf '%s' '{"memories":[{"id":"mem_1","content":"# 題\n\ncreo の本文","updated_at":"2026-09-08T00:00:00Z","kind":"context","metadata":{"cache":{"name":"shared-note","type":"project"}}}],"total":1}'
[ -n "$w" ] && printf '\n200'
exit 0
"""


def _no_git_env(env):
    # git を子プロセスで呼ぶテストは GIT_* を落とす (継いだ GIT_DIR で本物の repo を触らない。2026-10-01 の creo の事故)
    return {k: v for k, v in env.items() if not k.startswith('GIT_')}


class SyncHarness(unittest.TestCase):
    def setUp(self):
        if subprocess.run(['sh', '-c', 'command -v jq || command -v jaq'], capture_output=True).returncode != 0:
            self.skipTest('jq が無い')
        self._temp = tempfile.TemporaryDirectory()
        # macOS の一時 dir は /var → /private/var の symlink。git は実パスを返すので、最初から実パスで揃える
        self.temp = Path(os.path.realpath(self._temp.name))
        self.home = self.temp / 'home'
        (self.home / '.config/creo-memories').mkdir(parents=True)
        (self.home / '.config/creo-memories/api-key').write_text('k')
        self.bin = self.temp / 'bin'
        self.bin.mkdir()
        curl = self.bin / 'curl'
        curl.write_text(FAKE_CURL_LABELS)
        curl.chmod(0o755)
        self.cache = self.temp / 'cache'

    def tearDown(self):
        self._temp.cleanup()

    def env(self, **extra):
        env = dict(os.environ, HOME=str(self.home), PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                   CREO_SYNC_FORCE='1', XDG_CACHE_HOME=str(self.cache), XDG_CONFIG_HOME=str(self.home / '.config'))
        env.pop('CLAUDE_PLUGIN_ROOT', None)
        env.update(extra)
        return _no_git_env(env)

    def run_sync(self, cwd, **extra):
        return subprocess.run(['bash', str(ROOT / 'scripts/sync-local-cache.sh'), '--cwd', str(cwd)],
                              text=True, env=self.env(**extra), capture_output=True)

    @staticmethod
    def key(path):
        return ''.join(c if c.isascii() and c.isalnum() else '-' for c in str(path))


class SyncTarget(SyncHarness):
    def test_lane_worktree_writes_to_the_main_checkout_memory_dir(self):
        # Claude Code は worktree (VP lane) の session でも、本体の checkout の project dir の memory を読む
        # (2026-10-20 実測: cwd = creo-memories/.vp/lanes/webui、読む memory = -Users-…-creo-memories/memory)
        if subprocess.run(['git', '--version'], capture_output=True).returncode != 0:
            self.skipTest('git が無い')
        repo = self.temp / 'proj'
        repo.mkdir()
        git = lambda *a, cwd=repo: subprocess.run(['git', *a], cwd=cwd, env=self.env(), check=True, capture_output=True)
        git('init', '-q')
        git('-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-q', '--allow-empty', '-m', 'init')
        lane = repo / '.vp/lanes/web'
        git('worktree', 'add', '-q', '--detach', str(lane))
        result = self.run_sync(lane)
        self.assertEqual(result.returncode, 0, result.stderr)
        main_dir = self.home / '.claude/projects' / self.key(repo) / 'memory'
        lane_dir = self.home / '.claude/projects' / self.key(lane) / 'memory'
        self.assertTrue((main_dir / 'shared-note.md').exists(), list((self.home / '.claude/projects').glob('*')))
        self.assertFalse(lane_dir.exists())

    def _repo(self, name):
        repo = self.temp / name
        repo.mkdir()
        git = lambda *a: subprocess.run(['git', *a], cwd=repo, env=self.env(), check=True, capture_output=True)
        git('init', '-q')
        git('-c', 'user.name=t', '-c', 'user.email=t@example.com', 'commit', '-q', '--allow-empty', '-m', 'init')
        return repo, git

    def test_inherited_git_env_does_not_redirect_the_target(self):
        # hook の env に GIT_* が残っていても (GIT_COMMON_DIR は git-common-dir の答えそのものを変える)、cwd の repo を見る
        if subprocess.run(['git', '--version'], capture_output=True).returncode != 0:
            self.skipTest('git が無い')
        repo, _ = self._repo('proj')
        other, _ = self._repo('other')
        r = subprocess.run(['bash', str(ROOT / 'scripts/sync-local-cache.sh'), '--cwd', str(repo)], text=True,
                           env=dict(self.env(), GIT_COMMON_DIR=str(other / '.git'), GIT_DIR=str(other / '.git')),
                           capture_output=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((self.home / '.claude/projects' / self.key(repo) / 'memory/shared-note.md').exists(),
                        list((self.home / '.claude/projects').glob('*')))

    def test_exported_cdpath_does_not_break_the_target(self):
        # 本体の直下では git-common-dir が相対の `.git`。CDPATH が export されていると cd がそれを引き、
        # 移った先を stdout に出す (写し先の名前に改行が入る。santa 2 巡目)
        if subprocess.run(['git', '--version'], capture_output=True).returncode != 0:
            self.skipTest('git が無い')
        repo, _ = self._repo('proj')
        elsewhere = self.temp / 'elsewhere'
        elsewhere.mkdir()
        r = self.run_sync(repo, CDPATH=f'.:{elsewhere}')
        self.assertEqual(r.returncode, 0, r.stderr)
        dirs = [p.name for p in (self.home / '.claude/projects').glob('*')]
        self.assertEqual(dirs, [self.key(repo)])

    def test_subdirectory_of_a_repo_writes_to_the_repo_root(self):
        # 本体の checkout の subdir では git-common-dir が相対 (../.git) で返る。git 2.31 より前は
        # --path-format=absolute を知らず、flag をそのまま出していた (写し先の名前に改行が入る)
        if subprocess.run(['git', '--version'], capture_output=True).returncode != 0:
            self.skipTest('git が無い')
        repo, _ = self._repo('proj')
        sub = repo / 'apps/web'
        sub.mkdir(parents=True)
        r = self.run_sync(sub)
        self.assertEqual(r.returncode, 0, r.stderr)
        dirs = [p.name for p in (self.home / '.claude/projects').glob('*')]
        self.assertEqual(dirs, [self.key(repo)])

    def test_git_older_than_2_31_still_finds_the_main_checkout(self):
        # git 2.31 より前の rev-parse は知らない --path-format=absolute を 1 行目にそのまま出す
        # (builtin/rev-parse.c の show_flag)。その形を真似た git で、lane から本体に写せること
        real = subprocess.run(['sh', '-c', 'command -v git'], capture_output=True, text=True).stdout.strip()
        if not real:
            self.skipTest('git が無い')
        repo, git = self._repo('proj')
        lane = repo / '.vp/lanes/web'
        git('worktree', 'add', '-q', '--detach', str(lane))
        old = self.bin / 'git'
        old.write_text(f'''#!/bin/sh
for a in "$@"; do
  case "$a" in --path-format=*) echo "$a"; set -- $(for b in "$@"; do [ "$b" = "$a" ] || printf '%s\\n' "$b"; done); break ;; esac
done
exec {real} "$@"
''')
        old.chmod(0o755)
        r = self.run_sync(lane)
        self.assertEqual(r.returncode, 0, r.stderr)
        dirs = [p.name for p in (self.home / '.claude/projects').glob('*')]
        self.assertEqual(dirs, [self.key(repo)])

    def test_plain_dir_still_uses_cwd(self):
        plain = self.temp / 'plain'
        plain.mkdir()
        result = self.run_sync(plain)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.home / '.claude/projects' / self.key(plain) / 'memory/shared-note.md').exists())


class SyncDiagnosis(SyncHarness):
    def out(self, mode):
        plain = self.temp / 'plain'
        plain.mkdir(exist_ok=True)
        r = self.run_sync(plain, FAKE_LABELS=mode)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout + r.stderr

    def test_http_error_is_not_reported_as_missing_label(self):
        for code in ('401', '502'):
            o = self.out(code)
            self.assertIn(f'HTTP {code}', o)
            self.assertNotIn('が無い (label_create', o)

    def test_curl_failure_names_the_curl_it_ran(self):
        o = self.out('fail')
        self.assertIn('繋がらない', o)
        self.assertIn(str(self.bin / 'curl'), o)
        # 何と言ったか (DNS / TLS / timeout の見分け)。-w の 000 ではなく curl の言葉
        self.assertIn('Failed to connect', o)
        self.assertNotIn('が無い (label_create', o)

    def test_missing_label_is_still_reported(self):
        self.assertIn('label cache:claude が無い', self.out('none'))


class SyncKeepsLocalOnly(SyncHarness):
    def test_local_file_with_other_body_is_stashed_even_without_a_hash_tool(self):
        # shasum が無い (or 壊れている) と本文の比較が空どうしで「同じ」になり、local の本文を上書きしていた
        plain = self.temp / 'plain'
        plain.mkdir()
        mem = self.home / '.claude/projects' / self.key(plain) / 'memory'
        mem.mkdir(parents=True)
        (mem / 'shared-note.md').write_text('---\nname: shared-note\n---\n\nlocal にしか無い本文\n')
        for tool in ('shasum', 'sha256sum'):
            stub = self.bin / tool
            stub.write_text('#!/bin/sh\nexit 1\n')
            stub.chmod(0o755)
        r = self.run_sync(plain)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('creo の本文', (mem / 'shared-note.md').read_text())
        stashed = mem / 'shared-note.local-only.md'
        self.assertTrue(stashed.exists(), list(mem.glob('*')))
        self.assertIn('local にしか無い本文', stashed.read_text())

    def test_local_file_is_stashed_when_the_bodies_cannot_be_read(self):
        # awk が壊れていると本文が両方空になり、比較が「同じ」に戻る (shasum の時と同じ形の穴)
        plain = self.temp / 'plain'
        plain.mkdir()
        mem = self.home / '.claude/projects' / self.key(plain) / 'memory'
        mem.mkdir(parents=True)
        (mem / 'shared-note.md').write_text('---\nname: shared-note\n---\n\nlocal にしか無い本文\n')
        stub = self.bin / 'awk'
        stub.write_text('#!/bin/sh\nexit 2\n')
        stub.chmod(0o755)
        r = self.run_sync(plain)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('local にしか無い本文', (mem / 'shared-note.local-only.md').read_text())

    def test_same_body_is_not_stashed(self):
        plain = self.temp / 'plain'
        plain.mkdir()
        mem = self.home / '.claude/projects' / self.key(plain) / 'memory'
        mem.mkdir(parents=True)
        (mem / 'shared-note.md').write_text('---\nname: shared-note\n---\n\ncreo の本文\n')
        r = self.run_sync(plain)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((mem / 'shared-note.local-only.md').exists())


class SyncLog(SyncHarness):
    def test_background_runs_append_to_the_log(self):
        # 背景の同期の log は 1 枚を毎回上書きしていて、別の project の session が前の失敗を消していた
        import json, time
        plain = self.temp / 'plain'
        plain.mkdir()
        log = self.cache / 'creo-memories/sync.log'
        for _ in range(2):
            subprocess.run(['bash', str(ROOT / 'scripts/sync-local-cache.sh'), '--background'],
                           input=json.dumps({'cwd': str(plain)}), text=True, env=self.env(FAKE_LABELS='401'),
                           capture_output=True, check=True)
            deadline = time.time() + 15
            before = log.read_text().count('HTTP 401') if log.exists() else 0
            while time.time() < deadline:
                if log.exists() and log.read_text().count('HTTP 401') > before:
                    break
                time.sleep(0.2)
            time.sleep(0.5)  # 前の同期が lock を外し終えるまで (次の回が「別の同期が走っている」にならないように)
        self.assertEqual(log.read_text().count('HTTP 401'), 2, log.read_text())


if __name__ == '__main__':
    unittest.main()
