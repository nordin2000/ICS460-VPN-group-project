#!/usr/bin/env python3
"""Print a NetBird site-enrollment or user-setup plan. Dry-run only."""

import argparse
import json
import sys
from datetime import date

import vpnlib as lib


def plan_site(cfg: dict, args) -> None:
    name = lib.validate_name(args.name)
    lib.parse_site_exec(args.site)
    group = cfg["NETBIRD_GROUP"]
    body = lib.setup_key_body(name, f"<id of group {group}>", args.ephemeral,
                              date.today().isoformat())
    mgmt = cfg.get("NETBIRD_MANAGEMENT_URL", "")
    up = f"netbird up --setup-key-file <tmp file> --hostname {name}"
    if mgmt:
        up += f" --management-url {mgmt}"
    print(f"DRY RUN: enroll NetBird site {name!r}\n")
    print(f"1. GET /api/groups?name={group}  -> group ID (stop if missing: groups are Bundle B's)")
    print(f"2. GET /api/peers?name={name}  -> stop or exit 0 if it already exists")
    print(f"3. POST /api/setup-keys  {json.dumps(body)}")
    print("   (keep the returned key in memory only; it is shown in full just this once)")
    print(f"4. On {args.site}: check `netbird version`, write the key to a 0600 temp file,")
    print(f"   run `{up}`, then delete the temp file")
    print("5. Verify: `netbird status --check ready` on the site; poll "
          f"GET /api/peers?name={name} until connected and in {group}")
    print(f"6. Verify: ping {cfg['MUSEUM_SERVER_IP']} from the site "
          "(fails = enrolled, but Bundle B's policy may not allow it yet)")
    print("7. On failure: PUT /api/setup-keys/{id} {revoked: true} so the key can't be reused")


def plan_user(cfg: dict, args) -> None:
    group = cfg["NETBIRD_GROUP"]
    path = cfg.get("IDENTITY_PATH", "builtin")
    print(f"DRY RUN: prepare NetBird user {args.email!r} (identity path: {path})\n")
    print(f"1. GET /api/groups?name={group}  -> group ID")
    if path == "entra":
        print("2. User must already exist in Entra ID (Bundle B) and have logged in once")
        print("3. GET /api/users  -> pick the one user with this email (stop if 0 or 2+)")
        print("4. PUT /api/users/{id}  {role: <current>, auto_groups: [... + group ID], "
              "is_blocked: false}")
        print("5. If pending_approval: POST /api/users/{id}/approve")
    else:
        print("2. Self-hosted built-in login: POST /api/users/invites "
              f"{{email: {args.email}, name, role: user, auto_groups: [group ID]}}")
        print("   NetBird Cloud: POST /api/users {email, name, role: user, "
              "auto_groups: [group ID], is_service_user: false} (sends an invite)")
    print("Then: the person installs the client and logs in; every device they register")
    print(f"      lands in {group}. Verify by listing their peers once they have.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", required=True, help="KEY=VALUE config file")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, change nothing")
    ap.add_argument("--group", help="override NETBIRD_GROUP from the config")
    sub = ap.add_subparsers(dest="mode", required=True)
    s = sub.add_parser("site", help="enroll a headless site with a setup key")
    s.add_argument("--name", required=True)
    s.add_argument("--site", required=True, help="local, docker:<name> or ssh:<host>")
    s.add_argument("--ephemeral", action="store_true",
                   help="auto-remove after 10 min offline (for scaling tests)")
    s.add_argument("--dry-run", action="store_true", default=argparse.SUPPRESS)
    u = sub.add_parser("user", help="prepare a person's account")
    u.add_argument("--email", required=True)
    u.add_argument("--dry-run", action="store_true", default=argparse.SUPPRESS)
    args = ap.parse_args()

    try:
        cfg = lib.load_config(args.config)
        if args.group:
            cfg["NETBIRD_GROUP"] = args.group
        lib.require(cfg, "NETBIRD_API_URL", "NETBIRD_GROUP", "MUSEUM_SERVER_IP")
        if not args.dry_run:
            print("error: real changes are not built yet; rerun with --dry-run",
                  file=sys.stderr)
            return lib.EXIT_FAILED
        if args.mode == "site":
            plan_site(cfg, args)
        else:
            plan_user(cfg, args)
    except (ValueError, KeyError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return lib.EXIT_INPUT
    return lib.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
