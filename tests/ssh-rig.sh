#!/bin/sh
# Isolated real-SSH containers; run.py removes its containers, network and keys.
exec python3 "$(dirname "$0")/rig/run.py" "$@"
