#!/bin/sh
# Run xsync with copy-on-write cloning disabled (exercises the plain copy path).
exec "$(dirname "$0")/../build/xs" --no-clone "$@"
