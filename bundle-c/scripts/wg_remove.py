#!/usr/bin/env python3
"""Revoke a remote site's access in the plain WireGuard baseline.

Removes the peer from the running hub first (fastest revocation), then from
the config file so it cannot come back after a restart. Logs T0 (change
applied) so Bundle D can measure how quickly access really disappears.
Status: --dry-run works; real changes are not built yet.

Example:
  python scripts/wg_remove.py --config config.example --name site-wg-1 \
      --registry examples/sample-registry.json \
      --hub-conf examples/sample-hub-wg0.conf --dry-run
"""

import argparse
import sys
from pathlib import Path

import vpnlib as lib


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", required=True, help="KEY=VALUE config file")
    ap.add_argument("--name", required=True, help="peer name to revoke")
    ap.add_argument("--registry", help="override WG_REGISTRY from the config")
    ap.add_argument("--hub-conf", help="override HUB_CONF from the config")
    ap.add_argument("--check-site", metavar="SITE_EXEC",
                    help="also confirm the site can no longer reach the museum (logs T1)")
    ap.add_argument("--wipe-site", metavar="SITE_EXEC",
                    help="also bring the site's tunnel down and delete its key and config")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, change nothing")
    args = ap.parse_args()

    try:
        cfg = lib.load_config(args.config)
        lib.require(cfg, "WG_INTERFACE", "HUB_CONF", "WG_REGISTRY", "MUSEUM_SERVER_IP")
        name = lib.validate_name(args.name)
    except (ValueError, KeyError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return lib.EXIT_INPUT

    registry = lib.load_registry(args.registry or cfg["WG_REGISTRY"])
    entry = lib.find_peer(registry, name)
    if entry is None:
        print(f"error: {name!r} is not in the registry", file=sys.stderr)
        return lib.EXIT_PRECONDITION

    hub_conf_path = Path(args.hub_conf or cfg["HUB_CONF"])
    conf_text = hub_conf_path.read_text() if hub_conf_path.exists() else ""
    key = entry["public_key"]
    if entry.get("status") == "revoked" and key not in lib.peers_in_conf(conf_text):
        print(f"{name} is already revoked; nothing to do")
        return lib.EXIT_OK

    if not args.dry_run:
        print("error: real changes are not built yet; rerun with --dry-run", file=sys.stderr)
        return lib.EXIT_FAILED

    iface = cfg["WG_INTERFACE"]
    new_text, removed = lib.remove_peer_block(conf_text, key)
    print(f"DRY RUN: revoke WireGuard site {name!r}\n")
    print(f"1. Registry: key {key[:8]}..., tunnel IP {entry['tunnel_ip']}")
    print(f"2. T0 = {lib.now_iso()}: wg set {iface} peer <key> remove   (live, immediate)")
    if removed:
        print(f"3. Back up {hub_conf_path}, remove this block, then "
              f"wg syncconf {iface} <(wg-quick strip {iface}):")
        old_peers = len(lib.peers_in_conf(conf_text))
        new_peers = len(lib.peers_in_conf(new_text))
        print(f"   peers in hub config: {old_peers} -> {new_peers}")
    else:
        print(f"3. Key not found in {hub_conf_path}; only the live removal is needed")
    print("4. Remove any per-site firewall rule on the hub (gateway mode)")
    print(f"5. Registry: status revoked, revoked_at T0, keep {entry['tunnel_ip']} reserved")
    if args.wipe_site:
        print(f"6. On {args.wipe_site}: wg-quick down {iface}; delete its config and key")
    print(f"Verify: key absent from `wg show {iface} peers` and from the config file")
    if args.check_site:
        print(f"Verify: ping {cfg['MUSEUM_SERVER_IP']} from {args.check_site} until it fails; "
              "log T1")
    return lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
