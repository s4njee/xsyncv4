#!/usr/bin/env python3
"""Provision an isolated two-container SSH rig and run requested test modules."""
import pathlib
import subprocess
import tempfile
import uuid
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
IMAGE = "xsync-p0-rig"


def docker(*args, **kwargs):
    return subprocess.run(["docker", *map(str, args)], check=True, **kwargs)


def main():
    docker("build", "-t", IMAGE, "-f", REPO / "tests/rig/Dockerfile", REPO)
    tag = "xsync-rig-" + uuid.uuid4().hex[:10]
    network, client, server = tag + "-net", tag + "-client", tag + "-server"
    created, have_network = [], False
    with tempfile.TemporaryDirectory(prefix="xsync-ssh-keys-") as tmp:
        keys = pathlib.Path(tmp)
        key = keys / "id test"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], check=True)
        try:
            docker("network", "create", "--internal", network, capture_output=True)
            have_network = True
            for name, alias in ((server, "server"), (client, "client")):
                docker("run", "-d", "--name", name, "--network", network,
                       "--network-alias", alias, "-v", str(keys) + ":/keys:ro",
                       "-v", str(REPO / "tests") + ":/work/tests:ro", IMAGE, capture_output=True)
                created.append(name)
                docker("exec", name, "mkdir", "-p", "/rig")
            docker("cp", str(key) + ".pub", server + ":/root/.ssh/authorized_keys")
            docker("exec", server, "chown", "root:root", "/root/.ssh/authorized_keys")
            docker("exec", server, "chmod", "700", "/root/.ssh")
            docker("exec", server, "chmod", "600", "/root/.ssh/authorized_keys")
            docker("exec", "-d", server, "/usr/sbin/sshd", "-D", "-E", "/rig/sshd.log")
            modules = sys.argv[1:] or ["ssh_test.py"]
            for module in modules:
                print("Running " + module + " over real SSH", flush=True)
                filename, _, method = module.partition(':')
                docker("exec", "-e", "XSYNC_RIG_HOST=server", "-e", "XSYNC_TEST_BINARY=/usr/local/bin/xsync",
                       client, "python3", "/work/tests/" + filename, "-v", *([method] if method else []))
        except Exception:
            if server in created:
                subprocess.run(["docker", "exec", server, "cat", "/rig/sshd.log"])
            raise
        finally:
            for name in reversed(created):
                subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if have_network:
                subprocess.run(["docker", "network", "rm", network], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
