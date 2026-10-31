# Bundle C: VPN setup and automation

Scripts for adding and removing remote access in the two VPN setups the
project compares:

- **Plain WireGuard** (the "before"): keys and peer configs managed by hand.
- **NetBird** (the "after"): WireGuard underneath, managed centrally with
  single sign-on.

## Status (Progress Report 1, 2026-10-05)

| Part | Status |
| --- | --- |
| Helper functions in `scripts/vpnlib.py` (IP allocation, hub config editing, NetBird request bodies, config loading) | Implemented; 19 unit tests pass |
| `--dry-run` for all four scripts | Works; prints the exact plan |
| Real changes (running `wg`, calling the NetBird API, running commands on sites) | **Not built yet.** Without `--dry-run` the scripts stop with exit code 3 |

Nothing here has been run against a real VPN yet. Planned timeline: WireGuard
in week 2, NetBird in week 3, finished scripts handed to Bundle D in week 4.

## Layout

```
config.example          placeholders for values from Bundles A and B
scripts/vpnlib.py       shared helpers
scripts/wg_add.py       add a WireGuard site      (lowest priority; droppable)
scripts/wg_remove.py    revoke a WireGuard site
scripts/nb_add.py       enroll a NetBird site, or prepare a NetBird user
scripts/nb_remove.py    remove NetBird access (modes: peer, block-user, delete-user, group)
examples/               fake hub config and registry for dry runs and tests
tests/test_vpnlib.py    unit tests (no VPN, network or root needed)
```

## Try it

Requires Python 3.9+; no extra packages.

```
python -m unittest discover tests

python scripts/wg_add.py --config config.example --name site-wg-3 \
    --site docker:site-wg-3 --registry examples/sample-registry.json --dry-run

python scripts/wg_remove.py --config config.example --name site-wg-1 \
    --registry examples/sample-registry.json \
    --hub-conf examples/sample-hub-wg0.conf --check-site docker:site-wg-1 --dry-run

python scripts/nb_add.py --config config.example site --name site-nb-1 \
    --site docker:site-nb-1 --dry-run

python scripts/nb_add.py --config config.example --group prov-staff user \
    --email staff1@example.org --dry-run

python scripts/nb_remove.py --config config.example --mode peer \
    --name site-nb-1 --dry-run
```

## Config and secrets

Copy `config.example` to `config.env` and fill in real values once Bundles A
and B decide them. Until then, the placeholders let everything else proceed.

`NETBIRD_API_TOKEN` and setup keys are secrets. They come only from
environment variables; the scripts refuse to run if one appears in the config
file. Keep `config.env` and any `registry.json` out of git.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success, or already done |
| 1 | Bad arguments or config |
| 2 | Precondition failed (not found, missing group, ambiguous match) |
| 3 | The change failed (rollback attempted), or real mode not built yet |
| 4 | Change made, but verification failed |

## Design notes

- WireGuard has no usernames, so the scripts keep a small registry mapping
  names to public keys and tunnel addresses.
- The WireGuard remove script removes the peer from the running hub first
  (fastest revocation), then from the config file, so it can't come back after
  a restart.
- NetBird site enrollment uses one-off setup keys (one use, one day), so a
  deleted site can't quietly re-enroll.
- Remove scripts log T0 (change applied) and optionally T1 (device loses
  access) so Bundle D can measure revocation time.
- The scripts never create NetBird groups or policies; those belong to
  Bundle B.
