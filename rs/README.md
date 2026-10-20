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

The order of the port (`benchmarks/lab/engineer.py`, `PORT_STEPS`), each step proven against the C++
binary before the next:
1. `config-frames`: the configuration frames after HELLO, in xs-wire;
2. `mvp`: one long session, planned by [HANDOFF.md](HANDOFF.md): the rest of the codec, a server that
   receives and sends, and a client, interoperating with the C++ xs and at least as fast as it;
3. features in order of value: ZSTD, IDMAP, IO_CONTROL, OUTPUT, HLINK, RESUME, DELTA, filters, xattrs,
   POSIX ACLs.
