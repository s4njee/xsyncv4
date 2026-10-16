#!/bin/sh
# Make the relay's shared secret: written to ~/.config/xsdash/relay.json for the
# Mac's dashboard server (readable only by you), and stored in the Worker with
# `wrangler secret put`. The secret is never printed. Run after `wrangler login`.
set -eu
dir="$HOME/.config/xsdash"
file="$dir/relay.json"
mkdir -p "$dir"
chmod 700 "$dir"
umask 077
secret=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
printf '{"url": "https://dashboard.mk7s.dev", "secret": "%s"}\n' "$secret" > "$file"
chmod 600 "$file"
cd "$(dirname "$0")"
printf '%s' "$secret" | wrangler secret put INGEST_SECRET
echo "secret stored in the Worker and in $file"
