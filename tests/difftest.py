#!/usr/bin/env python3
"""Differential test harness for xsync (an rsync clone).

Every case builds the same deterministic fixture twice (a source tree and,
optionally, a pre-existing destination tree), runs the reference rsync on one
copy and the binary under test on the other with identical arguments and an
identical relative layout / cwd, and then compares the two resulting trees
(paths, file types, contents, symlink targets, permission bits, mtimes in
nanoseconds, hard-link grouping) and the two exit codes.

    python3 tests/difftest.py [--xsync PATH] [--rsync PATH] [--keep]
                              [-k SUBSTR] [-v] [--list] [--timeout SECS]
                              [--no-symlink-times] [--no-symlink-modes]

Exit status: 0 all cases passed, 1 at least one FAIL/ERROR, 2 setup problem
(e.g. the xsync binary has not been built).  FAIL means the tool under test
differs from rsync; ERROR means the case or the harness itself is broken
(the reference rsync did not do what the case expects).

Notes on how trees are compared
  * The whole per-case sandbox is compared, not just the destination, so a
    tool that modifies its source, writes through a symlink to somewhere
    outside the destination, or leaves stray temp files behind is caught.
  * Fixture mtimes are always explicit and far from "now".  An mtime that a
    tool leaves at the current time (no -t, -O, -J, a freshly created parent
    directory...) cannot be compared exactly, so any mtime that falls inside
    the window of the current case is normalised to the token <now>.  Both
    tools must then agree on "preserved value X" versus "<now>".
  * A case can opt out of individual attributes with skip={...}; the names
    are the ones printed in the diff: mode, mtime, dir-mtime, symlink-mtime,
    symlink-mode, hardlinks.

Only the python3 standard library is used.
"""

import argparse
import calendar
import concurrent.futures
import hashlib
import os
import random
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DEFAULT_XSYNC = os.path.join(REPO, "build", "xsync")
DEFAULT_RSYNC = "/opt/homebrew/bin/rsync"
FAKESSH = os.path.join(HERE, "fakessh.sh")

MAX_DIFF_LINES = 20
STEP_TIMEOUT = 30   # default seconds allowed per tool invocation
MB = 1024 * 1024

# Attributes that are compared unless a case (or a command-line switch) opts
# out.  These are also the labels used in the diff output.
ALL_ATTRS = ("mode", "mtime", "dir-mtime", "symlink-mtime", "symlink-mode",
             "hardlinks")


# --------------------------------------------------------------------------
# Deterministic fixture construction
# --------------------------------------------------------------------------

def T(year, month=1, day=1, hour=0, minute=0, second=0, ns=0):
    """UTC calendar time -> integer nanoseconds since the epoch."""
    return calendar.timegm((year, month, day, hour, minute, second)) * 10**9 + ns


def auto_mtime(rel):
    """Deterministic mtime for a fixture path.

    The first path component is ignored, so `src/a/b` and `dst/a/b` get the
    same time: a destination built with the same function as the source is
    automatically "already in sync".  About three quarters of the paths get
    non-zero nanoseconds.
    """
    key = rel.split("/", 1)[1] if "/" in rel else ""
    c = zlib.crc32(key.encode("utf-8", "surrogateescape"))
    sec = 1_500_000_000 - (c % (5 * 365 * 86400))         # 2012 .. 2017
    nsec = 0 if c % 4 == 0 else (c * 2654435761) % 1_000_000_000
    return sec * 10**9 + nsec


_BIG_CACHE = {}


def rnd(seed, n):
    """n pseudo-random (incompressible) bytes, deterministic for a seed."""
    if n >= MB:
        if (seed, n) not in _BIG_CACHE:
            _BIG_CACHE[(seed, n)] = random.Random(seed).randbytes(n)
        return _BIG_CACHE[(seed, n)]
    return random.Random(seed).randbytes(n)


_WORDS = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet "
          "kilo lima mike november oscar papa quebec romeo sierra tango "
          "uniform victor whiskey xray yankee zulu").split()


def text(seed, n):
    """n bytes of deterministic ASCII text."""
    r = random.Random(seed)
    out, size = [], 0
    while size < n:
        line = " ".join(r.choice(_WORDS) for _ in range(r.randint(3, 12))) + "\n"
        out.append(line)
        size += len(line)
    return "".join(out).encode("ascii")[:n]


