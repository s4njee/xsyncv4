#!/usr/bin/env python3
"""CVS listings retain each side's settings and validate global selections."""
import os
import shlex
import subprocess
import unittest

import difftest
import filter_diff_test as filters
import filter_cvs_test as cvs


class CvsListingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cvs.CvsDifferentials.setUpClass()

    def setUp(self):
        self.case = cvs.CvsDifferentials('test_local')
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)

    def test_listing_settings_and_validation(self):
        c = self.case
        for remote in (False, True):
            c.fixture(remote)
            before = difftest.snapshot(str(c.root))
            for flags, rules in ((['-C'], []), ([], ['-C']), ([], ['-Cr']), ([], ['-C/']),
                                 ([], ['+C', '- *']), ([], [': .rules']),
                                 ([], [': .missing', '!', '-C']), ([], [])):
                with self.subTest(remote=remote, flags=flags, rules=rules):
                    results = []
                    for native in (False, True):
                        server = ('/usr/local/bin/xsync' if filters.transfer.HOST else str(filters.transfer.BINARY)) if native else 'rsync'
                        command = [str(filters.transfer.BINARY) if native else filters.RSYNC, '-rl', *flags]
                        if native: command += ['--no-fallback']
                        command += ['--filter=' + rule for rule in rules]
                        source = str(c.root / 'src') + '/'
                        if remote:
                            source = (filters.transfer.HOST or 'fake') + ':' + source
                            command += ['-e', filters.transfer.RSH, '--rsync-path=' + shlex.join(
                                ['env', *[k + '=' + v for k, v in c.server_env.items()], server])]
                        result = subprocess.run(command + [source], capture_output=True, timeout=20,
                                                env=dict(c.env, TZ='UTC', LC_ALL='C'))
                        self.assertIn(result.returncode, (0, 4), result.stderr)
                        self.assertNotIn(b'falling back', result.stderr)
                        results.append(result)
                    self.assertEqual(results[0].returncode, results[1].returncode, results[1].stderr)
                    if results[0].returncode:
                        for result in results: self.assertIn(b'rejecting excluded file-list name', result.stderr)
                    else:
                        self.assertEqual(results[0].stdout, results[1].stdout)
                    self.assertEqual(difftest.snapshot(str(c.root)), before)


if __name__ == '__main__': unittest.main()
