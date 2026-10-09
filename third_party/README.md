# Release dependencies

The original source archives are checked in so release builds require no dependency
downloads. `manifest.json` records their upstream URL and SHA-256; CMake verifies
the archive hash before extracting it. License notices are retained beside the
archives and inside the unmodified sources.

- [Zstandard 1.5.7](https://github.com/facebook/zstd/releases/tag/v1.5.7), BSD-3-Clause
  or GPL-2.0; xsync uses the BSD license.
- [xxHash 0.8.3](https://github.com/Cyan4973/xxHash/releases/tag/v0.8.3), BSD-2-Clause.
- [ICU 77.1](https://github.com/unicode-org/icu/releases/tag/release-77-1), Unicode
  License V3 and the notices included in `icu4c-LICENSE.txt`.

Static ICU retains Unicode normalization and full/simple case folding used by the
filename collision guard. Its data is linked into the binary rather than loaded
from the destination machine. See the [upstream static build documentation](https://unicode-org.github.io/icu/userguide/icu4c/build.html).