def compressible(n):
    """n bytes of highly compressible data (still not a single repeated block)."""
    key = ("z", n)
    if key not in _BIG_CACHE:
        pat = (b"All work and no play makes rsync a dull tool. " * 100)[:4086]
        blocks = []
        for i in range(n // 4096 + 1):
            blocks.append(pat + b"%09d\n" % i)
        _BIG_CACHE[key] = b"".join(blocks)[:n]
    return _BIG_CACHE[key]


class Tree:
    """Builds a fixture below `root`.  Call done() when finished.

    Every path gets an explicit mtime (auto_mtime() unless given).  Directory
    modes and mtimes are applied in done(), after all children exist.
    """

    def __init__(self, root):
        self.root = root
        self.dirs = {}          # rel -> [mode, mtime_ns]

    def _p(self, rel):
        return os.path.join(self.root, rel)

    def _parents(self, rel):
        parent = os.path.dirname(rel)
        if parent:
            self.d(parent, _implicit=True)

    def d(self, rel, mode=None, mtime=None, _implicit=False):
        rel = rel.rstrip("/")
        if rel not in self.dirs:
            self._parents(rel)
            os.mkdir(self._p(rel))
            self.dirs[rel] = [0o755, auto_mtime(rel)]
        if not _implicit:
            if mode is not None:
                self.dirs[rel][0] = mode
            if mtime is not None:
                self.dirs[rel][1] = mtime
        return self

    def f(self, rel, data=b"", mode=0o644, mtime=None):
        self._parents(rel)
        p = self._p(rel)
        if os.path.lexists(p):          # allow a builder to override a file
            os.chmod(p, 0o600)
            os.unlink(p)
        with open(p, "wb") as fh:
            fh.write(data)
        os.chmod(p, mode)
        m = auto_mtime(rel) if mtime is None else mtime
        os.utime(p, ns=(m, m))
        return self

    def ln(self, rel, target, mtime=None, mode=None):
        self._parents(rel)
        p = self._p(rel)
        if os.path.lexists(p):
            os.unlink(p)
        os.symlink(target, p)
        if mode is not None and hasattr(os, "lchmod"):    # macOS/BSD only
            os.lchmod(p, mode)
        m = auto_mtime(rel) if mtime is None else mtime
        os.utime(p, ns=(m, m), follow_symlinks=False)
        return self

    def fifo(self, rel, mode=0o644, mtime=None):
        self._parents(rel)
        p = self._p(rel)
        os.mkfifo(p)
        os.chmod(p, mode)
        m = auto_mtime(rel) if mtime is None else mtime
        os.utime(p, ns=(m, m))
        return self

    def hl(self, rel, existing):
        """Hard link rel -> existing (shares inode, mode and mtime)."""
        self._parents(rel)
        os.link(self._p(existing), self._p(rel))
        return self

    def done(self):
        for rel, (mode, _) in self.dirs.items():
            os.chmod(self._p(rel), mode)
        for rel, (_, mtime) in self.dirs.items():
            os.utime(self._p(rel), ns=(mtime, mtime))


# ---- fixture builders ----------------------------------------------------

def B(*builders):
    """Compose fixture builders."""
    def build(t):
        for b in builders:
            b(t)
    return build


def mkdirs(*rels):
    def build(t):
        for r in rels:
            t.d(r)
    return build


def under(builder, top):
    return lambda t: builder(t, top)


def basic(t, top="src"):
    """A small tree with a bit of everything that needs no special handling."""
    p = lambda s: top + "/" + s
    t.f(p("a.txt"), text(1, 300))
    t.f(p("b.bin"), rnd(2, 5000))
    t.f(p("empty"), b"")
    t.f(p("exec.sh"), b"#!/bin/sh\necho hi\n", mode=0o755)
    t.f(p("ro.txt"), b"read only\n", mode=0o444)
    t.f(p(".hidden"), b"hidden\n")
    t.f(p("sub/c.txt"), text(3, 1200))
    t.f(p("sub/deep/d.txt"), text(4, 70000))
    t.f(p("sub/.dotdir/x"), b"x\n")
    t.d(p("emptydir"))
    t.d(p("sub/emptysub"), mode=0o750)
    t.ln(p("link_to_file"), "a.txt")
    t.ln(p("link_to_dir"), "sub")
    t.ln(p("sub/up_link"), "../b.bin")
    t.ln(p("dangling"), "no/such/target")
    t.ln(p("abs_link"), "/etc/hosts")
    t.f(p("old.txt"), b"old\n", mtime=T(1985, 10, 26, 1, 21, 0))
    t.f(p("ns.txt"), b"ns\n", mtime=T(2009, 2, 13, 23, 31, 30, 123456789))
    t.d(p("sub"), mtime=T(2011, 11, 11, 11, 11, 11, 111111111))


def plain(t, top="src"):
    """Regular files and directories only (no symlinks or odd modes)."""
    p = lambda s: top + "/" + s
    t.f(p("a.txt"), text(1, 300))
    t.f(p("b.bin"), rnd(2, 5000))
    t.f(p("empty"), b"")
    t.f(p("sub/c.txt"), text(3, 1200))
    t.f(p("sub/deep/d.txt"), text(4, 70000))
    t.d(p("emptydir"))


T1 = T(2015, 3, 1, 12, 0, 0, 500)
T2 = T(2016, 6, 2, 8, 30, 15, 250000000)


def upd(t, s="src", d="dst"):
    """Source plus an out-of-date destination covering every skip/transfer
    decision rsync makes."""
    S = lambda x: s + "/" + x
    D = lambda x: d + "/" + x
    for top in (s, d):                                   # already in sync
        t.f(top + "/same.txt", text(10, 500))
        t.f(top + "/sub/same2.txt", text(11, 900))
        t.f(top + "/sub/keepdir/k.txt", text(9, 200))
    # content, size and mtime all changed (dest older)
    t.f(S("changed.txt"), text(12, 800), mtime=T2)
    t.f(D("changed.txt"), text(13, 600), mtime=T1)
    # same size, different content, different mtime
    t.f(S("samesize_diffmtime.bin"), rnd(14, 4096), mtime=T2)
    t.f(D("samesize_diffmtime.bin"), rnd(15, 4096), mtime=T1)
    # identical content, only the mtime differs
    t.f(S("touched.txt"), text(16, 400), mtime=T2)
    t.f(D("touched.txt"), text(16, 400), mtime=T1)
    # different size, same mtime
    t.f(S("diffsize_samemtime.txt"), text(17, 700), mtime=T1)
    t.f(D("diffsize_samemtime.txt"), text(17, 650), mtime=T1)
    # same size and mtime, different content: invisible to the quick check
    t.f(S("sneaky.bin"), rnd(18, 3000), mtime=T1)
    t.f(D("sneaky.bin"), rnd(19, 3000), mtime=T1)
    # destination is newer than the source
    t.f(S("dest_newer.txt"), text(20, 300), mtime=T1)
    t.f(D("dest_newer.txt"), text(21, 350), mtime=T2)
    # only the mode differs
    t.f(S("mode_only.sh"), b"#!/bin/sh\n", mode=0o755, mtime=T1)
    t.f(D("mode_only.sh"), b"#!/bin/sh\n", mode=0o600, mtime=T1)
    # a multi-block file with a small edit in the middle (delta transfer)
    blob = bytearray(rnd(22, 300000))
    t.f(S("blob.bin"), bytes(blob), mtime=T2)
    blob[150000:150040] = b"x" * 40
    del blob[20000:20500]
    t.f(D("blob.bin"), bytes(blob), mtime=T1)
    # new in the source
    t.f(S("new.txt"), text(23, 250))
    t.f(S("newdir/n1.txt"), text(24, 100))
    t.d(S("newdir/emptynew"))
    t.f(S("sub/new_in_sub.txt"), text(25, 60))
    # only in the destination
    t.f(D("extra.txt"), text(26, 120))
    t.f(D("extra_dir/e1.txt"), text(27, 80))
    t.f(D("extra_dir/nested/e2.txt"), text(28, 80))
    t.d(D("extra_empty"))
    t.ln(D("extra_link"), "extra.txt")
    t.ln(D("extra_dangling"), "nowhere")
    t.f(D("sub/extra_in_sub.txt"), text(29, 90))
    # symlink whose target changed, and one that is already right
    t.ln(S("lnk"), "same.txt")
    t.ln(D("lnk"), "changed.txt")
    t.ln(S("lnk_same"), "same.txt")
    t.ln(D("lnk_same"), "same.txt")
    # directory whose mode and mtime differ
    t.d(S("sub"), mode=0o755, mtime=T2)
    t.d(D("sub"), mode=0o700, mtime=T1)


FILT_FILES = (
    "a.txt a.log foo foo.txt notes.md core x.tmp .gitignore "
    "sub/b.txt sub/b.log sub/foo sub/y.tmp sub/build "
    "sub/deep/c.txt sub/deep/c.o sub/deep/foo/inner.txt "
    "build/out.o build/keep.txt cache/x.dat sub/cache/top.txt "
    "sub/cache/y/z.txt tmp/t1 docs/readme.txt docs/img/pic.png "
    "docs/img/raw/pic.txt .git/config a/z.txt a/b/other.txt a/b/c/z.txt "
    "foo.d/in.txt logs/only.log"
).split()


def filt(t, top="src"):
    """Names chosen to tell rsync's filter-rule forms apart: `foo` exists as a
    top-level file, a nested file and a nested directory; `build` is a
    directory at the top and a plain file in sub/."""
    for i, rel in enumerate(FILT_FILES):
        t.f(top + "/" + rel, text(100 + i, 40 + 13 * i))
    t.d(top + "/emptydir")


def filt_dst(t):
    """A destination for the --delete + filter cases."""
    filt(t, "dst")
    for i, rel in enumerate(("stale.txt stale.log sub/old.log sub/old.txt "
                             "logs_only/x.log logs_only/deep/y.log "
                             "gone/g.txt gone/g.log tmp/stale_t "
                             "build/stale.o").split()):
        t.f("dst/" + rel, text(200 + i, 50), mtime=T1 + i)


def multi(t):
    t.f("src1/a.txt", text(40, 100))
    t.f("src1/sub/x.txt", text(41, 100))
    t.f("src1/common.txt", b"from src1\n")
    t.ln("src1/lnk", "a.txt")
    t.f("src2/b.txt", text(42, 100))
    t.f("src2/sub/y.txt", text(43, 100))
    t.f("src2/common.txt", b"from src2, longer\n")
    t.d("src2/empty")
    t.f("loose.txt", text(44, 100))
    t.d("dst")


WEIRD_NAMES = [
    "with space.txt", "it's \"quoted\".txt", "naïve-文件.txt",
    "-leading-dash.txt", "--double-dash", ".dotfile", "..twodots", "...",
    "new\nline.txt", "tab\there.txt", "back\\slash.txt", "star*glob?.txt",
    "[bracket].txt", "semi;colon&amp.txt", "$dollar`tick`.txt", "#hash",
    "~tilde", " leading space", "trailing space ", "percent%s%d.txt",
    "Ünïcödé dir/ファイル",
    "dir with space/inner file.txt", "dir with space/sub dir/x y z",
    "-dashdir/-f", ".dotdir/.inner", "emoji-\U0001f642.txt",
    "colon:name", "equals=sign", "comma,name", "bang!", "paren(s)", "{brace}",
    "a" * 200 + ".long",
]


def weird(t, top="src"):
    for i, name in enumerate(WEIRD_NAMES):
        t.f(top + "/" + name, text(300 + i, 20 + i))
    t.ln(top + "/link with space", "with space.txt")
    t.d(top + "/empty dir with space")


FILE_MODES = (0o600, 0o644, 0o755, 0o444, 0o400, 0o664, 0o640, 0o700, 0o711,
              0o666, 0o777, 0o4755, 0o500)


def modes(t, top="src"):
    p = lambda s: top + "/" + s
    for m in FILE_MODES:
        t.f(p("f%04o" % m), b"mode %04o\n" % m, mode=m)
    t.f(p("ro_dir/inside.txt"), b"inside\n")
    t.f(p("ro_dir/exec"), b"#!/bin/sh\n", mode=0o555)
    t.f(p("ro_dir/sub/deeper.txt"), b"deeper\n", mode=0o444)
    t.d(p("ro_dir"), mode=0o555)
    t.d(p("ro_dir/sub"), mode=0o555)
    t.f(p("private/secret"), b"secret\n", mode=0o600)
    t.d(p("private"), mode=0o700)
    t.d(p("open"), mode=0o777)
    t.d(p("sticky"), mode=0o1777)
    t.d(p("group_w"), mode=0o775)


def modes_dst_different(t):
    """Destination with the same content/mtimes as modes() but other modes."""
    for m in FILE_MODES:
        t.f("dst/f%04o" % m, b"mode %04o\n" % m, mode=0o640)
    t.f("dst/private/secret", b"secret\n", mode=0o644)
    t.d("dst/private", mode=0o755)
    t.d("dst/open", mode=0o700)


def setgid(t):
    t.f("src/sg/file.txt", b"in setgid dir\n")
    t.f("src/sg/sub/file2.txt", b"nested\n", mode=0o664)
    t.d("src/sg", mode=0o2775)
    t.d("src/sg/sub", mode=0o2750)
    t.d("src/plain")
    t.d("dst")


def symlinks(t, top="src"):
    p = lambda s: top + "/" + s
    t.f(p("file.txt"), text(50, 200))
    t.f(p("dir/inner.txt"), text(51, 200))
    t.f(p("dir/sub/deep.txt"), text(52, 200))
    t.ln(p("to_file"), "file.txt")
    t.ln(p("to_dir"), "dir")
    t.ln(p("to_dir_slash"), "dir/")
    t.ln(p("dangling"), "does/not/exist")
    t.ln(p("absolute"), "/etc/hosts")
    t.ln(p("abs_dangling"), "/nonexistent/xsync/difftest")
    t.ln(p("dir/up"), "../file.txt")
    t.ln(p("dir/sub/up2"), "../../file.txt")
    t.ln(p("outside"), "../outside.txt")
    t.ln(p("chain"), "to_file")
    t.ln(p("self_loop"), "self_loop")
    t.ln(p("dot"), ".")
    t.ln(p("long"), "x/" * 100 + "y")
    t.ln(p("old_link"), "file.txt", mtime=T(1999, 12, 31, 23, 59, 59, 987654321))
    t.f("outside.txt", b"outside the transfer root\n")


def symlinks_safe(t, top="src"):
    """Symlinks that -L can resolve, plus one dangling link."""
    p = lambda s: top + "/" + s
    t.f(p("file.txt"), text(50, 200))
    t.f(p("dir/inner.txt"), text(51, 200))
    t.f(p("dir/sub/deep.txt"), text(52, 200))
    t.ln(p("to_file"), "file.txt")
    t.ln(p("to_dir"), "dir")
    t.ln(p("dir/up"), "../file.txt")
    t.ln(p("outside"), "../outside.txt")
    t.ln(p("outside_dir"), "../outdir")
    t.ln(p("chain"), "to_file")
    t.f("outside.txt", b"outside the transfer root\n", mode=0o600)
    t.f("outdir/o1.txt", b"o1\n")
    t.f("outdir/nested/o2.txt", b"o2\n")


def symlink_modes(t):
    """macOS symlinks carry their own permission bits; rsync treats them like
    file modes (kept with -p, source mode & ~umask without)."""
    t.f("src/file.txt", b"file\n")
    for mode in (0o777, 0o755, 0o700, 0o644, 0o600, 0o555):
        t.ln("src/l%04o" % mode, "file.txt", mode=mode)
    t.ln("src/existing", "file.txt", mode=0o700)
    t.ln("dst/existing", "file.txt", mode=0o755, mtime=auto_mtime("src/existing"))
    t.ln("src/retarget", "file.txt", mode=0o750)
    t.ln("dst/retarget", "elsewhere", mode=0o700, mtime=T1)


def nsec(t):
    """Pairs that differ only below one second.  rsync's quick check compares
    whole seconds, so `skipped` is left alone (keeping the destination's
    nanoseconds) while `resized` is transferred and gets the source's."""
    t.f("src/skipped.txt", b"same size\n", mtime=T(2014, 1, 1, 0, 0, 0, 111111111))
    t.f("dst/skipped.txt", b"same size\n", mtime=T(2014, 1, 1, 0, 0, 0, 999999999))
    t.f("src/skipped_diff_content.txt", b"AAAA\n", mtime=T(2014, 1, 1, 0, 0, 1, 5))
    t.f("dst/skipped_diff_content.txt", b"BBBB\n", mtime=T(2014, 1, 1, 0, 0, 1, 6))
    t.f("src/resized.txt", b"longer than before\n", mtime=T(2014, 1, 1, 0, 0, 2, 111111111))
    t.f("dst/resized.txt", b"short\n", mtime=T(2014, 1, 1, 0, 0, 2, 999999999))
    t.f("src/zero_ns.txt", b"zero\n", mtime=T(2014, 1, 1, 0, 0, 3, 0))
    t.f("dst/zero_ns.txt", b"zero\n", mtime=T(2014, 1, 1, 0, 0, 3, 1))
    t.d("src/dir", mtime=T(2014, 1, 1, 0, 0, 4, 111111111))
    t.d("dst/dir", mtime=T(2014, 1, 1, 0, 0, 4, 999999999))
    t.ln("src/lnk", "skipped.txt", mtime=T(2014, 1, 1, 0, 0, 5, 111111111))
    t.ln("dst/lnk", "skipped.txt", mtime=T(2014, 1, 1, 0, 0, 5, 999999999))


def typechange(t):
    """Every entry has a different type in src/ and dst/."""
    t.f("src/target.txt", b"target\n")
    t.ln("src/sym_over_file", "target.txt")
    t.f("dst/sym_over_file", b"i was a file\n")
    t.f("src/file_over_sym", b"now a regular file\n")
    t.ln("dst/file_over_sym", "../outside/victim.txt")
    t.f("outside/victim.txt", b"must not be modified\n")
    t.f("src/file_over_emptydir", b"file replaces empty dir\n")
    t.d("dst/file_over_emptydir")
    t.f("src/file_over_dir", b"file replaces non-empty dir\n")
    t.f("dst/file_over_dir/child.txt", b"child\n")
    t.f("dst/file_over_dir/sub/grandchild.txt", b"grandchild\n")
    t.f("src/dir_over_file/inner.txt", b"inner\n")
    t.f("dst/dir_over_file", b"i was a file\n")
    t.f("src/dir_over_dirlink/inner.txt", b"inner\n")
    t.ln("dst/dir_over_dirlink", "../outside/realdir")
    t.f("outside/realdir/existing.txt", b"existing\n")
    t.ln("src/sym_over_dir", "target.txt")
    t.f("dst/sym_over_dir/child.txt", b"child\n")
    t.ln("src/sym_over_emptydir", "target.txt")
    t.d("dst/sym_over_emptydir")
    t.ln("src/sym_over_sym", "target.txt")
    t.ln("dst/sym_over_sym", "elsewhere")
    t.f("src/file_over_fifo", b"file replaces fifo\n")
    t.fifo("dst/file_over_fifo")
    t.f("src/dir_over_emptydir_same/x.txt", b"x\n")
    t.d("dst/dir_over_emptydir_same")


def specials(t):
    t.fifo("src/pipe", mode=0o644)
    t.fifo("src/sub/pipe600", mode=0o600)
    t.f("src/regular.txt", b"regular\n")
    t.d("dst")


def hardlinks(t):
    data = text(60, 5000)
    t.f("src/h1", data)
    t.hl("src/h2", "src/h1")
    t.hl("src/sub/h3", "src/h1")
    t.f("src/solo", data)
    t.d("dst")


def sizes(t):
    for n in (0, 1, 100, 1000, 1023, 1024, 1025, 1500, 4999, 5000, 5001,
              100000):
        t.f("src/s%06d" % n, rnd(70 + n, n))
        t.f("src/sub/t%06d" % n, rnd(71 + n, n))
    t.d("dst")


def deep(t, top="src", levels=40):
    rel = top
    for i in range(levels):
        rel += "/d%02d" % i
        if i % 5 == 0:
            t.f(rel + "/f%02d.txt" % i, b"level %d\n" % i)
        if i % 7 == 0:
            t.ln(rel + "/up", "..")
    t.f(rel + "/leaf.txt", b"leaf\n")
    t.d(rel + "/empty_leaf")


def many(t, top="src", count=3000):
    r = random.Random(4242)
    for i in range(count):
        t.f("%s/big/f%04d.dat" % (top, i), r.randbytes(r.randint(0, 200)),
            mode=0o644 if i % 10 else 0o600)
    t.f(top + "/other/one.txt", b"one\n")


def empty_dirs(t):
    for rel in ("e1", "e2/e3", "e2/e4/e5/e6", "e7"):
        t.d("src/" + rel)
    t.d("src/e7", mode=0o700)
    t.d("src/e2/e4", mtime=T(1991, 8, 25, 20, 57, 8, 1))


def empty_files(t):
    for rel in ("z0", "z1.txt", "sub/z2", "sub/z3"):
        t.f("src/" + rel, b"")
    t.f("src/ro_empty", b"", mode=0o444)
    t.f("src/nonempty", b"x")
    # destination has content where the source is empty, and vice versa
    t.f("dst/z0", b"not empty in dest\n", mtime=T1)
    t.f("dst/nonempty", b"", mtime=T1)
    t.f("dst/z1.txt", b"")


def time_extremes(t):
    for name, ns in (
            ("epoch", 0), ("epoch_plus_1ns", 1), ("one_second", 10**9),
            ("y1969", T(1969, 7, 20, 20, 17, 40, 5)),
            ("y1901", T(1901, 12, 13, 20, 45, 53)),
            ("y1980", T(1980, 1, 1)),
            ("y2038_last32", (2**31 - 1) * 10**9 + 999999999),
            ("y2038_first33", 2**31 * 10**9),
            ("y2040", T(2040, 2, 29, 12, 0, 0, 1)),
            ("y2106", T(2106, 2, 7, 6, 28, 16)),
            ("ns_max", T(2001, 9, 9, 1, 46, 40, 999999999)),
            ("ns_min", T(2001, 9, 9, 1, 46, 40, 1))):
        t.f("src/" + name, name.encode() + b"\n", mtime=ns)
    t.d("src/olddir", mtime=T(1975, 4, 30, 0, 0, 0, 42))
    t.f("src/olddir/f", b"f\n")
    t.ln("src/oldlink", "epoch", mtime=T(1978, 1, 1, 0, 0, 0, 7))
    t.d("src", mtime=T(1990, 1, 1, 0, 0, 0, 3))


def big_random(t):
    t.f("src/big.bin", rnd(7, 12 * MB), mtime=T(2021, 5, 5, 5, 5, 5, 555))
    t.f("src/small.txt", b"small\n")


def big_compressible(t):
    t.f("src/zeros_and_text.dat", compressible(12 * MB),
        mtime=T(2021, 6, 6, 6, 6, 6, 666))
    t.f("src/small.txt", b"small\n")


def big_delta(t, size=8 * MB):
    """A large source file and an older, damaged version of it in dst/."""
    data = rnd(77, size)
    t.f("src/big.bin", data, mtime=T(2020, 2, 2, 2, 2, 2, 222))
    b = bytearray(data)
    b[1000:1010] = b"XXXXXXXXXX"                      # overwrite in place
    b[5 * MB:5 * MB + 200000] = rnd(79, 200000)       # replace a region
    del b[3 * MB:3 * MB + 100000]                     # delete (shifts data)
    b[MB:MB] = rnd(78, 12345)                         # insert (shifts data)
    del b[-50000:]                                    # truncate
    b += b"different tail"
    t.f("dst/big.bin", bytes(b), mtime=T(2019, 1, 1, 1, 1, 1, 111))
    t.f("src/small.txt", b"small\n")
    del b, data


def unreadable(t):
    t.f("src/ok1.txt", b"ok1\n")
    t.f("src/secret.txt", b"cannot be read\n", mode=0o000)
    t.f("src/sub/ok2.txt", b"ok2\n")
    t.d("dst")


def spaces(t):
    t.f("src dir/a file.txt", text(80, 100))
    t.f("src dir/sub dir/b  two  spaces.txt", text(81, 100))
    t.f("src dir/plain.txt", text(82, 100))
    t.ln("src dir/a link", "a file.txt")
    t.d("src dir/empty dir")
    t.d("dst dir")


# --------------------------------------------------------------------------
# Tree snapshots and comparison
# --------------------------------------------------------------------------

def _hash_file(path, mode):
    h = hashlib.blake2b(digest_size=16)
    try:
        fh = open(path, "rb")
    except PermissionError:
        # e.g. a mode-000 file: we own it, so borrow read permission briefly
        # (chmod changes ctime only, which is not compared).
        os.chmod(path, mode | 0o400)
        try:
            fh = open(path, "rb")
        finally:
            os.chmod(path, mode)
    with fh:
        while True:
            chunk = fh.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def snapshot(root):
    """rel path -> dict(type, mode, mtime, [size, hash | target | links])."""
    snap = {}
    inodes = {}

    def walk(dpath, rel, dmode):
        try:
            names = os.listdir(dpath)
        except PermissionError:
            os.chmod(dpath, dmode | 0o500)
            try:
                names = os.listdir(dpath)
                _walk_names(dpath, rel, names)
            finally:
                os.chmod(dpath, dmode)
            return
        _walk_names(dpath, rel, names)

    def _walk_names(dpath, rel, names):
        for name in sorted(names):
            p = os.path.join(dpath, name)
            r = name if not rel else rel + "/" + name
            try:
                st = os.lstat(p)
            except OSError as exc:
                snap[r] = {"type": "unreadable(%s)" % exc.strerror,
                           "mode": 0, "mtime": 0}
                continue
            e = {"mode": st.st_mode & 0o7777, "mtime": st.st_mtime_ns}
            snap[r] = e
            if stat.S_ISDIR(st.st_mode):
                e["type"] = "dir"
                walk(p, r, e["mode"])
            elif stat.S_ISREG(st.st_mode):
                e["type"] = "file"
                e["size"] = st.st_size
                try:
                    e["hash"] = _hash_file(p, e["mode"])
                except OSError as exc:
                    e["hash"] = "unreadable(%s)" % exc.strerror
                if st.st_nlink > 1:
                    inodes.setdefault((st.st_dev, st.st_ino), []).append(r)
            elif stat.S_ISLNK(st.st_mode):
                e["type"] = "symlink"
                e["target"] = os.readlink(p)
            elif stat.S_ISFIFO(st.st_mode):
                e["type"] = "fifo"
            elif stat.S_ISSOCK(st.st_mode):
                e["type"] = "socket"
            else:
                e["type"] = "special(%o)" % stat.S_IFMT(st.st_mode)

    walk(root, "", 0o700)
    for group in inodes.values():
        if len(group) > 1:
            for r in group:
                snap[r]["links"] = tuple(sorted(group))
    return snap


def q(rel):
    """Printable form of a relative path (control characters escaped)."""
    out = []
    for ch in rel:
        if ch == "\\":
            out.append("\\\\")
        elif ch < " " or ch == "\x7f":
            out.append({"\n": "\\n", "\t": "\\t", "\r": "\\r"}.get(
                ch, "\\x%02x" % ord(ch)))
        else:
            out.append(ch)
    s = "".join(out)
    if len(s) > 90:
        s = s[:40] + "..." + s[-40:]
    if s != rel or s.startswith(" ") or s.endswith(" "):
        return '"' + s + '"'
    return s


def fmt_time(ns):
    if ns == "<now>":
        return ns
    sec, frac = divmod(ns, 10**9)
    try:
        base = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(sec))
    except (OverflowError, ValueError, OSError):
        base = "@%d" % sec
    return "%s.%09d" % (base, frac)


