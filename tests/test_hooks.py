import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Hooks(unittest.TestCase):
    def test_session_cwd_with_spaces_and_json_characters(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            project = parent / 'plugin-creo-memories'
            project.mkdir()
            lane = project / '.vp/lanes/a space'
            lane.mkdir(parents=True)
            binary = parent / 'bin'
            binary.mkdir()
            vp = binary / 'vp'
            vp.write_text('#!/bin/sh\nprintf \'%s\\t%s\\n\' "$PWD" \'quote" and back\\slash\'\n')
            vp.chmod(0o755)
            env = dict(os.environ, PATH=str(binary)+os.pathsep+os.environ['PATH'])
            env.pop('CLAUDE_PLUGIN_ROOT', None)
            is_vp = ROOT.name == 'plugin-vantage-point'
            target = lane if is_vp else project
            hook = ROOT / ('hooks/scripts/lane-status.sh' if is_vp else 'hooks/session-start.sh')
            result = subprocess.run(['bash',str(hook)],input=json.dumps({'cwd':str(target)}),text=True,cwd=parent,env=env,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            if is_vp:
                content=json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
                self.assertIn(str(lane),content)
                self.assertIn('quote" and back',content)
            else:
                self.assertIn('chronista-plugins',result.stdout)
                self.assertNotIn('remember / search の atlasId に',result.stdout)

    def test_invalid_event_is_quiet(self):
        hook=ROOT / ('hooks/scripts/lane-status.sh' if ROOT.name == 'plugin-vantage-point' else 'hooks/session-start.sh')
        result=subprocess.run(['bash',str(hook)],input='{bad',text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout,'')

@unittest.skipIf(ROOT.name == 'plugin-vantage-point', 'creo-memories の hook')
class CreoSessionHooks(unittest.TestCase):
    def run_start(self, source):
        with tempfile.TemporaryDirectory() as temp:
            env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
            env.pop('CLAUDE_PLUGIN_ROOT', None)
            r = subprocess.run(['bash', str(ROOT / 'hooks/session-start.sh')],
                               input=json.dumps({'cwd': temp, 'source': source}), text=True, env=env, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            return r.stdout

    def test_compact_prompts_a_handoff(self):
        # SessionStart の stdout は agent の context に入る。compaction の後は、要約を材料に handoff を書く番
        out = self.run_start('compact')
        self.assertIn("kind: 'handoff'", out)
        self.assertIn('縮みました', out)

    def test_other_starts_do_not_prompt_a_handoff(self):
        for source in ('startup', 'resume', 'clear'):
            self.assertNotIn('縮みました', self.run_start(source), source)

    def test_today_brain_is_not_the_project(self):
        # 「今日の脳」は既定の atlas の分。project の分は briefing({ atlasId }) で取る
        out = self.run_start('startup')
        self.assertIn('briefing({ atlasId })', out)
        self.assertNotIn('重複検索は不要', out)

    def test_no_hook_whose_output_never_reaches_the_agent(self):
        # PreCompact の stdout は debug log、Stop の systemMessage は人にだけ (Claude Code の hooks の文書)。
        # 「hook が思い出させる」と書いてあっても agent には届いていなかった
        hooks = json.loads((ROOT / 'hooks/hooks.json').read_text())['hooks']
        self.assertNotIn('PreCompact', hooks)
        self.assertNotIn('Stop', hooks)

if __name__ == '__main__':
    unittest.main()
