#!/usr/bin/env python3
"""Add a remote site to the plain WireGuard baseline (the "before" system).

Lowest-priority script: the group plan allows dropping it if time runs short.
Status: --dry-run works; real changes are not built yet.

Example:
  python scripts/wg_add.py --config config.example --name site-wg-3 \
      --site docker:site-wg-3 --registry examples/sample-registry.json --dry-run
"""

import argparse
import sys
from datetime import date

import vpnlib as lib


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", required=True, help="KEY=VALUE config file")
    ap.add_argument("--name", required=True, help="peer name, e.g. site-wg-3")
    ap.add_argument("--site", required=True, help="local, docker:<name> or ssh:<host>")
    ap.add_argument("--registry", help="override WG_REGISTRY from the config")
    ap.add_argument("--keepalive", action="store_true", help="add PersistentKeepalive = 25")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, change nothing")
    args = ap.parse_args()

    try:
        cfg = lib.load_config(args.config)
        lib.require(cfg, "WG_INTERFACE", "WG_SUBNET", "HUB_TUNNEL_IP", "WG_PORT",
                    "MUSEUM_VPN_ENDPOINT", "MUSEUM_SERVER_IP", "HUB_CONF", "WG_REGISTRY")
        name = lib.validate_name(args.name)
        lib.parse_site_exec(args.site)
    except (ValueError, KeyError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return lib.EXIT_INPUT

    registry = lib.load_registry(args.registry or cfg["WG_REGISTRY"])
    existing = lib.find_peer(registry, name)
    if existing and existing.get("status") == "active":
        print(f"{name} is already an active peer ({existing['tunnel_ip']}); nothing to do")
        return lib.EXIT_OK
    try:
        ip = lib.next_free_ip(cfg["WG_SUBNET"], cfg["HUB_TUNNEL_IP"], registry)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return lib.EXIT_PRECONDITION

    iface = cfg["WG_INTERFACE"]
    if not args.dry_run:
        print("error: real changes are not built yet; rerun with --dry-run", file=sys.stderr)
        return lib.EXIT_FAILED

    print(f"DRY RUN: add WireGuard site {name!r} ({lib.now_iso()})\n")
    print(f"1. Tunnel IP: {ip} (next free in {cfg['WG_SUBNET']})")
    print(f"2. On site {args.site}: umask 077; wg genkey | tee private.key | wg pubkey")
    print("   (private key stays on the site; only the public key comes back)")
    print(f"3. On the hub: back up {cfg['HUB_CONF']}, then append:")
    block = lib.add_peer_block("", name, "<site public key>", ip)
    print("   " + block.strip().replace("\n", "\n   "))
    print(f"4. On the hub: wg syncconf {iface} <(wg-quick strip {iface})")
    print(f"5. On the site: write /etc/wireguard/{iface}.conf:")
    site_conf = lib.render_site_conf(ip, "<hub public key>", cfg["MUSEUM_VPN_ENDPOINT"],
                                     cfg["WG_PORT"], cfg["MUSEUM_SERVER_IP"], args.keepalive)
    print("   " + site_conf.strip().replace("\n", "\n   "))
    print(f"   then: wg-quick up {iface}")
    print(f"6. Verify: recent handshake in `wg show {iface} latest-handshakes`; "
          f"ping {cfg['MUSEUM_SERVER_IP']} from the site")
    print(f"7. Registry: add {{name: {name}, tunnel_ip: {ip}, status: active, "
          f"added: {date.today()}}}")
    print("\nOn any failure after step 3: remove the new peer block and re-sync the hub.")
    return lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
