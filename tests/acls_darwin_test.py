#!/usr/bin/env python3
"""Preserve the complete Darwin ACL, including fields omitted by rsync's shim."""
import ctypes
import os
from pathlib import Path
import shlex
import subprocess
import unittest

import acls_test as acl
import output_test as transfer
from xattrs_test import DARWIN

LIBC = acl.LIBC
if DARWIN:
    LIBC.acl_from_text.argtypes = (ctypes.c_char_p,)
    LIBC.acl_from_text.restype = ctypes.c_void_p
    LIBC.acl_get_entry.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))
    LIBC.acl_get_flagset_np.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
    LIBC.acl_add_flag_np.argtypes = (ctypes.c_void_p, ctypes.c_int)
    LIBC.acl_set_flagset_np.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    LIBC.acl_set_permset_mask_np.argtypes = (ctypes.c_void_p, ctypes.c_uint64)
    LIBC.acl_set_link_np.argtypes = (ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)

UUID = '01234567-89AB-CDEF-0012-3456789ABCDE'
VARIANTS = ('synchronize', 'all_permissions', 'no_inherit', 'defer_inherit',
            'inherited', 'file_inherit', 'directory_inherit', 'limit_inherit',
            'only_inherit', 'all_entry_flags', 'uuid_allow', 'uuid_deny')


def set_variant(path, variant):
    acl.set_acl(path)
    value = LIBC.acl_get_link_np(os.fsencode(path), 256)
    if not value: raise OSError(ctypes.get_errno(), 'get ACL')
    try:
        if variant.startswith('uuid_'):
            LIBC.acl_free(value)
            action = 'allow' if variant == 'uuid_allow' else 'deny'
            value = LIBC.acl_from_text(('!#acl 1\nuser:' + UUID + ':::' + action + ':readattr\n').encode())
            if not value: raise OSError(ctypes.get_errno(), 'parse UUID ACL')
        elif variant in ('no_inherit', 'defer_inherit'):
            flags = ctypes.c_void_p()
            if LIBC.acl_get_flagset_np(value, ctypes.byref(flags)): raise OSError(ctypes.get_errno(), 'ACL flags')
            flag = 1 << 17 if variant == 'no_inherit' else 1
            if LIBC.acl_add_flag_np(flags, flag) or LIBC.acl_set_flagset_np(value, flags): raise OSError(ctypes.get_errno(), 'set ACL flags')
        else:
            entry = ctypes.c_void_p()
            if LIBC.acl_get_entry(value, 0, ctypes.byref(entry)): raise OSError(ctypes.get_errno(), 'ACL entry')
            if variant in ('synchronize', 'all_permissions'):
                permissions = (128 if variant == 'synchronize' else 0x3ffe) | (1 << 20)
                if LIBC.acl_set_permset_mask_np(entry, permissions): raise OSError(ctypes.get_errno(), 'ACL permissions')
            else:
                bits = {'inherited': 16, 'file_inherit': 32, 'directory_inherit': 64,
                        'limit_inherit': 32 | 64 | 128, 'only_inherit': 32 | 64 | 256,
                        'all_entry_flags': 0x1f0}[variant]
                flags = ctypes.c_void_p()
                if LIBC.acl_get_flagset_np(entry, ctypes.byref(flags)): raise OSError(ctypes.get_errno(), 'entry flags')
                for bit in (16, 32, 64, 128, 256):
                    if bits & bit and LIBC.acl_add_flag_np(flags, bit): raise OSError(ctypes.get_errno(), 'add entry flag')
                if LIBC.acl_set_flagset_np(entry, flags): raise OSError(ctypes.get_errno(), 'set entry flags')
        if LIBC.acl_set_link_np(os.fsencode(path), 256, value): raise OSError(ctypes.get_errno(), 'write ACL')
    finally:
        if value: LIBC.acl_free(value)


@unittest.skipUnless(DARWIN, 'Darwin ACL flags and UUID principals')
class DarwinAclTests(acl.AclDifferentials):
    # Use the shared fixture setup, but do not rerun inherited test methods.
    test_local_acl_metadata_and_data_paths = None
    test_clone_acl_metadata_and_data_paths = None
    test_mode_only_updates_do_not_itemize_acl_changes = None
    test_native_push_pull_acl_metadata_and_data_paths = None
    test_acls_and_hardlinks_across_directories = None
    test_acl_storage_failure_after_xattrs_preserves_existing_files = None
    test_readonly_directories_and_repeat_sync = None

    def check_complete_acl(self, variant, direction, clone=False, metadata_only=False):
        self.fixture(inherited=False)
        source, target = self.root / 'src', self.root / 'dst'
        for name in ('', 'same', 'changed'):
            set_variant(source / name, variant)
        if metadata_only:
            (target / 'changed').write_bytes((source / 'changed').read_bytes())
            os.utime(target / 'changed', ns=(1500000000000000000, 1500000000000000000))
        before = acl.snapshot(source)
        root_acl = acl.get_acl(source)
        command = [str(transfer.BINARY), '--no-fallback', '-aAi', '-j8']
        if not clone: command += ['--no-clone']
        a, b = str(source) + '/', str(target) + '/'
        if direction != 'local':
            command += ['-e', transfer.RSH, '--rsync-path=' + shlex.quote(str(transfer.BINARY))]
            if direction == 'push': b = 'fake:' + b
            else: a = 'fake:' + a
        for repeat in (False, True):
            result = subprocess.run(command + [a, b], capture_output=True, timeout=30,
                                    env=dict(os.environ, XSYNC_CONFIG='', XSYNC_OPTS=''))
            self.assertEqual(result.returncode, 0, (variant, direction, result.stdout, result.stderr))
            self.assertEqual(acl.snapshot(source), before)
            self.assertEqual(acl.get_acl(source), root_acl)
            self.assertEqual(acl.get_acl(target), root_acl)
            for name in ('same', 'changed'):
                self.assertEqual(acl.get_acl(target / name), before[name]['acl'])
            self.assertEqual((target / 'changed').read_bytes(), (source / 'changed').read_bytes())
            if repeat: self.assertEqual(result.stdout, b'')
            elif metadata_only: self.assertIn(b'.f.......a.', result.stdout)

    def test_complete_flags_and_uuid_principals(self):
        for variant in VARIANTS:
            for direction in ('local', 'push', 'pull'):
                for metadata in (False, True):
                    with self.subTest(variant=variant, direction=direction, metadata=metadata):
                        self.check_complete_acl(variant, direction, metadata_only=metadata)

    def test_clone_preserves_complete_flags_and_uuid_principals(self):
        for variant in VARIANTS:
            with self.subTest(variant=variant): self.check_complete_acl(variant, 'local', clone=True)


if __name__ == '__main__': unittest.main()
