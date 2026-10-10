#!/usr/bin/env python3
"""Exercise pinned relative operations, root boundaries, swaps and thread lifetime."""
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class DestinationScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory(prefix='xs-destination-scope-')
        cls.binary = pathlib.Path(cls.build.name) / 'scope-test'
        subprocess.run(['c++', '-std=c++20', '-pthread', '-I' + str(ROOT / 'src'),
                        str(ROOT / 'tests/destination_scope_test.cpp'),
                        str(ROOT / 'src/destination.cpp'), '-o', str(cls.binary)],
                       check=True, capture_output=True, timeout=60)

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def exercise(self, name):
        with tempfile.TemporaryDirectory(prefix='xs-destination-scope-case-') as root:
            result = subprocess.run([str(self.binary), root, name], capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_nested_pins_restore_the_previous_directory(self): self.exercise('nested')
    def test_symlinks_and_parent_paths_cannot_escape(self): self.exercise('escape')
    def test_renamed_directory_does_not_follow_replacement(self): self.exercise('swap')
    def test_workers_keep_independent_pins(self): self.exercise('threads')
    def test_descriptors_are_bounded_by_active_scopes(self): self.exercise('descriptors')
    def test_lexical_aliases_and_changed_cwd(self): self.exercise('normalization')
    def test_filesystem_root_anchor(self): self.exercise('root-anchor')
    def test_inherited_parent_survives_scope_and_rejects_symlinks(self): self.exercise('inherited')
    def test_inherited_parent_boundaries_and_normalization(self): self.exercise('inherited-boundaries')
    def test_parent_capability_survives_worker_handoff(self): self.exercise('inherited-thread')
    def test_retained_parent_budget_and_fallback(self): self.exercise('parent-budget')
    def test_low_descriptor_limit_preserves_uncached_operations(self): self.exercise('parent-low-limit')


if __name__ == '__main__':
    unittest.main()
