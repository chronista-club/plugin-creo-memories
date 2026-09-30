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
case "$*" in *api/labels*) printf '%s' "$labels"; exit 0 ;; esac
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


if __name__ == '__main__':
    unittest.main()
