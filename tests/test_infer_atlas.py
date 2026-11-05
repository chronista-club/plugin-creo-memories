from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/infer-atlas.sh'


def infer(dir_name: str) -> str:
    # git repo ではない dir で走らせ、dir 名から推定させる (継いだ GIT_* で本物の repo を触らない)
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / dir_name
        target.mkdir()
        result = subprocess.run(['bash', str(SCRIPT), str(target)], text=True, capture_output=True, env=env)
        return result.stdout.strip()


class InferAtlas(unittest.TestCase):
    def test_repo_name_matching_the_atlas_passes_through(self):
        # 2026-11-04: Atlas を creoui → creo-ui に改名 (slug も)。repo 名と同じなので alias は要らない
        self.assertEqual(infer('creo-ui'), 'creo-ui')

    def test_old_directory_name_maps_to_the_renamed_atlas(self):
        self.assertEqual(infer('creoui'), 'creo-ui')

    def test_unknown_repo_name_is_returned_as_is(self):
        self.assertEqual(infer('ghost-repo'), 'ghost-repo')


if __name__ == '__main__':
    unittest.main()
