# Bundle D: tests and results

Suraz collected these results on November 23, 2026 using the Bundle C lab.
Both VPN setups served Rose's museum page. NetBird used Kanag's team policies.

- `test-plan.txt`: checks, tools and pass criteria.
- `tests/`: Python checks for WireGuard removal.
- `measure.sh`: collect a new set of HTTP timings.
- `data/`: CSVs and recorded test outcomes.
- `evidence/`: command output with personal paths and account details redacted.
- `results/`: the report, graph and comparison/scaling tables.

Start with [the results](results/results.txt) or [the comparison PDF](results/comparison-and-scaling.pdf).

## Run the checks

From `bundle-d`:

```sh
python3 -B -m unittest discover -s tests
```

These five checks use temporary configs and mocked WireGuard commands.
They cover keeping the other peers, backups/permissions, repeat removal,
command failure and verification failure.

For HTTP measurements, start both Bundle C labs and give the NetBird client
Staff access. Then run:

```sh
sh measure.sh 100.89.247.26
```

Use your museum peer's NetBird IP. The script makes a new folder in `private/`
with 30 samples per VPN, command errors and connection status around each batch.
It uses the same pinned curl image in each client's network namespace.

## Read the numbers

The recorded WireGuard median was 1.178 ms; NetBird was 413.982 ms.
WireGuard stayed on local Docker networks. NetBird used an internet relay.
These numbers describe those paths. Compare access management and observed
behavior alongside response time.

The hub-reload trials recovered in about 15-16 seconds. Selective removal kept
the other sites working across all five trials. NetBird device deletion blocked
the disposable client; SSO re-enrollment and restoring Staff brought it back.

Screenshots and original verbatim logs are kept locally under `private/`.
The shared evidence keeps request output, timings and exits, with redacted paths
and account details. Historical commands describe the folder layout at test time.