def describe(e):
    t = e["type"]
    if t == "symlink":
        return "symlink -> " + q(e["target"])
    if t == "file":
        return "file (%d bytes)" % e["size"]
    return t


def _collapse(paths, snap):
    """Drop paths whose parent directory is also in the list; return
    [(path, n_hidden_descendants)]."""
    pset = set(paths)
    tops = []
    counts = {}
    for p in sorted(paths):
        parent = p
        top = None
        while "/" in parent:
            parent = parent.rsplit("/", 1)[0]
            if parent in pset:
                top = parent
        if top is None:
            tops.append(p)
        else:
            counts[top] = counts.get(top, 0) + 1
    return [(p, counts.get(p, 0)) for p in tops]


class Diff(str):
    """One line of difference, tagged with its kind so that a flood of one
    kind (say, 3000 mtimes) cannot crowd every other kind out of the report."""
    kind = ""


def _d(kind, textline):
    d = Diff(textline)
    d.kind = kind
    return d


def condense(lines, limit=MAX_DIFF_LINES):
    """Cap a report at about `limit` lines, keeping examples of every kind."""
    if len(lines) <= limit:
        return list(lines)
    kinds = []
    for l in lines:
        k = getattr(l, "kind", None)
        if k is not None and k not in kinds:
            kinds.append(k)
    plain = sum(1 for l in lines if getattr(l, "kind", None) is None)
    per_kind = max(2, (limit - plain) // max(1, len(kinds)) - 1)
    out, shown, hidden = [], {}, {}
    for l in lines:
        k = getattr(l, "kind", None)
        if k is None:
            out.append(l)
        elif shown.get(k, 0) < per_kind:
            shown[k] = shown.get(k, 0) + 1
            out.append(l)
        else:
            if k not in hidden:
                hidden[k] = len(out)
                out.append(None)            # placeholder for the "... more" line
            shown[k] += 1
    for k, pos in hidden.items():
        n = shown[k] - per_kind
        out[pos] = "... and %d more %s difference%s" % (n, k, "" if n == 1 else "s")
    if len(out) > limit + 4:
        out = out[:limit] + ["... and %d more lines" % (len(out) - limit)]
    return out


def compare(ref, got, skip=(), window=None, ignore=(),
            names=("rsync result", "xsync result"), words=("expected", "got")):
    """Return a list of human-readable differences between two snapshots.

    `window` is (lo_ns, hi_ns): mtimes inside it are "set by the tool during
    this case" and compare equal to each other as <now>.
    """
    def norm(ns):
        if window and window[0] <= ns <= window[1]:
            return "<now>"
        return ns

    def ignored(p):
        return any(p == i or p.startswith(i + "/") for i in ignore)

    E, G = words
    diffs = []
    rkeys = {p for p in ref if not ignored(p)}
    gkeys = {p for p in got if not ignored(p)}
    for label, only, snap in (("only in %s" % names[0], rkeys - gkeys, ref),
                              ("only in %s" % names[1], gkeys - rkeys, got)):
        for p, hidden in _collapse(only, snap):
            extra = " (+%d entries below it)" % hidden if hidden else ""
            diffs.append(_d(label, "%s: %s  [%s]%s" % (label, q(p), describe(snap[p]), extra)))

    for p in sorted(rkeys & gkeys):
        a, b = ref[p], got[p]
        if a["type"] != b["type"]:
            diffs.append(_d("type", "%s: type %s=%s %s=%s" % (q(p), E, describe(a), G, describe(b))))
            continue
        kind = a["type"]
        if kind == "file":
            if a["hash"] != b["hash"]:
                diffs.append(_d("content", "%s: content %s=%d bytes [%s] %s=%d bytes [%s]" % (
                    q(p), E, a["size"], a["hash"][:8], G, b["size"], b["hash"][:8])))
            if "hardlinks" not in skip and a.get("links") != b.get("links"):
                diffs.append(_d("hardlinks", "%s: hardlinks %s=%s %s=%s" % (
                    q(p),
                    E, "{%s}" % ", ".join(map(q, a["links"])) if a.get("links") else "none",
                    G, "{%s}" % ", ".join(map(q, b["links"])) if b.get("links") else "none")))
        elif kind == "symlink":
            if a["target"] != b["target"]:
                diffs.append(_d("symlink-target", "%s: symlink-target %s=%s %s=%s" % (
                    q(p), E, q(a["target"]), G, q(b["target"]))))
        mode_attr = "symlink-mode" if kind == "symlink" else "mode"
        if mode_attr not in skip and a["mode"] != b["mode"]:
            diffs.append(_d(mode_attr, "%s: %s %s=%04o %s=%04o" % (
                q(p), mode_attr, E, a["mode"], G, b["mode"])))
        time_attr = {"symlink": "symlink-mtime", "dir": "dir-mtime"}.get(kind, "mtime")
        if time_attr not in skip:
            ma, mb = norm(a["mtime"]), norm(b["mtime"])
            if ma != mb:
                note = ""
                if "<now>" not in (ma, mb) and ma // 10**9 == mb // 10**9:
                    note = " (sub-second part only)"
                diffs.append(_d(time_attr + note, "%s: %s %s=%s %s=%s%s" % (
                    q(p), time_attr, E, fmt_time(ma), G, fmt_time(mb), note)))
    return diffs


# ---- assertions on the reference result (guard against rotten cases) ------

def present(*paths):
    return lambda s: ["expected %s to exist" % q(p) for p in paths if p not in s]


def absent(*paths):
    return lambda s: ["expected %s not to exist" % q(p) for p in paths if p in s]


def same_file(a, b):
    def check(s):
        if a not in s or b not in s:
            return ["expected both %s and %s to exist" % (q(a), q(b))]
        if s[a].get("hash") != s[b].get("hash"):
            return ["expected %s and %s to have equal content" % (q(a), q(b))]
        return []
    return check


def diff_file(a, b):
    def check(s):
        if a not in s or b not in s:
            return ["expected both %s and %s to exist" % (q(a), q(b))]
        if s[a].get("hash") == s[b].get("hash"):
            return ["expected %s and %s to differ in content" % (q(a), q(b))]
        return []
    return check


def is_type(path, kind):
    def check(s):
        if path not in s:
            return ["expected %s to exist" % q(path)]
        if s[path]["type"] != kind:
            return ["expected %s to be a %s, it is a %s" % (q(path), kind, s[path]["type"])]
        return []
    return check


def same_mtime(a, b):
    def check(s):
        if a not in s or b not in s:
            return ["expected both %s and %s to exist" % (q(a), q(b))]
        if s[a]["mtime"] != s[b]["mtime"]:
            return ["expected %s and %s to have the same mtime" % (q(a), q(b))]
        return []
    return check


def all_of(*checks):
    return lambda s: [msg for c in checks for msg in c(s)]


# --------------------------------------------------------------------------
# Case table
# --------------------------------------------------------------------------

class Case:
    def __init__(self, name, build, steps, rc, unchanged, verify, skip, ignore, serial):
        self.name = name
        self.build = build
        self.steps = steps
        self.rc = rc
        self.unchanged = unchanged
        self.verify = verify
        self.skip = frozenset(skip)
        self.ignore = tuple(ignore)
        self.serial = serial


CASES = []


def case(name, build, *steps, rc=0, unchanged=None, verify=None, skip=(), ignore=(),
         serial=False, ref_args=()):
    """Register a case.

    steps      one or more argument lists (a str is split with shlex) that are
               passed verbatim to both tools, run in order with the sandbox as
               cwd.  Placeholders: {BIN} absolute path of the tool being run,
               {SSH} absolute path of fakessh.sh, {ROOT} absolute sandbox path.
    rc         exit code(s) the *reference* rsync is expected to return; a
               mismatch means the case itself is broken.
    unchanged  N: the tree after the last step must be identical to the tree
               after step N (0 = the pristine fixture), mtimes included.
    verify     callable(final reference snapshot) -> list of problems; again a
               guard that the case exercises what it claims to.
    skip       attribute names (see ALL_ATTRS) not to compare for this case.
    ignore     relative paths (and everything below them) not to compare.
    serial     build/run the reference side to completion (and delete it)
               before starting the other side.  Used by the large-file cases
               to halve their peak disk usage; all other cases run the two
               sides concurrently.
    """
    assert all(c.name != name for c in CASES), "duplicate case name " + name
    assert not set(skip) - set(ALL_ATTRS), skip
    parsed = [shlex.split(s) if isinstance(s, str) else list(s) for s in steps]
    rcs = list(rc) if isinstance(rc, (list, tuple)) else [rc] * len(parsed)
    assert len(rcs) == len(parsed), name
    c = Case(name, build, parsed, rcs, unchanged, verify, skip, ignore, serial)
    c.ref_args = list(ref_args)
    CASES.append(c)


emptydst = mkdirs("dst")
nothing = lambda t: None
R = "-e {SSH} --rsync-path={BIN}"       # remote-shell boilerplate

for transport, command in (
        ("local", "-a src/ ./"),
        ("push", "-a " + R + " src/ fakehost:{ROOT}/"),
        ("pull", "-a " + R + " fakehost:{ROOT}/src/ ./")):
    case("source_inside_destination_%s" % transport, plain, command,
         verify=all_of(same_file("src/a.txt", "a.txt"), present("sub/deep/d.txt")))

# xsync deliberately excludes its destination. Give rsync that same exclusion
# to compare the intended safe result, rather than rsync's one nest per run.
for transport, command in (
        ("local", "-a src/ src/backup/"),
        ("push", "-a " + R + " src/ fakehost:{ROOT}/src/backup/"),
        ("pull", "-a " + R + " fakehost:{ROOT}/src/ src/backup/")):
    for existing in (False, True):
        fixture = B(plain, mkdirs("src/backup")) if existing else plain
        case("nested_dest_%s_%s" % (transport, "existing" if existing else "new"),
             fixture, command, command, ref_args=("--exclude=/backup/",),
             verify=all_of(same_file("src/a.txt", "src/backup/a.txt"),
                           absent("src/backup/backup")))

# ---- invocation forms ------------------------------------------------------
case("a_trailing_slash", B(basic, emptydst), "-a src/ dst/",
     verify=all_of(same_file("src/a.txt", "dst/a.txt"), is_type("dst/dangling", "symlink"),
                   same_mtime("src/ns.txt", "dst/ns.txt"), same_mtime("src/sub", "dst/sub"),
                   same_mtime("src/link_to_file", "dst/link_to_file")))
case("a_no_trailing_slash", B(basic, emptydst), "-a src dst/",
     verify=present("dst/src/a.txt", "dst/src/sub/deep/d.txt"))
case("a_no_slash_either", B(basic, emptydst), "-a src dst", verify=present("dst/src/a.txt"))
case("a_src_slash_dot", B(basic, emptydst), "-a src/. dst", verify=present("dst/a.txt"))
case("a_dest_missing", basic, "-a src/ newdst", verify=present("newdst/a.txt"))
case("a_dest_missing_trailing_slash", basic, "-a src/ newdst/", verify=present("newdst/a.txt"))
case("a_dest_missing_src_no_slash", basic, "-a src newdst", verify=present("newdst/src/a.txt"))
case("a_dest_parent_missing", basic, "-a src/ no/such/dst/", rc=11, verify=absent("no"))
case("a_mkpath", basic, "-a --mkpath src/ made/up/dst/", verify=present("made/up/dst/a.txt"))
case("multiple_sources", multi, "-a src1 src2/ loose.txt dst/",
     verify=present("dst/src1/a.txt", "dst/b.txt", "dst/loose.txt", "dst/sub/y.txt"))
case("multiple_sources_overlap", multi, "-a src1/ src2/ dst/",
     verify=present("dst/a.txt", "dst/b.txt", "dst/sub/x.txt", "dst/sub/y.txt", "dst/common.txt"))
case("multiple_sources_dest_missing", multi, "-a src1 src2/ loose.txt newdst",
     verify=present("newdst/src1/a.txt", "newdst/loose.txt"))
case("file_to_new_name", B(basic, emptydst), "-a src/a.txt dst/renamed.txt",
     verify=same_file("src/a.txt", "dst/renamed.txt"))
case("file_to_existing_dir", B(basic, emptydst), "-a src/a.txt dst",
     verify=same_file("src/a.txt", "dst/a.txt"))
case("file_to_missing_dir_slash", basic, "-a src/a.txt newdir/",
     verify=same_file("src/a.txt", "newdir/a.txt"))
case("file_to_missing_name", basic, "-a src/a.txt newname",
     verify=all_of(is_type("newname", "file"), same_file("src/a.txt", "newname")))
case("file_overwrite_existing_file",
     B(basic, lambda t: t.f("dst/a.txt", b"stale destination content\n", mode=0o600, mtime=T1)),
     "-a src/a.txt dst/a.txt", verify=same_file("src/a.txt", "dst/a.txt"))
case("files_to_missing_dir", basic, "-a src/a.txt src/b.bin src/exec.sh newdir",
     verify=present("newdir/a.txt", "newdir/b.bin"))
case("symlink_as_source_arg", B(basic, emptydst), "-a src/link_to_file src/link_to_dir dst/",
     verify=all_of(is_type("dst/link_to_file", "symlink"), is_type("dst/link_to_dir", "symlink")))
case("double_dash_separator",
     B(emptydst, lambda t: t.f("-dash.txt", b"leading dash on the command line\n")),
     ["-a", "--", "-dash.txt", "dst/"], verify=present("dst/-dash.txt"))
case("version", nothing, "--version", unchanged=0)
case("help", nothing, "--help", unchanged=0)
case("no_args", nothing, [], rc=1, unchanged=0)
case("unknown_option", B(basic, emptydst), "-a --no-such-option src/ dst/", rc=1, unchanged=0)
case("missing_source", emptydst, "-a nonexistent/ dst/", rc=23)
case("missing_source_partial", B(basic, emptydst), "-a src/a.txt nonexistent.txt src/b.bin dst/",
     rc=23, verify=present("dst/a.txt", "dst/b.bin"))
if os.geteuid() != 0:  # Root bypasses this permission fixture; injected EIO tests cover root.
    case("unreadable_source_file", unreadable, "-a src/ dst/", rc=23,
         verify=all_of(present("dst/ok1.txt", "dst/sub/ok2.txt"), absent("dst/secret.txt")))

# ---- re-runs and updates ---------------------------------------------------
case("rerun_unchanged", B(basic, under(basic, "dst")), "-a src/ dst/", unchanged=0)
case("run_twice", B(basic, emptydst), "-a src/ dst/", "-a src/ dst/", unchanged=1)
case("run_twice_delete", B(upd), "-a --delete src/ dst/", "-a --delete src/ dst/", unchanged=1)
case("update_mixed", upd, "-a src/ dst/",
     verify=all_of(same_file("src/changed.txt", "dst/changed.txt"),
                   same_file("src/samesize_diffmtime.bin", "dst/samesize_diffmtime.bin"),
                   same_file("src/diffsize_samemtime.txt", "dst/diffsize_samemtime.txt"),
                   same_file("src/blob.bin", "dst/blob.bin"),
                   same_file("src/dest_newer.txt", "dst/dest_newer.txt"),
                   same_mtime("src/touched.txt", "dst/touched.txt"),
                   diff_file("src/sneaky.bin", "dst/sneaky.bin"),
                   present("dst/extra.txt", "dst/extra_dir/nested/e2.txt", "dst/extra_link",
                           "dst/extra_empty", "dst/new.txt", "dst/newdir/emptynew")))
case("delete", upd, "-a --delete src/ dst/",
     verify=all_of(absent("dst/extra.txt", "dst/extra_dir", "dst/extra_empty", "dst/extra_link",
                          "dst/extra_dangling", "dst/sub/extra_in_sub.txt"),
                   present("dst/new.txt", "dst/sub/keepdir/k.txt")))
case("delete_before", upd, "-a --delete-before src/ dst/", verify=absent("dst/extra.txt"))
case("delete_after", upd, "-a --delete-after src/ dst/", verify=absent("dst/extra.txt"))
case("delete_no_trailing_slash",
     B(upd, lambda t: (t.f("dst/src/stale.txt", b"stale\n"), t.f("dst/outside_src.txt", b"keep\n"))),
     "-a --delete src dst/",
     verify=all_of(absent("dst/src/stale.txt"), present("dst/outside_src.txt", "dst/extra.txt")))
case("update_newer_kept", upd, "-au src/ dst/",
     verify=all_of(diff_file("src/dest_newer.txt", "dst/dest_newer.txt"),
                   same_file("src/changed.txt", "dst/changed.txt")))
case("size_only", upd, "-a --size-only src/ dst/",
     verify=all_of(diff_file("src/samesize_diffmtime.bin", "dst/samesize_diffmtime.bin"),
                   same_file("src/diffsize_samemtime.txt", "dst/diffsize_samemtime.txt")))
case("checksum", upd, "-ac src/ dst/",
     verify=all_of(same_file("src/sneaky.bin", "dst/sneaky.bin"),
                   same_file("src/samesize_diffmtime.bin", "dst/samesize_diffmtime.bin")))
case("ignore_times", upd, "-aI src/ dst/", verify=same_file("src/sneaky.bin", "dst/sneaky.bin"))
case("ignore_existing", upd, "-a --ignore-existing src/ dst/",
     verify=all_of(diff_file("src/changed.txt", "dst/changed.txt"), present("dst/new.txt")))
case("existing", upd, "-a --existing src/ dst/",
     verify=all_of(same_file("src/changed.txt", "dst/changed.txt"),
                   absent("dst/new.txt", "dst/newdir")))
case("existing_delete", upd, "-a --existing --delete src/ dst/",
     verify=absent("dst/new.txt", "dst/extra.txt"))
case("dry_run", upd, "-an --delete src/ dst/", unchanged=0)
case("dry_run_verbose_itemize", upd, "-anvi --delete src/ dst/", unchanged=0)
case("dry_run_dest_missing", basic, "-an src/ newdst/", unchanged=0, verify=absent("newdst"))
case("whole_file", upd, "-aW src/ dst/", verify=same_file("src/blob.bin", "dst/blob.bin"))
case("no_whole_file", upd, "-a --no-whole-file src/ dst/",
     verify=same_file("src/blob.bin", "dst/blob.bin"))
case("inplace", B(upd, lambda t: (t.hl("alias_changed", "dst/changed.txt"),
                                  t.hl("alias_blob", "dst/blob.bin"))),
     "-a --inplace src/ dst/",
     verify=all_of(same_file("src/changed.txt", "alias_changed"),
                   same_file("src/blob.bin", "alias_blob")))
for transport, command in (
        ("local", "src/ dst/"),
        ("push", R + " src/ fakehost:{ROOT}/dst/"),
        ("pull", R + " fakehost:{ROOT}/src/ dst/")):
    case("inplace_replaces_destination_symlink_%s" % transport,
         B(plain, lambda t: (t.f("outside", b"must survive"), t.ln("dst/a.txt", "../outside"))),
         "-a --inplace " + command,
         verify=all_of(same_file("src/a.txt", "dst/a.txt"), diff_file("outside", "dst/a.txt")))

case("not_inplace_breaks_hardlink", B(upd, lambda t: t.hl("alias_changed", "dst/changed.txt")),
     "-a src/ dst/", verify=diff_file("src/changed.txt", "alias_changed"))
case("az_local", upd, "-az src/ dst/", verify=same_file("src/blob.bin", "dst/blob.bin"))
case("az_local_fresh", B(basic, emptydst), "-az src/ dst/")
case("one_file_system", B(basic, emptydst), "-ax src/ dst/", verify=present("dst/sub/deep/d.txt"))

# ---- option subsets of -a --------------------------------------------------
case("r_only", B(basic, emptydst), "-r src/ dst/",
     verify=all_of(present("dst/sub/deep/d.txt"), absent("dst/link_to_file")))
case("r_only_existing_dest", upd, "-r src/ dst/")
case("rt", B(basic, emptydst), "-rt src/ dst/", verify=same_mtime("src/ns.txt", "dst/ns.txt"))
case("rl", B(basic, emptydst), "-rl src/ dst/", verify=is_type("dst/link_to_dir", "symlink"))
case("rlp", B(basic, emptydst), "-rlp src/ dst/")
case("rlpt", B(basic, emptydst), "-rlpt src/ dst/")
case("rlpt_update", upd, "-rlpt src/ dst/")
case("a_no_times", B(basic, emptydst), "-a --no-times src/ dst/")
case("a_no_times_update", upd, "-a --no-times src/ dst/")
case("a_no_perms", B(modes, emptydst), "-a --no-perms src/ dst/")
case("a_no_perms_existing", B(modes, modes_dst_different), "-a --no-perms src/ dst/")
case("omit_dir_times", B(basic, emptydst), "-aO src/ dst/")
case("omit_dir_times_update", upd, "-aO src/ dst/")
case("omit_link_times", B(basic, emptydst), "-aJ src/ dst/")
case("dirs_no_recursion", B(basic, emptydst), "-d src/ dst/",
     verify=all_of(present("dst/a.txt", "dst/sub"), absent("dst/sub/c.txt")))
case("dirs_no_recursion_no_slash", B(basic, emptydst), "-dt src dst/",
     verify=all_of(is_type("dst/src", "dir"), absent("dst/src/a.txt")))
case("no_r_dir_skipped", B(basic, emptydst), "src dst/", unchanged=0)
case("no_r_files_and_dir", B(basic, emptydst), "-t src/a.txt src/sub src/b.bin dst/",
     verify=all_of(present("dst/a.txt", "dst/b.bin"), absent("dst/sub")))
case("max_size", sizes, "-a --max-size=1k src/ dst/",
     verify=all_of(present("dst/s001024"), absent("dst/s001025")))
case("min_size", sizes, "-a --min-size=1025 src/ dst/",
     verify=all_of(present("dst/s001025"), absent("dst/s001024")))
case("max_min_size_units", sizes, "-a --min-size=100 --max-size=5KB src/ dst/",
     verify=all_of(present("dst/s000100", "dst/s005000"), absent("dst/s000001", "dst/s005001")))

# ---- filters ---------------------------------------------------------------
case("exclude_simple", B(filt, emptydst), "-a --exclude=*.log --exclude=tmp --exclude=.git src/ dst/",
     verify=all_of(absent("dst/a.log", "dst/sub/b.log", "dst/tmp", "dst/.git"), present("dst/a.txt")))
case("include_exclude_txt_only", B(filt, emptydst),
     ["-a", "--include=*/", "--include=*.txt", "--exclude=*", "src/", "dst/"],
     verify=all_of(present("dst/sub/deep/c.txt", "dst/emptydir", "dst/cache"),
                   absent("dst/a.log", "dst/foo", "dst/cache/x.dat")))
case("include_exclude_prune_empty", B(filt, emptydst),
     ["-am", "--include=*/", "--include=*.txt", "--exclude=*", "src/", "dst/"],
     verify=all_of(present("dst/sub/deep/c.txt"), absent("dst/emptydir", "dst/cache", "dst/logs")))
case("exclude_anchored", B(filt, emptydst), "-a --exclude=/foo --exclude=/sub/cache src/ dst/",
     verify=all_of(absent("dst/foo", "dst/sub/cache"),
                   present("dst/sub/foo", "dst/sub/deep/foo/inner.txt", "dst/cache/x.dat")))
case("exclude_anchored_no_slash_src", B(filt, emptydst), "-a --exclude=/src/foo --exclude=/foo.txt src dst/",
     verify=all_of(absent("dst/src/foo"), present("dst/src/sub/foo", "dst/src/foo.txt")))
case("exclude_dir_only", B(filt, emptydst), "-a --exclude=foo/ --exclude=build/ src/ dst/",
     verify=all_of(absent("dst/sub/deep/foo", "dst/build"),
                   present("dst/foo", "dst/sub/foo", "dst/sub/build")))
case("exclude_doublestar", B(filt, emptydst),
     ["-a", "--exclude=**/cache/**", "--exclude=a/**/z.txt", "--exclude=docs/**.txt", "src/", "dst/"],
     verify=all_of(absent("dst/sub/cache/top.txt", "dst/sub/cache/y", "dst/a/b/c/z.txt",
                          "dst/docs/readme.txt", "dst/docs/img/raw/pic.txt"),
                   present("dst/sub/cache", "dst/a/b/other.txt", "dst/docs/img/pic.png")))
case("exclude_wildcards", B(filt, emptydst),
     ["-a", "--exclude=*.[ol]*", "--exclude=fo?", "--exclude=sub/*/c.txt", "--exclude=docs/*/raw",
      "src/", "dst/"],
     verify=all_of(absent("dst/a.log", "dst/sub/deep/c.o", "dst/foo", "dst/sub/deep/c.txt",
                          "dst/docs/img/raw"),
                   present("dst/foo.txt", "dst/foo.d/in.txt")))
case("exclude_triple_star", B(filt, emptydst),
     ["-a", "--include=/docs/***", "--include=/sub/", "--include=/sub/deep/***", "--exclude=*",
      "src/", "dst/"],
     verify=all_of(present("dst/docs/img/raw/pic.txt", "dst/sub/deep/foo/inner.txt"),
                   absent("dst/a.txt", "dst/sub/b.txt")))
case("exclude_from_file",
     B(filt, emptydst, lambda t: t.f("rules.txt",
                                     b"# comment line\n; another comment\n\n*.log\n/foo\nbuild/\n"
                                     b"**/cache/**\n+ keepme\n*.tmp\n")),
     "-a --exclude-from=rules.txt src/ dst/",
     verify=all_of(absent("dst/a.log", "dst/foo", "dst/build", "dst/x.tmp", "dst/sub/cache/top.txt"),
                   present("dst/sub/foo", "dst/sub/build")))
case("include_from_file",
     B(filt, emptydst, lambda t: t.f("inc.txt", b"*/\n*.txt\n")),
     "-a --include-from=inc.txt --exclude=* src/ dst/",
     verify=all_of(present("dst/a.txt"), absent("dst/a.log")))
case("filter_rules", B(filt, emptydst),
     ["-a", "-f", "+ /sub/deep/c.o", "-f", "- *.o", "--filter=- /docs/img/", "-f", "exclude *.tmp",
      "-f", "include /cache/", "-f", "- /cache/*", "src/", "dst/"],
     verify=all_of(present("dst/sub/deep/c.o", "dst/cache", "dst/docs/readme.txt"),
                   absent("dst/build/out.o", "dst/docs/img", "dst/x.tmp", "dst/sub/y.tmp",
                          "dst/cache/x.dat")))
case("exclude_order_first_match_wins", B(filt, emptydst),
     ["-a", "--exclude=*.txt", "--include=a.txt", "--include=*.md", "--exclude=sub", "src/", "dst/"],
     verify=all_of(absent("dst/a.txt", "dst/sub"), present("dst/notes.md")))
case("delete_with_exclude", B(filt, filt_dst), "-a --delete --exclude=*.log --exclude=/tmp/ src/ dst/",
     verify=all_of(present("dst/stale.log", "dst/sub/old.log", "dst/logs_only/x.log",
                           "dst/gone/g.log", "dst/tmp/stale_t"),
                   absent("dst/stale.txt", "dst/sub/old.txt", "dst/gone/g.txt",
                          "dst/build/stale.o")))
case("delete_excluded", B(filt, filt_dst), "-a --delete-excluded --exclude=*.log --exclude=/tmp/ src/ dst/",
     verify=absent("dst/stale.log", "dst/sub/old.log", "dst/logs_only", "dst/gone", "dst/tmp",
                   "dst/a.log", "dst/stale.txt"))
case("delete_with_include_exclude", B(filt, filt_dst),
     ["-a", "--delete", "--include=*/", "--include=*.txt", "--exclude=*", "src/", "dst/"],
     verify=all_of(absent("dst/stale.txt", "dst/sub/old.txt"), present("dst/stale.log", "dst/a.log")))
case("delete_protect_filter", B(filt, filt_dst),
     ["-a", "--delete", "--filter=P stale.*", "--filter=P /gone/", "src/", "dst/"],
     verify=all_of(present("dst/stale.txt", "dst/stale.log", "dst/gone/g.txt"),
                   absent("dst/sub/old.txt", "dst/logs_only")))

# ---- tree shapes -----------------------------------------------------------
case("empty_dirs", B(empty_dirs, emptydst), "-a src/ dst/",
     verify=all_of(is_type("dst/e2/e4/e5/e6", "dir"), same_mtime("src/e2/e4", "dst/e2/e4")))
case("empty_source_dir", mkdirs("src", "dst"), "-a src/ dst/")
case("empty_source_dir_delete",
     B(mkdirs("src"), under(plain, "dst")), "-a --delete src/ dst/", verify=absent("dst/a.txt"))
case("empty_files", empty_files, "-a src/ dst/",
     verify=all_of(same_file("src/z0", "dst/z0"), same_file("src/nonempty", "dst/nonempty")))
case("deep_nesting", B(deep, emptydst), "-a src/ dst/",
     verify=present("dst/" + "/".join("d%02d" % i for i in range(40)) + "/leaf.txt"))
case("deep_nesting_delete", B(mkdirs("src"), under(deep, "dst")), "-a --delete src/ dst/",
     verify=absent("dst/d00"))
case("many_files", B(many, emptydst), "-a src/ dst/",
     verify=present("dst/big/f0000.dat", "dst/big/f2999.dat"))
case("many_files_update_delete",
     B(lambda t: many(t, "src", 1500), lambda t: many(t, "dst", 1600),
       lambda t: [t.f("src/big/f%04d.dat" % i, b"changed %d\n" % i, mtime=T2 + i)
                  for i in range(0, 1500, 7)]),
     "-a --delete src/ dst/",
     verify=all_of(absent("dst/big/f1500.dat", "dst/big/f1599.dat"),
                   same_file("src/big/f0007.dat", "dst/big/f0007.dat")))
case("weird_names", B(weird, emptydst), "-a src/ dst/",
     verify=present("dst/new\nline.txt", "dst/-leading-dash.txt", "dst/naïve-文件.txt",
                    "dst/trailing space ", "dst/" + "a" * 200 + ".long"))
case("weird_names_delete",
     B(lambda t: [t.f("src/" + n, text(300 + i, 20 + i)) for i, n in enumerate(WEIRD_NAMES[::2])],
       under(weird, "dst")),
     "-a --delete src/ dst/", verify=absent("dst/it's \"quoted\".txt", "dst/link with space"))
case("weird_name_source_args", B(weird, emptydst),
     ["-a", "src/with space.txt", "src/new\nline.txt", "src/star*glob?.txt", "src/[bracket].txt",
      "src/$dollar`tick`.txt", "src/dir with space", "dst/"],
     verify=present("dst/new\nline.txt", "dst/star*glob?.txt", "dst/dir with space/inner file.txt"))
case("large_random_file", B(big_random, emptydst), "-a src/ dst/",
     verify=same_file("src/big.bin", "dst/big.bin"), serial=True)
case("large_compressible_file_z", B(big_compressible, emptydst), "-az src/ dst/",
     verify=same_file("src/zeros_and_text.dat", "dst/zeros_and_text.dat"), serial=True)
case("large_delta_local", big_delta, "-a --no-whole-file src/ dst/",
     verify=same_file("src/big.bin", "dst/big.bin"), serial=True)
case("large_delta_inplace", big_delta, "-a --no-whole-file --inplace src/ dst/",
     verify=same_file("src/big.bin", "dst/big.bin"), serial=True)
case("same_second_different_nsec", nsec, "-a src/ dst/",
     verify=all_of(diff_file("src/skipped_diff_content.txt", "dst/skipped_diff_content.txt"),
                   same_mtime("src/resized.txt", "dst/resized.txt"),
                   lambda s: [] if s["dst/skipped.txt"]["mtime"] == T(2014, 1, 1, 0, 0, 0, 999999999)
                   else ["expected rsync to leave dst/skipped.txt (and its nanoseconds) alone"]))
case("same_second_different_nsec_checksum", nsec, "-ac src/ dst/",
     verify=same_file("src/skipped_diff_content.txt", "dst/skipped_diff_content.txt"))
case("time_extremes", B(time_extremes, emptydst), "-a src/ dst/",
     verify=all_of(same_mtime("src/y1901", "dst/y1901"), same_mtime("src/y2106", "dst/y2106"),
                   same_mtime("src/epoch", "dst/epoch"), same_mtime("src/ns_max", "dst/ns_max"),
                   same_mtime("src/oldlink", "dst/oldlink"), same_mtime("src/olddir", "dst/olddir")))

# ---- permissions -----------------------------------------------------------
case("modes", B(modes, emptydst), "-a src/ dst/")
case("modes_fix_existing", B(modes, modes_dst_different), "-a src/ dst/")
case("modes_r_only", B(modes, emptydst), "-r src/ dst/")
case("modes_rt_existing_dest", B(modes, modes_dst_different), "-rt src/ dst/")
case("modes_readonly_dir_update",
     B(modes, under(modes, "dst"),
       lambda t: (t.f("src/ro_dir/inside.txt", b"inside, but changed\n", mtime=T2),
                  t.f("src/ro_dir/sub/added.txt", b"added\n"),
                  t.f("dst/ro_dir/sub/stale.txt", b"stale\n"))),
     "-a --delete src/ dst/",
     verify=all_of(same_file("src/ro_dir/inside.txt", "dst/ro_dir/inside.txt"),
                   present("dst/ro_dir/sub/added.txt"), absent("dst/ro_dir/sub/stale.txt")))
case("setgid_dir", setgid, "-a src/ dst/")
case("setgid_dir_no_perms", setgid, "-rt src/ dst/")

# ---- symlinks, type changes, specials, hard links --------------------------
case("symlinks", B(symlinks, emptydst), "-a src/ dst/",
     verify=all_of(is_type("dst/to_file", "symlink"), is_type("dst/dangling", "symlink"),
                   is_type("dst/absolute", "symlink"), is_type("dst/self_loop", "symlink"),
                   same_mtime("src/old_link", "dst/old_link")))
case("symlinks_update",
     B(symlinks, under(symlinks, "dst"),
       lambda t: (t.ln("dst/to_file", "dir/inner.txt"), t.ln("dst/dangling", "file.txt"),
                  t.ln("dst/old_link", "file.txt", mtime=T1), t.ln("dst/extra_link", "file.txt"))),
     "-a src/ dst/", verify=present("dst/extra_link"))
case("symlinks_no_l_skipped", B(symlinks, emptydst), "-rpt src/ dst/",
     verify=absent("dst/to_file", "dst/to_dir"))
for transport, command in (
        ("local", "src/ dst/"),
        ("push", R + " src/ fakehost:{ROOT}/dst/"),
        ("pull", R + " fakehost:{ROOT}/src/ dst/")):
    case("safe_links_%s" % transport, B(symlinks, emptydst), "-a --safe-links " + command,
         verify=all_of(absent("dst/absolute", "dst/abs_dangling", "dst/outside"),
                       present("dst/dir/up", "dst/dir/sub/up2", "dst/dangling")))
    case("safe_links_delete_%s" % transport, B(symlinks, under(symlinks, "dst")),
         "-a --safe-links --delete " + command)
    case("safe_links_copy_links_%s" % transport, B(symlinks_safe, emptydst), "-aL --safe-links " + command)
for transport, command in (
        ("local", "src dst/"),
        ("push", R + " src fakehost:{ROOT}/dst/"),
        ("pull", R + " fakehost:{ROOT}/src dst/")):
    case("safe_links_source_directory_%s" % transport, B(symlinks, emptydst), "-a --safe-links " + command,
         verify=all_of(present("dst/src/outside"), absent("dst/src/absolute")))

case("symlink_modes", symlink_modes, "-a src/ dst/")
case("symlink_modes_no_perms", symlink_modes, "-rlt src/ dst/")
case("copy_links", B(symlinks_safe, emptydst), "-aL src/ dst/",
     verify=all_of(is_type("dst/to_file", "file"), is_type("dst/to_dir", "dir"),
                   present("dst/outside_dir/nested/o2.txt"), same_file("outside.txt", "dst/outside")))
case("copy_links_dangling",
     B(symlinks_safe, emptydst, lambda t: t.ln("src/dangling", "missing-target")),
     "-aL src/ dst/", rc=23, verify=all_of(absent("dst/dangling"), is_type("dst/to_file", "file")))
case("copy_links_source_arg", B(symlinks_safe, emptydst), "-rtL src/to_file src/to_dir dst/",
     verify=all_of(is_type("dst/to_file", "file"), present("dst/to_dir/inner.txt")))
case("typechange", typechange, "-a src/ dst/", rc=23,
     verify=all_of(is_type("dst/file_over_dir", "dir"), is_type("dst/sym_over_dir", "dir"),
                   is_type("dst/file_over_emptydir", "file"), is_type("dst/sym_over_file", "symlink"),
                   is_type("dst/file_over_sym", "file"), is_type("dst/dir_over_dirlink", "dir"),
                   is_type("dst/file_over_fifo", "file"), absent("outside/realdir/inner.txt")))
case("typechange_force", typechange, "-a --force src/ dst/",
     verify=all_of(is_type("dst/file_over_dir", "file"), is_type("dst/sym_over_dir", "symlink"),
                   is_type("dst/dir_over_dirlink", "dir"), is_type("dst/file_over_sym", "file"),
                   absent("outside/realdir/inner.txt")))
case("typechange_delete", typechange, "-a --delete src/ dst/",
     verify=all_of(is_type("dst/file_over_dir", "file"), is_type("dst/sym_over_dir", "symlink"),
                   is_type("dst/dir_over_file", "dir"), is_type("dst/sym_over_file", "symlink")))
case("fifo", specials, "-a src/ dst/",
     verify=all_of(is_type("dst/pipe", "fifo"), is_type("dst/sub/pipe600", "fifo")))
case("fifo_without_D_skipped", specials, "-rlpt src/ dst/",
     verify=all_of(absent("dst/pipe"), present("dst/regular.txt")))
case("hardlinks_no_H", hardlinks, "-a src/ dst/",
     verify=all_of(same_file("src/h1", "dst/h2"),
                   lambda s: ["dst/h1 should not be hard-linked without -H"]
                   if s.get("dst/h1", {}).get("links") else []))

if sys.platform == "darwin":
    def immutable_dest(t):
        t.f("src/file", b"same", mode=0o644, mtime=T1)
        t.f("dst/file", b"same", mode=0o600, mtime=T1)
        os.chflags(t._p("dst/file"), stat.UF_IMMUTABLE)

    for transport, command in (
            ("local", "-a src/ dst/"),
            ("push", "-a " + R + " src/ fakehost:{ROOT}/dst/"),
            ("pull", "-a " + R + " fakehost:{ROOT}/src/ dst/")):
        case("attribute_failure_%s" % transport, immutable_dest, command, rc=23)

# ---- remote shell mode (via fakessh.sh) ------------------------------------
for transport, command in (
        ("local", "src/ dst/"),
        ("push", R + " src/ fakehost:{ROOT}/dst/"),
        ("pull", R + " fakehost:{ROOT}/src/ dst/")):
    for limit in (0, 1, 3):
        case("max_delete_%s_%d" % (transport, limit),
             B(plain, lambda t: t.f("dst/extra_a", b"a").f("dst/extra_b", b"b")),
             "-a --delete --max-delete=%d " % limit + command,
             rc=25 if limit < 2 else 0, skip=("dir-mtime",))
    case("delete_after_missing_source_%s" % transport,
         lambda t: t.f("dst/extra", b"keep"),
         "-a --delete " + command, rc=23, verify=present("dst/extra"))
    for limit in (0, 1, 2, 3):
        case("max_delete_nested_%s_%d" % (transport, limit),
             B(plain, lambda t: t.f("dst/extra_dir/a", b"a").f("dst/extra_dir/b", b"b")),
             "-a --delete --max-delete=%d " % limit + command,
             rc=25 if limit < 3 else 0, skip=("dir-mtime",))
case("remote_pull_wildcards", B(plain, emptydst),
     "-a " + R + " fakehost:{ROOT}/src/*.txt fakehost:{ROOT}/src/sub/*.txt dst/",
     verify=all_of(present("dst/a.txt", "dst/c.txt"), absent("dst/b.bin")))
case("remote_pull_wildcard_no_match", B(plain, emptydst),
     "-a " + R + " fakehost:{ROOT}/src/*.missing dst/", rc=23,
     verify=absent("dst/a.txt"))
case("remote_pull_wildcard_dirs", B(plain, emptydst),
     "-a " + R + " fakehost:{ROOT}/src/s*/ dst/",
     verify=all_of(present("dst/c.txt", "dst/deep/d.txt"), absent("dst/sub")))
case("remote_pull_wildcard_brackets", B(plain, emptydst),
     "-a " + R + " fakehost:{ROOT}/src/[ab].* dst/",
     verify=all_of(present("dst/a.txt", "dst/b.bin"), absent("dst/empty")))
case("remote_push_a", B(basic, emptydst), "-a " + R + " src/ fakehost:{ROOT}/dst/",
     verify=all_of(same_file("src/sub/deep/d.txt", "dst/sub/deep/d.txt"),
                   same_mtime("src/ns.txt", "dst/ns.txt")))
case("remote_pull_a", B(basic, emptydst), "-a " + R + " fakehost:{ROOT}/src/ dst/",
     verify=all_of(same_file("src/sub/deep/d.txt", "dst/sub/deep/d.txt"),
                   same_mtime("src/ns.txt", "dst/ns.txt")))
case("remote_push_az", B(basic, emptydst), "-az " + R + " src/ fakehost:{ROOT}/dst/",
     verify=same_file("src/sub/deep/d.txt", "dst/sub/deep/d.txt"))
case("remote_pull_az", B(basic, emptydst), "-az " + R + " fakehost:{ROOT}/src/ dst/",
     verify=same_file("src/sub/deep/d.txt", "dst/sub/deep/d.txt"))
case("remote_push_dest_missing", basic, "-a " + R + " src fakehost:{ROOT}/newdst",
     verify=present("newdst/src/a.txt"))
case("remote_pull_dest_missing", basic, "-a " + R + " fakehost:{ROOT}/src newdst",
     verify=present("newdst/src/a.txt"))
case("remote_push_az_delete_update", upd, "-az --delete " + R + " src/ fakehost:{ROOT}/dst/",
     verify=all_of(same_file("src/blob.bin", "dst/blob.bin"), absent("dst/extra.txt", "dst/extra_dir")))
case("remote_pull_az_delete_update", upd, "-az --delete " + R + " fakehost:{ROOT}/src/ dst/",
     verify=all_of(same_file("src/blob.bin", "dst/blob.bin"), absent("dst/extra.txt", "dst/extra_dir")))
case("remote_push_update_no_delete", upd, "-a " + R + " src/ fakehost:{ROOT}/dst/",
     verify=present("dst/extra.txt"))
case("remote_pull_checksum", upd, "-ac " + R + " fakehost:{ROOT}/src/ dst/",
     verify=same_file("src/sneaky.bin", "dst/sneaky.bin"))
case("remote_push_exclude", B(filt, filt_dst),
     "-a --delete --exclude=*.log --exclude=/foo --exclude=build/ " + R + " src/ fakehost:{ROOT}/dst/",
     verify=all_of(present("dst/stale.log", "dst/build/stale.o"), absent("dst/stale.txt")))
case("remote_pull_exclude", B(filt, filt_dst),
     "-a --delete --exclude=*.log --exclude=/foo --exclude=build/ " + R + " fakehost:{ROOT}/src/ dst/",
     verify=all_of(present("dst/stale.log", "dst/build/stale.o"), absent("dst/stale.txt")))
case("remote_pull_include_exclude", B(filt, emptydst),
     ["-a", "--include=*/", "--include=*.txt", "--exclude=*", "-e", "{SSH}", "--rsync-path={BIN}",
      "fakehost:{ROOT}/src/", "dst/"],
     verify=all_of(present("dst/sub/deep/c.txt"), absent("dst/a.log")))
case("remote_push_single_file", B(basic, emptydst), "-a " + R + " src/a.txt fakehost:{ROOT}/dst/renamed.txt",
     verify=same_file("src/a.txt", "dst/renamed.txt"))
case("remote_pull_single_file", B(basic, emptydst), "-a " + R + " fakehost:{ROOT}/src/a.txt dst/renamed.txt",
     verify=same_file("src/a.txt", "dst/renamed.txt"))
case("remote_pull_two_files", B(basic, emptydst),
     "-a " + R + " fakehost:{ROOT}/src/a.txt fakehost:{ROOT}/src/b.bin dst/",
     verify=present("dst/a.txt", "dst/b.bin"))
case("remote_push_spaces", spaces,
     ["-a", "-e", "{SSH}", "--rsync-path={BIN}", "src dir/", "fakehost:{ROOT}/dst dir/"],
     verify=present("dst dir/a file.txt", "dst dir/sub dir/b  two  spaces.txt"))
case("remote_pull_spaces", spaces,
     ["-a", "-e", "{SSH}", "--rsync-path={BIN}", "fakehost:{ROOT}/src dir/", "dst dir/"],
     verify=present("dst dir/a file.txt", "dst dir/sub dir/b  two  spaces.txt"))
case("remote_pull_spaces_single_file", spaces,
     ["-a", "-e", "{SSH}", "--rsync-path={BIN}", "fakehost:{ROOT}/src dir/a file.txt", "dst dir/new name.txt"],
     verify=present("dst dir/new name.txt"))
case("remote_push_weird_names", B(weird, emptydst), "-a " + R + " src/ fakehost:{ROOT}/dst/",
     verify=present("dst/new\nline.txt", "dst/-leading-dash.txt"))
case("remote_pull_weird_names", B(weird, emptydst), "-a " + R + " fakehost:{ROOT}/src/ dst/",
     verify=present("dst/new\nline.txt", "dst/-leading-dash.txt"))
case("remote_push_user_at_host", B(basic, emptydst), "-a " + R + " src/ someone@fakehost:{ROOT}/dst/",
     verify=present("dst/a.txt"))
case("remote_push_modes_symlinks", B(modes, symlinks, emptydst), "-a " + R + " src/ fakehost:{ROOT}/dst/",
     verify=present("dst/ro_dir/sub/deeper.txt", "dst/to_file"))
case("remote_pull_modes_symlinks", B(modes, symlinks, emptydst), "-a " + R + " fakehost:{ROOT}/src/ dst/",
     verify=present("dst/ro_dir/sub/deeper.txt", "dst/to_file"))
case("remote_push_large_delta", big_delta, "-a " + R + " src/ fakehost:{ROOT}/dst/",
     verify=same_file("src/big.bin", "dst/big.bin"), serial=True)
case("remote_pull_large_delta_z", big_delta, "-az " + R + " fakehost:{ROOT}/src/ dst/",
     verify=same_file("src/big.bin", "dst/big.bin"), serial=True)
case("remote_push_many_files", B(lambda t: many(t, "src", 800), emptydst),
     "-az " + R + " src/ fakehost:{ROOT}/dst/", verify=present("dst/big/f0799.dat"))
case("remote_pull_dry_run", upd, "-an --delete " + R + " fakehost:{ROOT}/src/ dst/", unchanged=0)
case("remote_pull_missing_source", emptydst, "-a " + R + " fakehost:{ROOT}/nonexistent/ dst/", rc=23)
case("remote_push_r_only", B(basic, emptydst), "-r " + R + " src/ fakehost:{ROOT}/dst/",
     verify=absent("dst/link_to_file"))


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

def make_removable(root):
    """chmod u+rwx every directory below root so rmtree cannot fail."""
    if not os.path.isdir(root) or os.path.islink(root):
        return
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            if hasattr(os, "chflags"):
                os.chflags(d, 0)
            os.chmod(d, 0o700)
            with os.scandir(d) as it:
                for entry in it:
                    if hasattr(os, "chflags") and not entry.is_symlink():
                        os.chflags(entry.path, 0)
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
        except OSError:
            pass


def wipe(path):
    make_removable(path)
    shutil.rmtree(path, ignore_errors=True)


def tool_env(home):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("RSYNC_") and k not in ("CVSIGNORE", "LC_ALL", "LANG")}
    env["HOME"] = home          # hermetic: no ~/.popt, no ~/.cvsignore
    env["LC_ALL"] = "C"
    env["TZ"] = "UTC"
    return env


