# Progress terminal verification

U-01 is **partial** as of 2026-10-10. Automated checks pass; native GUI
visual pass was reported successful by the user; its saved evidence path
is pending inspection.

Run `python3 tests/progress_test.py -v` for local PTY/tmux checks, and
`tests/ssh-rig.sh progress_test.py` for the isolated Linux real-SSH checks.
Each run uses disposable transfer directories and removes its own tmux server.

| Check | Result / evidence |
|---|---|
| PTY widths 1, 12, 32, 80, 120 | Pass: every frame fits within width minus one, valid UTF-8, cursor restored |
| UTF-8 paths, CJK and combining characters | Pass: clipping uses display columns |
| Tabs, ESC and invalid filename bytes under `-8` | Pass: controls escaped on macOS/Linux; invalid UTF-8 additionally covered on Linux (APFS rejects such names) |
| `LC_ALL=C` | Pass: ASCII bars/spinner and octal escaped high filename bytes |
| `TERM=dumb` | Pass: ASCII lines, no ANSI escapes |
| `NO_COLOR=1`, resize then interrupt | Pass: no SGR colors, cursor restored, exit 20 |
| tmux 3.7b, 120 → 18 → 90 columns | Pass: pre-transfer sentinel survives, no stale live bars after completion, cursor visible |
| Push over real SSH, Linux arm64 | Pass: same client renderer and cursor cleanup; no GUI terminal attached |
| Terminal.app, dark and light profiles | User reported manual pass on 2026-10-10; screenshots/version evidence path pending |
| iTerm, dark and light profiles | User reported manual pass on 2026-10-10; screenshots/version evidence path pending |

Local log: `/tmp/xsync-u01-pty2.log` (6 methods); real SSH log:
`/tmp/xsync-u01-real-ssh.log` (5 methods, tmux unavailable in the rig).
Output regression log: `/tmp/xsync-u01-output.log` (10 methods).

For the remaining visual pass, create a disposable source with a large file,
then run the development binary with `-a --no-clone --progress --bwlimit=512`.
Capture a frame at 80 columns, a narrow frame, and a light-profile frame. Resize
while transferring; verify earlier output survives, rows do not wrap, and the
cursor is visible after completion or Ctrl-C. Repeat inside tmux and with an
SSH transfer. Add screenshots and record terminal versions here before marking
U-01 done. Foreground-color bars are implemented, but light-theme legibility
was reported passed by the user; saved visual evidence has not yet been inspected.
