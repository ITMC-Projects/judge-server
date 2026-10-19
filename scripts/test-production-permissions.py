"""Filesystem permission regression tests; run on Linux for real chmod semantics."""
import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('judge_permissions', ROOT / 'production/validate.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class PermissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'config').mkdir()
        self.problems = self.root / 'custom problems'
        self.problems.mkdir()
        self.env = self.root / 'judge.env'
        self.env.write_text('DMOJ_JUDGE_KEY=keep-existing-secret\nOJ_PROBLEMS_DIR=' + self.problems.as_posix() + '\n')
        self.config = self.root / 'config/judge.yml'
        self.config.write_text('problem_storage_globs: [/problems/**/]\n')

    def tearDown(self):
        self.tmp.cleanup()

    @unittest.skipIf(os.name == 'nt', 'Requires POSIX permission bits')
    def test_repairs_permissions_preserves_content_and_never_recurses(self):
        child = self.problems / 'private-child'
        child.mkdir(mode=0o700)
        self.problems.chmod(0o700)
        self.config.chmod(0o600)
        self.env.chmod(0o644)
        before = self.env.read_bytes(), self.config.read_bytes()
        validator.prepare_permissions(self.root)
        validator.prepare_permissions(self.root)
        self.assertEqual(stat.S_IMODE(self.problems.stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o644)
        self.assertEqual(stat.S_IMODE(self.env.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(child.stat().st_mode), 0o700)
        self.assertEqual(before, (self.env.read_bytes(), self.config.read_bytes()))

    def test_missing_problems_optional_during_init_required_at_start(self):
        self.problems.rmdir()
        validator.prepare_permissions(self.root, require_problems=False)
        self.assertFalse(self.problems.exists())
        with self.assertRaisesRegex(ValueError, 'missing'):
            validator.prepare_permissions(self.root)

    def test_permission_failure_has_actionable_error(self):
        with patch.object(validator.stat, 'S_IMODE', return_value=0), \
                patch.object(Path, 'chmod', side_effect=PermissionError('denied')):
            with self.assertRaisesRegex(ValueError, 'Cannot set 600 permissions.*as its owner'):
                validator.prepare_permissions(self.root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