def run_tool(argv, cwd, env, timeout):
    """Returns (exit_code_or_string, stdout, stderr).

    The tool gets its own process group so that on a timeout the whole family
    (client, fake ssh, "remote" server) can be killed; otherwise a stuck child
    holding the output pipes open would hang the harness as well.
    """
    try:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True)
    except OSError as exc:
        return "could not execute: %s" % exc.strerror, "", ""
    try:
        out, err = proc.communicate(timeout=timeout)
        rc = proc.returncode
        if rc < 0:
            rc = "killed by signal %d" % -rc
    except subprocess.TimeoutExpired:
        exited = proc.poll()
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:
            pass
        out, err = proc.communicate()
        if exited is None:
            rc = "timeout after %gs" % timeout
        else:
            rc = "exit %s, but child processes were still running after %gs" % (exited, timeout)
    return rc, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


def clip(textblock, limit=30):
    lines = textblock.rstrip("\n").split("\n") if textblock.strip() else []
    if len(lines) > limit:
        lines = lines[:limit] + ["... (%d more lines)" % (len(lines) - limit)]
    return lines


class Side:
    """Result of building the fixture and running every step with one tool."""

    def __init__(self):
        self.snaps = []     # snapshot before step 0, then after each step
        self.rcs = []
        self.outputs = []   # (argv, stdout, stderr)
        self.build_error = None


