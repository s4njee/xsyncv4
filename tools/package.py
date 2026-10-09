#!/usr/bin/env python3
"""Create a reproducible source archive and a usable local Homebrew formula."""
import gzip
import hashlib
import pathlib
import re
import subprocess
import tarfile

REPO = pathlib.Path(__file__).resolve().parent.parent


def main():
    version = re.search(r'#define XSYNC_VERSION "([^"]+)"', (REPO / 'src/common.h').read_text())[1]
    revision = subprocess.check_output(['git', 'rev-parse', '--short=12', 'HEAD'], cwd=REPO, text=True).strip()
    dirty = subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', 'src', 'cmake', 'tools', 'completions',
                            'CMakeLists.txt', 'CMakePresets.json'], cwd=REPO).returncode
    if dirty: revision += '-dirty'
    output = REPO / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / f'xsync-{version}-source.tar.gz'
    inputs = ['CMakeLists.txt', 'CMakePresets.json', 'README.md', 'backlog.md', 'src', 'cmake', 'tools',
              'completions', 'third_party', 'tests/filter_test.cpp']
    for name in ('xsync-linux-amd64', 'xsync-linux-arm64', 'xsync-darwin-universal', 'manifest.json'):
        if (output / name).is_file(): inputs.append('dist/' + name)
    files = []
    for item in inputs:
        path = REPO / item
        files.extend(p for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts) if path.is_dir() else files.append(path)
    with archive.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0, filename='') as compressed:
        with tarfile.open(fileobj=compressed, mode='w') as tar:
            for path in sorted(files):
                info = tar.gettarinfo(str(path), arcname=f'xsync-{version}/' + str(path.relative_to(REPO)))
                info.uid = info.gid = info.mtime = 0
                info.uname = info.gname = ''
                with path.open('rb') as contents: tar.addfile(info, contents)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    # Generated formula is local to this checkout; no public hosting is inferred.
    formula = f'''class Xsync < Formula
  desc "Parallel rsync work-alike with native SSH transfers and rsync fallback"
  url "{archive.as_uri()}"
  version "{version}"
  sha256 "{digest}"

  depends_on "cmake" => :build
  depends_on "ninja" => :build
  depends_on "python@3.14" => :build

  def install
    system "cmake", "-S", ".", "-B", "build", "-G", "Ninja",
           *std_cmake_args, "-DXSYNC_RELEASE_STATIC=ON", "-DXSYNC_BUILD_RELEASE_SET=OFF",
           "-DHOMEBREW_ALLOW_FETCHCONTENT=ON",
           "-DXSYNC_GIT_HASH={revision}"
    system "cmake", "--build", "build"
    system "cmake", "--install", "build"
  end

  test do
    (testpath/"source").write "installed executable works\\n"
    system bin/"xsync", "--no-fallback", "-a", testpath/"source", testpath/"destination"
    assert_equal (testpath/"source").read, (testpath/"destination").read
    assert_path_exists man1/"xsync.1"
    assert_path_exists share/"zsh/site-functions/_xsync"
  end
end
'''
    path = output / 'homebrew/Formula/xsync.rb'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(formula)
    print(f'Source: {archive}\nSHA-256: {digest}\nFormula: {path}')


if __name__ == '__main__':
    main()
