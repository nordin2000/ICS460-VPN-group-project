"""Remove our test client. Run from the lab folder: python3 remove.py"""
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG = Path("/etc/wireguard/wg0.conf")


def remove_from_hub(key):
    # This function runs inside the hub, where the config is stored.
    from vpnlib import remove_peer_block, peers_in_conf

    old = CONFIG.read_text()
    new, changed = remove_peer_block(old, key)
    peers = subprocess.check_output(["wg", "show", "wg0", "peers"], text=True).split()
    if key not in peers and not changed:
        print("Client is already removed from live and saved configuration.")
        return

    backup = CONFIG.with_suffix(".conf.before-remove")
    if not backup.exists():
        backup.write_text(old)
        backup.chmod(0o600)

    subprocess.run(["wg", "set", "wg0", "peer", key, "remove"], check=True)
    print("T0 (live peer removed):", datetime.now(timezone.utc).isoformat())
    temp = CONFIG.with_suffix(".conf.tmp")
    temp.write_text(new)
    temp.chmod(0o600)
    temp.replace(CONFIG)

    peers = subprocess.check_output(["wg", "show", "wg0", "peers"], text=True).split()
    if key in peers or key in peers_in_conf(CONFIG.read_text()):
        raise RuntimeError("Removal verification failed")
    print("Client removed from live and saved configuration. Test webpage access next.")


def main():
    if len(sys.argv) == 2:
        # The hub receives the public key as an argument.
        remove_from_hub(sys.argv[1])
    else:
        # On the Mac, get the public key and send this script to the hub.
        key = subprocess.check_output(
            ["docker", "compose", "exec", "-T", "client", "cat", "/etc/wireguard/public.key"],
            text=True,
        ).strip()
        for source in ["remove.py", "../scripts/vpnlib.py"]:
            subprocess.run(["docker", "cp", source, "ics460c-hub:/tmp/"], check=True)
        subprocess.run(
            ["docker", "compose", "exec", "-T", "hub", "python3", "/tmp/remove.py", key],
            check=True,
        )


if __name__ == "__main__":
    main()
