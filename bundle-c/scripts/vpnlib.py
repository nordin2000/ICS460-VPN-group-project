"""Shared helpers for Bundle C's VPN add/remove scripts.

Status (Progress Report 1):
  * Implemented and unit-tested: the pure helpers in this file (config
    loading, name checks, tunnel IP allocation, editing the hub's
    WireGuard config text, building NetBird API request bodies).
  * NOT built yet: anything that touches a real system (running `wg`,
    calling the NetBird API, running commands on a site). Those functions
    raise NotImplementedError. The entry-point scripts only work in
    --dry-run mode for now.

Command and API details follow the official docs:
  https://git.zx2c4.com/wireguard-tools/about/src/man/wg.8
  https://git.zx2c4.com/wireguard-tools/about/src/man/wg-quick.8
  https://docs.netbird.io/api
"""

from __future__ import annotations

import ipaddress
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

# Exit codes shared by all four scripts (see README).
EXIT_OK = 0            # success, or "already done"
EXIT_INPUT = 1         # bad arguments or config
EXIT_PRECONDITION = 2  # not found, missing group, ambiguous match, ...
EXIT_FAILED = 3        # the change itself failed (rollback attempted)
EXIT_VERIFY = 4        # change made, but verification failed

# Secrets are only ever read from environment variables, never the config file.
SECRET_KEYS = {"NETBIRD_API_TOKEN", "NETBIRD_SETUP_KEY"}

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,30}$")


def now_iso() -> str:
    """UTC timestamp used for the T0/T1 revocation-timing logs."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

def load_config(path: str | Path) -> dict[str, str]:
    """Read KEY=VALUE lines from a config file; environment variables win.

    Secret keys are refused if they appear in the file, so a token can never
    be committed by accident.
    """
    config: dict[str, str] = {}
    for lineno, raw in enumerate(Path(path).read_text().splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{lineno}: expected KEY=VALUE, got {raw!r}")
        key, value = (part.strip() for part in line.split("=", 1))
        if key in SECRET_KEYS:
            raise ValueError(
                f"{path}:{lineno}: {key} is a secret; set it as an environment "
                "variable instead of putting it in the config file"
            )
        config[key] = value
    for key in list(config) + sorted(SECRET_KEYS):
        if key in os.environ:
            config[key] = os.environ[key]
    return config


def require(config: dict[str, str], *keys: str) -> None:
    missing = [k for k in keys if not config.get(k)]
    if missing:
        raise KeyError("missing config values: " + ", ".join(missing))


def validate_name(name: str) -> str:
    """Peer names: lowercase letters, digits and dashes, up to 31 characters."""
    if not NAME_RE.match(name):
        raise ValueError(
            f"invalid name {name!r}: use lowercase letters, digits and dashes "
            "(e.g. site-wg-1), max 31 characters"
        )
    return name


def parse_site_exec(value: str) -> tuple[str, str | None]:
    """How to run commands on a site: 'local', 'docker:<container>' or 'ssh:<host>'."""
    if value == "local":
        return ("local", None)
    kind, _, target = value.partition(":")
    if kind in ("docker", "ssh") and target:
        return (kind, target)
    raise ValueError(f"SITE_EXEC must be local, docker:<name> or ssh:<host>, got {value!r}")


def run_on_site(site_exec: str, command: list[str]) -> str:
    """Run a command on a site and return its output. Not built yet."""
    raise NotImplementedError("running commands on sites is a Week 2 task")


# --------------------------------------------------------------------------
# WireGuard registry (WireGuard has no names, so the scripts keep their own)
# --------------------------------------------------------------------------

def load_registry(path: str | Path) -> dict:
    p = Path(path)
    if not p.exists():
        return {"peers": []}
    return json.loads(p.read_text())


def save_registry(path: str | Path, registry: dict) -> None:
    """Write atomically so a crash can't leave a half-written registry."""
    p = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(registry, indent=2) + "\n")
    tmp.replace(p)


def find_peer(registry: dict, name: str) -> dict | None:
    for entry in registry.get("peers", []):
        if entry.get("name") == name:
            return entry
    return None


