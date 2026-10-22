You are implementing one change to xs, a parallel rsync work-alike in C++, in this checkout. A reviewer
(Claude Opus 5.5) read the lab's measurements and wrote the brief below. The goal is a faster copy on the lab's
Mac-to-Mac link (both ends macOS), fresh and no-op, with nothing else slower or less correct.

The node of the lab's decision tree: Compression for slow links
Its question: Where bytes are the limit, does better compression pay for its CPU?
What the lab will measure: A zstd dictionary trained on a corpus sample, and long-range mode, on lab2's internet link; negative levels on the 10 GbE cable (RQ-Z2).

The brief:
Scope this sitting to the part that runs on this link: negative (fast) zstd levels, plus an optional long-range flag. Dictionary training is left for later, since it needs lab2's internet link. Find where the transport sets up its zstd compressor and where the compression level option is parsed (search for ZSTD_createCCtx, ZSTD_c_compressionLevel and the compress-level option). Changes: (1) Accept negative levels in the option parser, validated against ZSTD_minCLevel()..ZSTD_maxCLevel(). Reject 0 explicitly or document it as zstd's default. (2) Pass the level through ZSTD_CCtx_setParameter(ZSTD_c_compressionLevel). (3) Add --zstd-long[=windowLog], which sets ZSTD_c_enableLongDistanceMatching and ZSTD_c_windowLog on the compressor. The decompressor must set ZSTD_d_windowLogMax to match, or reject the frame. Because the receiver needs to know this, carry the flag in the existing option negotiation, or fail cleanly if the peer lacks it. Edge cases: with -j4 each worker owns its own CCtx (no sharing); small files must not regress (keep the existing threshold below which data is sent uncompressed); level and long mode must apply identically on push and pull. Tests: a unit round-trip test compressing and decompressing random, text and incompressible buffers at levels -7, -1, 1 and 3, with and without long mode. Also add option-parse tests for out-of-range values. Keep the change under about 400 lines. Race to propose afterwards (RQ-Z2): no compression vs level -1 vs level -5 on the 10G link with the large and mixed-bimodal corpora.

Rules:
- Change only files under src/ and tests/, at most 600 lines in all. Keep the wire compatible with an xs that
  lacks any new feature: put protocol changes behind a new PF_ feature bit, negotiated as the existing ones are.
- Add or extend a test under tests/ that exercises the change.
- Build: cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release && cmake --build build --target xsync
- Check with the lab's suite, which the loop's gate runs too
  (env XSYNC_TEST_BINARY=$PWD/build/xs XSYNC_FALLBACK=0 python3 tests/<file>): destination_scope_test.py, delta_test.py, deletion_test.py, directory_lifetime_test.py, p0_test.py, wire_test.py, error_test.py, output_test.py, broken_stdout_test.py, list_test.py, filter_merge_test.py, prune_wire_test.py, defaults_test.py, dry_summary_test.py
- Do not commit, push or touch git branches: the loop commits your change after its gate passes.