def run_side(c, cfg, side_name, binary):
    side = Side()
    root = os.path.join(cfg.tmp, c.name, side_name)
    os.makedirs(root, exist_ok=True)
    try:
        t = Tree(root)
        c.build(t)
        t.done()
    except Exception as exc:        # a fixture bug must not kill the whole run
        side.build_error = "%s: %s" % (type(exc).__name__, exc)
        if not cfg.keep:
            wipe(root)
        return side
    side.snaps.append(snapshot(root))
    subst = {"{BIN}": binary, "{SSH}": cfg.ssh, "{ROOT}": root}
    for step in c.steps:
        argv = [binary] + (c.ref_args if side_name == "ref" else [])
        if cfg.itemize and not ('--itemize-changes' in step or any(
                arg.startswith('-') and not arg.startswith('--') and 'i' in arg[1:] for arg in step)):
            argv.append('-i')
        for arg in step:
            for key, val in subst.items():
                arg = arg.replace(key, val)
            argv.append(arg)
        rc, out, err = run_tool(argv, root, cfg.env, cfg.timeout)
        side.rcs.append(rc)
        side.outputs.append((argv, out, err))
        side.snaps.append(snapshot(root))
    if not cfg.keep:
        wipe(root)
    return side


def run_case(c, cfg):
    """Returns (status, lines) where status is PASS, FAIL or ERROR."""
    start = time.time_ns() - 2 * 10**9
    if c.serial:
        ref = run_side(c, cfg, "ref", cfg.rsync)
        got = run_side(c, cfg, "got", cfg.xsync)
    else:
        fut = cfg.pool.submit(run_side, c, cfg, "ref", cfg.rsync)
        got = run_side(c, cfg, "got", cfg.xsync)
        ref = fut.result()
    window = (start, time.time_ns() + 2 * 10**9)
    _BIG_CACHE.clear()
    if not cfg.keep:
        wipe(os.path.join(cfg.tmp, c.name))

    verbose = []
    if cfg.verbose:
        for label, side in (("rsync", ref), ("xsync", got)):
            for (argv, out, err), rc in zip(side.outputs, side.rcs):
                verbose.append("[%s] $ %s" % (label, " ".join(shlex.quote(a) for a in argv)))
                verbose.append("[%s] exit code: %s" % (label, rc))
                verbose += ["[%s] stdout| %s" % (label, l) for l in clip(out)]
                verbose += ["[%s] stderr| %s" % (label, l) for l in clip(err)]

    # -- problems with the case itself (never the fault of the tool under test)
    if ref.build_error or got.build_error:
        return "ERROR", verbose + ["fixture construction failed: %s" % (ref.build_error or got.build_error)]
    pre = compare(ref.snaps[0], got.snaps[0], names=("first copy", "second copy"),
                  words=("first", "second"))
    if pre:
        return "ERROR", verbose + condense(
            ["fixture is not deterministic (the two copies differ before any tool ran):"] + pre)
    fresh = [p for p, e in ref.snaps[0].items() if window[0] <= e["mtime"] <= window[1]]
    if fresh:
        return "ERROR", verbose + ["fixture has paths without an explicit mtime: " + ", ".join(map(q, fresh[:5]))]
    problems = []
    for i, (want, have) in enumerate(zip(c.rc, ref.rcs)):
        if want is not None and want != have:
            problems.append("reference rsync exit code for step %d is %s but the case expects %s"
                            % (i + 1, have, want))
            problems += ["  rsync stderr| " + l for l in clip(ref.outputs[i][2], 4)]
    if c.verify and not problems:
        problems += ["reference rsync result is not what the case expects: " + m
                     for m in c.verify(ref.snaps[-1])]
    if c.unchanged is not None and not problems:
        d = compare(ref.snaps[c.unchanged], ref.snaps[-1], names=("tree before", "tree after"),
                    words=("before", "after"))
        if d:
            problems.append("reference rsync changed a tree the case expects to stay untouched:")
            problems += d
    if problems:
        return "ERROR", verbose + condense(problems)

    # -- differences between the reference and the tool under test
    diffs = []
    multi_step = len(c.steps) > 1
    for i, (a, b) in enumerate(zip(ref.rcs, got.rcs)):
        if a != b:
            where = " (step %d)" % (i + 1) if multi_step else ""
            diffs.append("exit code%s: expected=%s got=%s" % (where, a, b))
            diffs += ["  xsync stderr| " + l for l in clip(got.outputs[i][2], 3)]
        step = c.steps[i]
        itemize = cfg.itemize or '--itemize-changes' in step or any(
            arg.startswith('-') and not arg.startswith('--') and 'i' in arg[1:] for arg in step)
        if itemize and a == b:
            def file_lines(out):
                return sorted(line for line in out.splitlines() if
                              line.startswith('*deleting') or
                              (len(line) >= 12 and line[0] in '<>ch.' and line[1] in 'fdLDS' and line[11] == ' '))
            want, have = file_lines(ref.outputs[i][1]), file_lines(got.outputs[i][1])
            if want != have:
                import difflib
                diffs.append('itemized stdout differs at step %d:' % (i + 1))
                diffs += list(difflib.unified_diff(want, have, fromfile='rsync', tofile='xsync', lineterm=''))[:40]
    for i in range(1, len(ref.snaps)):
        d = compare(ref.snaps[i], got.snaps[i], skip=c.skip | cfg.skip, window=window, ignore=c.ignore)
        if d:
            if multi_step:
                diffs.append("tree after step %d:" % i)
            diffs += d
            break       # later steps only compound the first divergence
    if c.unchanged is not None:
        d = compare(got.snaps[c.unchanged], got.snaps[-1], skip=cfg.skip,
                    names=("tree before", "tree after"), words=("before", "after"))
        if d:
            diffs.append("xsync modified a tree that must stay untouched:")
            diffs += d
    if not diffs:
        return "PASS", verbose
    lines = ["$ xsync " + " ".join(shlex.quote(a) for a in step) for step in c.steps]
    return "FAIL", verbose + lines + condense(diffs)


