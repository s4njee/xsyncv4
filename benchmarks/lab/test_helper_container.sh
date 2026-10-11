#!/bin/sh
# Exercises xsbench-helper for real. Run it as root inside a disposable,
# privileged Linux container with iproute2 and e2fsprogs, never on a host:
#
#   docker run --rm --privileged -v "$PWD/benchmarks/lab:/lab:ro" IMAGE \
#     sh /lab/test_helper_container.sh
#
# It changes the container's qdisc, mounts a loop device and drops caches.
set -eu
PATH=/usr/sbin:/usr/bin:/sbin:/bin
[ "$(id -u)" -eq 0 ] || { echo "run as root in a container" >&2; exit 1; }
[ -f /.dockerenv ] || [ -n "${XSBENCH_ALLOW_HOST:-}" ] || { echo "refusing to run outside a container" >&2; exit 1; }

HELPER=/usr/local/sbin/xsbench-helper
CONF=/etc/xsbench-helper.conf
failures=0

install -o root -g root -m 0755 /lab/xsbench-helper "$HELPER"
write_conf() {
  printf '%s\n' "$@" >"$CONF"
  chown root:root "$CONF"
  chmod 0644 "$CONF"
}

# expect STATUS PATTERN COMMAND...: the command exits STATUS and its combined
# output contains PATTERN.
expect() {
  want=$1
  pattern=$2
  shift 2
  set +e
  output=$("$@" 2>&1)
  got=$?
  set -e
  if [ "$got" -eq "$want" ] && printf '%s' "$output" | grep -q -- "$pattern"; then
    echo "ok   $*"
  else
    echo "FAIL $* -> $got (wanted $want, /$pattern/)"
    printf '%s\n' "$output" | sed 's/^/       /'
    failures=$((failures + 1))
  fi
}

qdisc() { tc qdisc show dev eth0 root | head -n 1; }

write_conf interface=eth0 scratch=/mnt scratch_fstype=ext4
expect 0 'config=ok' "$HELPER" status
expect 0 'root=yes' "$HELPER" status
expect 0 'netem=off' "$HELPER" status
expect 0 'scratch_mounted=no' "$HELPER" status

# Configuration that a non-root user could have edited is refused.
chmod 0666 "$CONF"
expect 4 'writable' "$HELPER" netem set 5 0 30
chmod 0644 "$CONF"
write_conf 'interface=eth0;reboot'
expect 3 'not a valid name' "$HELPER" netem set 5 0 30
write_conf interface=nosuch0
expect 3 'does not exist' "$HELPER" netem set 5 0 30
write_conf interface=eth0 scratch=/mnt scratch_fstype=ext4

# netem: set, inspect, clear.
before=$(qdisc)
expect 0 'delay_ms=20' "$HELPER" netem set 20 0.5 600
expect 0 'netem' qdisc
expect 0 'delay 20ms' qdisc
expect 0 'loss 0.5%' qdisc
expect 0 'limit 100000' qdisc
expect 0 'netem=on' "$HELPER" status
expect 0 'netem_timer=on' "$HELPER" status
expect 0 'delay_ms=0' "$HELPER" netem set 0 0 600
expect 0 'netem=off' "$HELPER" netem clear
expect 0 'netem=off' "$HELPER" status
expect 0 'netem_timer=off' "$HELPER" status
if [ "$(qdisc)" = "$before" ]; then
  echo "ok   root qdisc restored: $before"
else
  echo "FAIL root qdisc is '$(qdisc)', was '$before'"
  failures=$((failures + 1))
fi
expect 0 'netem=off' "$HELPER" netem clear

# The lifetime clears netem without any further call.
expect 0 'lifetime_s=2' "$HELPER" netem set 5 0 2
sleep 4
expect 0 'netem=off' "$HELPER" status
expect 0 'netem_timer=off' "$HELPER" status

# A qdisc somebody configured is never replaced, and never removed by clear.
tc qdisc replace dev eth0 root handle 1: pfifo limit 100
expect 4 'refusing' "$HELPER" netem set 5 0 30
expect 0 'netem=off' "$HELPER" netem clear
expect 0 'pfifo 1:' qdisc
tc qdisc del dev eth0 root

# Scratch mount: only what fstab defines, only the expected type.
expect 3 'does not choose devices' "$HELPER" mount-scratch
truncate -s 64M /scratch.img
mkfs.ext4 -q -F /scratch.img
echo '/scratch.img /mnt ext4 loop,noauto 0 0' >>/etc/fstab
expect 0 'scratch_fstab=yes' "$HELPER" status
expect 0 'scratch_fstype=ext4' "$HELPER" mount-scratch
expect 0 'scratch_mounted=yes' "$HELPER" status
expect 0 'scratch_fstype=ext4' "$HELPER" mount-scratch
write_conf interface=eth0 scratch=/mnt scratch_fstype=xfs
expect 4 'expected xfs' "$HELPER" mount-scratch
write_conf interface=eth0
expect 3 'no scratch mount point' "$HELPER" mount-scratch
umount /mnt

# Without an fstab entry, only a UUID from the root-owned configuration mounts.
sed -i '/scratch.img/d' /etc/fstab
loop=$(losetup --find --show /scratch.img)
uuid=$(blkid -s UUID -o value "$loop")
write_conf interface=eth0 scratch=/mnt scratch_source=/dev/sda1
expect 3 'must be UUID=' "$HELPER" mount-scratch
write_conf interface=eth0 scratch=/mnt
expect 3 'does not choose devices' "$HELPER" mount-scratch
write_conf interface=eth0 scratch=/mnt "scratch_source=UUID=$uuid"
expect 0 'scratch_fstype=ext4' "$HELPER" mount-scratch
expect 0 'scratch_mounted=yes' "$HELPER" status
umount /mnt
losetup -d "$loop"

# Governor: containers usually expose no cpufreq; either answer is valid.
set +e
"$HELPER" governor performance >/tmp/governor.out 2>&1
governor_status=$?
set -e
case "$governor_status" in
  0)
    expect 0 'governor_saved=yes' "$HELPER" status
    expect 0 'governor=' "$HELPER" governor restore
    expect 0 'governor_saved=no' "$HELPER" status
    ;;
  3) echo "ok   governor performance -> 3 (no cpufreq here)" ;;
  *)
    echo "FAIL governor performance -> $governor_status"
    failures=$((failures + 1))
    ;;
esac
expect 0 'governor=' "$HELPER" governor restore

expect 0 'dropped=yes' "$HELPER" drop-caches

echo
if [ "$failures" -eq 0 ]; then echo "all helper checks passed"; else echo "$failures helper checks failed"; fi
[ "$failures" -eq 0 ]
