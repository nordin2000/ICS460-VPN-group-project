#!/usr/bin/env python3
"""Print a NetBird removal plan. Dry-run only. Does not change the identity provider."""

import argparse
import sys

import vpnlib as lib

CAVEATS = {
    "peer": "not durable for a person: an active user could log in again and enroll "
            "a new device",
    "block-user": "effect on already-connected devices is unconfirmed; Bundle D must test it",
    "delete-user": "the identity-provider account is left untouched",
    "group": "only removes access granted through this group; changes Bundle B's groups",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", required=True, help="KEY=VALUE config file")
    ap.add_argument("--mode", required=True, choices=sorted(CAVEATS))
    ap.add_argument("--name", help="device name (peer and group modes)")
    ap.add_argument("--email", help="user email (block-user and delete-user modes)")
    ap.add_argument("--check-site", metavar="SITE_EXEC",
                    help="also confirm the device can no longer reach the museum (logs T1)")
    ap.add_argument("--ignore-missing", action="store_true",
                    help="exit 0 if the target is already gone")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, change nothing")
    args = ap.parse_args()

    try:
        cfg = lib.load_config(args.config)
        lib.require(cfg, "NETBIRD_API_URL", "MUSEUM_SERVER_IP")
        if args.mode in ("peer", "group"):
            if not args.name:
                raise ValueError(f"--mode {args.mode} needs --name")
            lib.validate_name(args.name)
        elif not args.email:
            raise ValueError(f"--mode {args.mode} needs --email")
        if args.mode == "group":
            lib.require(cfg, "NETBIRD_GROUP")
    except (ValueError, KeyError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return lib.EXIT_INPUT

    if not args.dry_run:
        print("error: real changes are not built yet; rerun with --dry-run", file=sys.stderr)
        return lib.EXIT_FAILED

    target = args.name or args.email
    print(f"DRY RUN: remove {target!r} from NetBird, mode {args.mode}\n")
    if args.mode in ("peer", "group"):
        print(f"1. GET /api/peers?name={args.name}  -> exactly one match "
              "(0: not found; 2+: stop and list them)")
    else:
        print("1. GET /api/users  -> exactly one user with this email")
    print(f"2. T0 = {lib.now_iso()}")
    if args.mode == "peer":
        print("3. DELETE /api/peers/{id}")
    elif args.mode == "block-user":
        print("3. PUT /api/users/{id}  {role: <current>, auto_groups: <current>, "
              "is_blocked: true}")
    elif args.mode == "delete-user":
        print("3. DELETE /api/users/{id}  (optionally delete the user's peers first)")
    else:
        print(f"3. GET /api/groups?name={cfg['NETBIRD_GROUP']}, then PUT /api/groups/{{id}} "
              "with every member except this device")
    print("4. Revoke any unused setup keys named enroll-<name>-* so the device can't re-enroll")
    print("5. Verify through the API that the change shows up")
    if args.check_site:
        print(f"6. Ping {cfg['MUSEUM_SERVER_IP']} from {args.check_site} until it fails; log T1")
    print(f"\nCaveat for this mode: {CAVEATS[args.mode]}")
    return lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
