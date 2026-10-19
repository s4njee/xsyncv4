# xs-rs

A Rust implementation of xs that is compatible with the C++ xs on the wire, so a C++ client can push
to or pull from a Rust server and the other way round. Developed by the VPS lab's engineer
(backlog-vps-lab.md, P5) against the lab's measurements and the mars lab's results.

The C++ protocol lives in `src/remote.cpp` and `src/common.h`; there is no separate written
specification, so the C++ source and its wire tests (`tests/*wire_test.py`) are the reference.

| Crate | What it holds |
|---|---|
| `xs-wire` | Frames, LEB128 and zigzag integers, strings, frame types, feature bits, HELLO and `F_MSG` |

```sh
cargo test --manifest-path rs/Cargo.toml                         # unit tests
XS_BIN=build/xs cargo test --manifest-path rs/Cargo.toml        # also against a C++ xs --server
```

The order of the port, each step proven against the C++ binary before the next:
1. the codec (`xs-wire`, seeded);
2. a server receiver (`--server`, role R) with core features, so a C++ client pushes to it;
3. a server sender (role S), so a C++ client pulls from it;
4. a client: ssh spawn, HELLO, the version-mismatch reply;
5. features in order of value: ZSTD, IDMAP, IO_CONTROL, OUTPUT, PROGRESS_ACK, DIR_CHILDREN, HLINK,
   RESUME, DELTA, filters, relative, files-from, xattrs, POSIX ACLs.