def die(message):
    """Setup/usage problem (exit status 2; test failures exit with 1)."""
    sys.stderr.write("difftest: error: %s\n" % message)
    sys.exit(2)


def resolve_binary(path, what, hint):
    """Absolute path of an executable, or exit with a clear message."""
    cand = path
    if os.sep not in path:
        cand = shutil.which(path) or path
    cand = os.path.abspath(cand)
    if not os.path.isfile(cand):
        die("%s binary not found: %s\n%s" % (what, cand, hint))
    if not os.access(cand, os.X_OK):
        die("%s binary is not executable: %s" % (what, cand))
    return cand


def without_spaces(path, tmp, name):
    """rsync splits -e and --rsync-path on whitespace; if a path contains any,
    reach it through a symlink in the (whitespace-free) scratch directory."""
    if not any(ch.isspace() for ch in path):
        return path
    link_dir = os.path.join(tmp, ".bin-" + name)
    os.makedirs(link_dir, exist_ok=True)
    link = os.path.join(link_dir, os.path.basename(path).replace(" ", "_"))
    os.symlink(path, link)
    return link


def main():
    ap = argparse.ArgumentParser(
        description="Differential tests: run rsync and xsync on identical fixtures "
                    "and compare the resulting trees and exit codes.")
    ap.add_argument("--xsync", default=DEFAULT_XSYNC, metavar="PATH",
                    help="binary under test (default: build/xsync in the repo)")
    ap.add_argument("--rsync", default=DEFAULT_RSYNC, metavar="PATH",
                    help="reference rsync (default: %(default)s)")
    ap.add_argument("--keep", action="store_true",
                    help="keep the scratch directory (CASE/ref and CASE/got trees); the "
                         "whole suite leaves about 250 MB behind, so combine with -k")
    ap.add_argument("-k", dest="filter", action="append", default=[], metavar="SUBSTR",
                    help="only run cases whose name contains SUBSTR (repeatable)")
    ap.add_argument("-v", dest="verbose", action="store_true",
                    help="show the commands run and both tools' stdout/stderr")
    ap.add_argument("--list", action="store_true", help="list case names and exit")
    ap.add_argument("--itemize", action="store_true", help="request -i for every transfer and compare sorted file lines")
    ap.add_argument("--timeout", type=float, default=STEP_TIMEOUT, metavar="SECS",
                    help="kill a tool invocation after SECS seconds (default: %(default)s)")
    ap.add_argument("--no-symlink-times", action="store_true",
                    help="do not compare symlink mtimes in any case")
    ap.add_argument("--no-symlink-modes", action="store_true",
                    help="do not compare symlink permission bits in any case")
    args = ap.parse_args()
    try:        # file names in reports may not be encodable on an ASCII stdout
        sys.stdout.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass

    selected = [c for c in CASES
                if not args.filter or any(f in c.name for f in args.filter)]
    if args.list:
        for c in selected:
            print(c.name)
        return 0
    if not selected:
        die("no case matches -k %s" % " -k ".join(args.filter))

    class Cfg:
        pass
    cfg = Cfg()
    cfg.rsync = resolve_binary(args.rsync, "reference rsync",
                               "Pass --rsync PATH to point at GNU rsync 3.x.")
    cfg.xsync = resolve_binary(args.xsync, "xsync",
                               "Build it first, or pass --xsync PATH.")
    if not os.access(FAKESSH, os.X_OK):
        die("%s is missing or not executable" % FAKESSH)
    cfg.keep = args.keep
    cfg.timeout = args.timeout
    cfg.verbose = args.verbose
    cfg.itemize = args.itemize
    cfg.skip = frozenset((["symlink-mtime"] if args.no_symlink_times else []) +
                         (["symlink-mode"] if args.no_symlink_modes else []))

    os.umask(0o022)
    cfg.tmp = os.path.realpath(tempfile.mkdtemp(prefix="xsync-difftest-"))
    if any(ch.isspace() for ch in cfg.tmp):
        shutil.rmtree(cfg.tmp, ignore_errors=True)
        die("temp directory path contains whitespace: %s (set TMPDIR)" % cfg.tmp)
    home = os.path.join(cfg.tmp, ".home")
    os.mkdir(home)
    cfg.env = tool_env(home)
    cfg.ssh = without_spaces(FAKESSH, cfg.tmp, "ssh")
    cfg.rsync = without_spaces(cfg.rsync, cfg.tmp, "rsync")
    cfg.xsync = without_spaces(cfg.xsync, cfg.tmp, "xsync")

    print("reference: %s\nunder test: %s\nscratch:   %s" % (cfg.rsync, cfg.xsync, cfg.tmp))
    cfg.pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    counts = {"PASS": 0, "FAIL": 0, "ERROR": 0}
    failed = []
    t0 = time.time()
    try:
        for c in selected:
            tc = time.time()
            try:
                status, lines = run_case(c, cfg)
            except KeyboardInterrupt:
                raise
            except Exception as exc:     # harness bug: report it, keep going
                status, lines = "ERROR", ["harness exception: %s: %s" % (type(exc).__name__, exc)]
                if not cfg.keep:
                    wipe(os.path.join(cfg.tmp, c.name))
            counts[status] += 1
            if status != "PASS":
                failed.append(c.name)
            suffix = "  (%.2fs)" % (time.time() - tc) if cfg.verbose else ""
            print("%s %s%s" % (status, c.name, suffix))
            for line in lines:
                print("    " + line)
            sys.stdout.flush()
    except KeyboardInterrupt:
        print("\ninterrupted")
        counts["ERROR"] += 1
    finally:
        cfg.pool.shutdown(wait=True)
        if cfg.keep:
            print("kept scratch directory: %s" % cfg.tmp)
        else:
            wipe(cfg.tmp)

    total = sum(counts.values())
    summary = "%d passed, %d failed" % (counts["PASS"], counts["FAIL"])
    if counts["ERROR"]:
        summary += ", %d harness/case errors" % counts["ERROR"]
    print("\n%s (of %d cases) in %.1fs" % (summary, total, time.time() - t0))
    if failed:
        print("not passing: " + " ".join(failed))
    return 0 if counts["PASS"] == total else 1


if __name__ == "__main__":
    sys.exit(main())
