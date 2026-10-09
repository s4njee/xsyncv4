# Protocol compatibility fixture

`protocol3.tar.gz` freezes CMakeLists.txt, src/ and tests/filter_test.cpp from local
commit `29050650e074`, before protocol negotiation was added. Its SHA-256 and
protocol are recorded in `protocol3.json`. The compatibility tests compile this
peer independently and exercise actual old-client/new-server and
new-client/old-server transfers with fallback disabled.

Do not regenerate it from current sources: it protects the frozen protocol-3
layout and the historical server/client handshake. Add a new fixture when the
supported N/N-1 window advances.