def next_free_ip(subnet: str, hub_ip: str, registry: dict) -> str:
    """Lowest unused tunnel address in the subnet.

    Skips the hub, active peers, and revoked peers whose address has not
    been released yet (so old logs and test results stay unambiguous).
    """
    net = ipaddress.ip_network(subnet, strict=True)
    taken = {ipaddress.ip_address(hub_ip)}
    for entry in registry.get("peers", []):
        if entry.get("status") == "active" or not entry.get("released", False):
            taken.add(ipaddress.ip_address(entry["tunnel_ip"]))
    for host in net.hosts():
        if host not in taken:
            return str(host)
    raise RuntimeError(f"no free addresses left in {subnet}")


# --------------------------------------------------------------------------
# Hub config editing (pure text functions, so they can be unit-tested)
# --------------------------------------------------------------------------

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
    return [
        m.group(1)
        for section in _split_sections(conf_text)
        if section.lstrip().startswith("[Peer]")
        for m in [_KEY_LINE.search(section)]
        if m
    ]


def add_peer_block(conf_text: str, name: str, public_key: str, tunnel_ip: str) -> str:
    """Append a [Peer] block for a new site. Refuses duplicate keys."""
    if public_key in peers_in_conf(conf_text):
        raise ValueError("this public key is already in the hub config")
    block = (
        "\n[Peer]\n"
        f"# {name}\n"
        f"PublicKey = {public_key}\n"
        f"AllowedIPs = {tunnel_ip}/32\n"
    )
    return conf_text.rstrip("\n") + "\n" + block


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


def render_site_conf(tunnel_ip: str, hub_public_key: str, endpoint: str,
                     port: str, museum_ip: str, keepalive: bool = False) -> str:
    """Site config template. The private key is filled in ON the site, so it
    never passes through the admin machine."""
    lines = [
        "[Interface]",
        "PrivateKey = <inserted on the site>",
        f"Address = {tunnel_ip}/32",
        "",
        "[Peer]",
        f"PublicKey = {hub_public_key}",
        f"Endpoint = {endpoint}:{port}",
        f"AllowedIPs = {museum_ip}/32",
    ]
    if keepalive:
        lines.append("PersistentKeepalive = 25")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# NetBird helpers (pure; they build request bodies the API docs describe)
# --------------------------------------------------------------------------

def pick_exactly_one(items: list[dict], what: str) -> dict:
    """Never guess: stop if there are zero or several matches."""
    if not items:
        raise LookupError(f"no {what} found")
    if len(items) > 1:
        ids = ", ".join(str(i.get("id")) for i in items)
        raise LookupError(f"{len(items)} {what}s match ({ids}); refusing to guess")
    return items[0]


def setup_key_body(peer_name: str, group_id: str, ephemeral: bool, date: str) -> dict:
    """POST /api/setup-keys body: one-off, 1 day (the API minimum), 1 use."""
    return {
        "name": f"enroll-{peer_name}-{date}",
        "type": "one-off",
        "expires_in": 86400,
        "auto_groups": [group_id],
        "usage_limit": 1,
        "ephemeral": ephemeral,
    }


def group_update_without(group: dict, peer_id: str) -> dict:
    """PUT /api/groups/{id} replaces the whole group, so send every other
    member back unchanged and leave out just this one peer."""
    return {
        "name": group["name"],
        "peers": [p["id"] for p in group.get("peers", []) if p["id"] != peer_id],
    }


def user_update_body(user: dict, blocked: bool) -> dict:
    """PUT /api/users/{id} needs role, auto_groups and is_blocked together,
    so copy the current values and change only is_blocked."""
    return {
        "role": user["role"],
        "auto_groups": list(user.get("auto_groups", [])),
        "is_blocked": blocked,
    }


class NetBirdAPI:
    """Thin client for the NetBird REST API (header: 'Authorization: Token ...').

    Not built yet. Planned calls, all from https://docs.netbird.io/api :
      GET    /api/groups?name=<name>        resolve NETBIRD_GROUP to its ID
      POST   /api/setup-keys                create a one-off enrollment key
      PUT    /api/setup-keys/{id}           revoke an unused key
      GET    /api/peers?name=<name>         find a peer by name
      DELETE /api/peers/{id}                remove a device
      GET    /api/users                     find a user (filtered by email locally)
      PUT    /api/users/{id}                block / unblock, set default groups
      DELETE /api/users/{id}                remove a user from NetBird
      PUT    /api/groups/{id}               replace a group's member list
    """

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def request(self, method: str, path: str, body: dict | None = None):
        raise NotImplementedError("NetBird API calls are a Week 3 task")
