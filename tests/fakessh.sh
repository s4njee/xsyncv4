#!/bin/sh
# fakessh.sh - a stand-in for ssh that never touches the network.
#
# Usable as `rsync -e /abs/path/fakessh.sh ... fakehost:/path`.  It accepts
# the ssh command line rsync builds ([options] host command...), skips the
# ssh options, drops the host, and runs the remaining words joined by single
# spaces through `sh -c` -- which is what sshd does with the remote command.
# stdin/stdout/stderr are inherited, so the rsync protocol flows straight
# through to the "remote" process, which runs on this machine in the caller's
# working directory.

while [ $# -gt 0 ]; do
    case "$1" in
        --)
            shift
            break
            ;;
        # ssh options that take a separate argument: -l user, -p port, -o opt...
        -[BbcDEeFIiJLlmOopQRSWw])
            if [ $# -ge 2 ]; then shift 2; else shift; fi
            ;;
        # the same options with the argument attached (-p2222, -oFoo=bar),
        # and plain flags, possibly bundled (-x, -T, -4, -vv ...)
        -?*)
            shift
            ;;
        *)
            break
            ;;
    esac
done

if [ $# -lt 1 ]; then
    echo "fakessh: missing host argument" >&2
    exit 255
fi
shift   # the host name: ignored

if [ $# -lt 1 ]; then
    echo "fakessh: no remote command given (interactive logins unsupported)" >&2
    exit 255
fi

exec /bin/sh -c "$*"
