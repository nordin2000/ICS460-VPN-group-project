"""Remove one site. Run from the lab folder: python3 remove.py north"""
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CONFIG = Path("/etc/wireguard/wg0.conf")

_KEY_LINE = re.compile(r"^\s*PublicKey\s*=\s*(\S+)\s*$", re.MULTILINE)


def _split_sections(conf_text: str) -> list[str]:
    """Split a WireGuard config into chunks, each starting at a [Section] line."""
    sections: list[list[str]] = [[]]
    for line in conf_text.splitlines(keepends=True):
        if line.lstrip().startswith("[") and sections[-1]:
            sections.append([])
        sections[-1].append(line)
    return ["".join(s) for s in sections if s]


def peers_in_conf(conf_text: str) -> list[str]:
    """Public keys of every [Peer] section."""
    keys = []
    for section in _split_sections(conf_text):
        if section.lstrip().startswith("[Peer]"):
            match = _KEY_LINE.search(section)
            if match:
                keys.append(match.group(1))
    return keys


def remove_peer_block(conf_text: str, public_key: str) -> tuple[str, bool]:
    """Remove the [Peer] block with this key. Matches by key, never by name."""
    kept, removed = [], False
    for section in _split_sections(conf_text):
        m = _KEY_LINE.search(section)
        if section.lstrip().startswith("[Peer]") and m and m.group(1) == public_key:
            removed = True
            continue
        kept.append(section)
    text = "".join(kept)
    return (re.sub(r"\n{3,}", "\n\n", text), removed)


def remove_from_hub(key):
    # This function runs inside the hub, where the config is stored.
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
    if len(sys.argv) == 3 and sys.argv[1] == "--key":
        # Internal mode: this runs inside the hub.
        remove_from_hub(sys.argv[2])
        return

    if len(sys.argv) != 2 or sys.argv[1] not in ("north", "east", "west"):
        raise SystemExit("Usage: python3 remove.py north|east|west")
    site = sys.argv[1]
    key = subprocess.check_output(
        ["docker", "compose", "exec", "-T", site, "cat", "/etc/wireguard/public.key"],
        text=True,
    ).strip()
    subprocess.run(["docker", "compose", "cp", "remove.py", "hub:/tmp/"], check=True)
    subprocess.run(
        ["docker", "compose", "exec", "-T", "hub", "python3", "/tmp/remove.py", "--key", key],
        check=True,
    )


if __name__ == "__main__":
    main()
