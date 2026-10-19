"""Static judge deployment tests; Docker CLI required, daemon not required."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('judge_prod_validate', ROOT / 'production/validate.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
BASH = os.environ.get('BASH_BIN', 'bash')


class JudgeProductionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'judge-server'
        shutil.copytree(ROOT / 'production', self.root / 'production',
                        ignore=shutil.ignore_patterns('judge.env', 'judge.yml', '__pycache__'))
        (self.root / 'scripts').mkdir()
        shutil.copy(ROOT / 'scripts/prod.sh', self.root / 'scripts/prod.sh')
        self.p = self.root / 'production'
        (self.root.parent / 'ITMC-OJ-docker/dmoj/production/data/problems').mkdir(parents=True)
        self.init()

    def tearDown(self):
        self.tmp.cleanup()

    def init(self):
        env = dict(os.environ, JUDGE_TEST_PYTHON=Path(sys.executable).as_posix())
        subprocess.run([BASH, '-c', 'python3(){ "$JUDGE_TEST_PYTHON" "$@"; }; export -f python3; bash scripts/prod.sh prod-init'],
                       cwd=self.root, env=env, capture_output=True, check=True)

    def test_init_preserves_key_and_custom_config(self):
        values = validator.read(self.p / 'judge.env')
        self.assertEqual(len(values['DMOJ_JUDGE_KEY']), 64)
        self.assertGreaterEqual(len(set(values['DMOJ_JUDGE_KEY'])), 8)
        env = (self.p / 'judge.env').read_bytes()
        config = self.p / 'config/judge.yml'
        config.write_text(config.read_text() + '# keep custom configuration\n')
        before = config.read_bytes()
        self.init()
        self.assertEqual((self.p / 'judge.env').read_bytes(), env)
        self.assertEqual(config.read_bytes(), before)
        validator.validate(self.p)

    def test_reject_invalid_settings(self):
        file = self.p / 'judge.env'
        original = file.read_text()
        key = validator.read(file)['DMOJ_JUDGE_KEY']
        for old, new, message in [(key, 'a' * 64, 'strong'), (key, 'replace-with-key', 'placeholder'),
                                  ('OJ_BRIDGE_PORT=9999', 'OJ_BRIDGE_PORT=0', 'PORT')]:
            file.write_text(original.replace(old, new))
            with self.assertRaisesRegex(ValueError, message):
                validator.validate(self.p)
        file.write_text(original.replace('OJ_PROBLEMS_DIR=', 'OJ_PROBLEMS_DIR=/missing/'))
        with self.assertRaisesRegex(ValueError, 'absolute directory'):
            validator.validate(self.p)

    def test_compose_production_contract(self):
        result = subprocess.run(['docker', 'compose', '-p', 'itmc-oj-judge', '--env-file', str(self.p / 'judge.env'),
                                 '-f', str(self.p / 'compose.yml'), 'config', '--format', 'json'],
                                check=True, capture_output=True, text=True)
        cfg = json.loads(result.stdout)
        judge = cfg['services']['judge']
        self.assertFalse(judge.get('ports'))
        self.assertEqual(judge['image'], 'itmc-oj-prod/judge:local')
        self.assertEqual(judge['command'][1], 'itmc-oj-prod-bridged')
        self.assertEqual(judge['restart'], 'unless-stopped')
        self.assertEqual(cfg['networks']['oj']['name'], 'itmc-oj-prod_db')
        self.assertTrue(cfg['networks']['oj']['external'])
        mounts = {v['target']: v for v in judge['volumes']}
        self.assertEqual(set(mounts), {'/problems', '/judge/.docker/judge.yml'})
        self.assertTrue(all(v['read_only'] and not v['bind']['create_host_path'] for v in mounts.values()))
        self.assertIn('production', mounts['/problems']['source'])
        self.assertEqual(judge['logging']['options']['max-size'], '10m')
        self.assertEqual(set(judge['environment']), {'DMOJ_JUDGE_NAME', 'DMOJ_JUDGE_KEY'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
