#!/usr/bin/env python3
"""Focused receiver trust checks using a deliberately hostile protocol peer."""
import ctypes
import ctypes.util
import os
import pathlib
import re
import select
import struct
import subprocess
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
BINARY = pathlib.Path(os.environ.get("XSYNC_TEST_BINARY", REPO / "build/xs")).resolve()
HEADER = (REPO / "src/common.h").read_text()
VERSION = int(re.search(r"PROTO_VERSION = (\d+)", HEADER)[1])
BOOLS = re.findall(r"X\((\w+)\)", HEADER.split("#define WIRE_V3_BOOL_OPTS(X)")[1].split("#define WIRE_V3_INT_OPTS(X)")[0])
INTS = re.findall(r"X\((\w+)\)", HEADER.split("#define WIRE_V3_INT_OPTS(X)")[1].split("#define BOOL_OPTS(X)")[0])


def var(value):
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    return bytes(result + bytes([value]))


def string(value):
    if isinstance(value, str):
        value = value.encode()
    return var(len(value)) + value


def frame(kind, payload):
    return struct.pack("<IB", len(payload), kind) + payload


def directory(entries=(), rel="", ident=0, parent=0, index=0):
    body = string(rel) + var(0o755) + b"\0" * 4 + var(len(entries))
    for name, kind, extra in entries:
        body += string(name) + bytes([kind]) + var(0o644) + b"\0\0" + extra
    return frame(2, var(ident) + var(parent) + var(index) + b"\1" + body)


def read_frame(proc):
    def exact(size):
        data = b""
        while len(data) < size:
            if not select.select([proc.stdout], [], [], 10)[0]:
                raise AssertionError("receiver did not answer")
            part = os.read(proc.stdout.fileno(), size - len(data))
            if not part:
                raise AssertionError("receiver closed before the expected frame")
            data += part
        return data
    length, kind = struct.unpack("<IB", exact(5))
    return kind, exact(length)


class ReceiverTrustTests(unittest.TestCase):
    def test_malformed_output_configuration(self):
        for kind, config in ((12, b'\0\0'), (12, b'\0' * 5), (12, b'\0\0\2\0'), (2, b'')):
            with self.subTest(kind=kind, config=config), tempfile.TemporaryDirectory() as tmp:
                target = pathlib.Path(tmp) / 'uncreated'
                options = bytes(name in ('recursive', 'itemize') for name in BOOLS)
                options += b''.join(var(1 if name == 'max_delete' else 2 if name == 'jobs' else 0) for name in INTS)
                hello = b'XSYNC\1' + var(VERSION) + b'R' + var(97) + options + b'\0\1' + string(str(target))
                proc = subprocess.Popen([str(BINARY), '--server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    proc.stdin.write(frame(1, hello)); proc.stdin.flush()
                    self.assertEqual(read_frame(proc)[0], 1)
                    proc.stdin.write(frame(kind, config)); proc.stdin.flush()
                    message_kind, message = read_frame(proc)
                    self.assertEqual(message_kind, 8)
                    self.assertEqual(message[:2], b'\2\2')
                    self.assertIn(b'output configuration', message)
                    proc.communicate(timeout=10)
                    self.assertEqual(proc.returncode, 2)
                    self.assertFalse(target.exists())
                finally:
                    if proc.poll() is None: proc.kill()
                    proc.communicate()

    def test_hostile_paths(self):
        cases = ("dot", "dotdot", "slash", "nul_name", "nul_target", "root_path", "child_path", "duplicate_root", "nonzero_root", "unrequested_data")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = pathlib.Path(tmp)
                dst, outside = root / "dst", root / "outside"
                dst.mkdir()
                outside.mkdir()
                (outside / "file").write_bytes(b"untouched")
                options = bytes(name in ("recursive", "links", "perms", "safe_links") for name in BOOLS)
                options += b"".join(var(1 if name == "max_delete" else 2 if name == "jobs" else 0) for name in INTS)
                hello = b"XSYNC\1" + var(VERSION) + b"R" + (var(15) if VERSION >= 4 else b'') + options + b"\0\1" + string(str(dst))
                proc = subprocess.Popen([str(BINARY), "--server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    proc.stdin.write(frame(1, hello))
                    proc.stdin.flush()
                    for _ in range(2):
                        kind, payload = read_frame(proc)
                        self.assertIn(kind, (1, 10))
                    if case in ("dot", "dotdot", "slash", "nul_name"):
                        name = {"dot": ".", "dotdot": "..", "slash": "../outside/file", "nul_name": b"file\0evil"}[case]
                        bad = directory([(name, 1, b"\0")])
                    elif case == "nul_target":
                        bad = directory([("link", 3, string(b"target\0evil"))])
                    elif case == "root_path":
                        bad = directory(rel="../outside")
                    elif case == "nonzero_root":
                        bad = directory(ident=1)
                    else:
                        entry = ("hot", 2, b"\0") if case == "child_path" else ("link", 3, string("../outside/file"))
                        proc.stdin.write(directory([entry]))
                        proc.stdin.flush()
                        while read_frame(proc)[0] != 3:
                            pass
                        if case == "child_path":
                            bad = directory(rel="../outside", ident=1, parent=1)
                        elif case == "duplicate_root":
                            bad = directory()
                        else:
                            raw = b"\0\0\4"  # R_FAIL for a link that was never requested.
                            lib = ctypes.CDLL(ctypes.util.find_library("xxhash"))
                            lib.XXH3_64bits.argtypes = (ctypes.c_void_p, ctypes.c_size_t)
                            lib.XXH3_64bits.restype = ctypes.c_uint64
                            bad = frame(4, b"\0" + struct.pack("<Q", lib.XXH3_64bits(raw, len(raw))) + raw)
                    proc.stdin.write(bad)
                    proc.stdin.flush()
                    self.assertEqual(proc.wait(timeout=10), 2)
                    self.assertEqual((outside / "file").read_bytes(), b"untouched")
                    self.assertEqual(sorted(p.name for p in outside.iterdir()), ["file"])
                finally:
                    if proc.poll() is None:
                        proc.kill()
                    proc.stdin.close()
                    proc.stdout.close()
                    proc.stderr.close()
                    proc.wait()


if __name__ == "__main__":
    unittest.main()
