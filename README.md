# Museum VPN - ICS 460

A Docker museum network with plain WireGuard and centrally managed NetBird access.

| Folder | Work | Contributor |
| --- | --- | --- |
| [bundle-a](bundle-a/README.md) | Original museum server and practice network | Rose Nordin |
| [Bundle-B](Bundle-B/README.md) | NetBird user/group monitoring and policy configuration | Kanag Xiong |
| [bundle-c](bundle-c/README.md) | Integrated VPN lab and connection/removal scripts | Suraz Basnet |
| [bundle-d](bundle-d/README.md) | Test plan, measurements, graphs and results | Suraz Basnet |

## Run the combined lab

Start Docker Desktop, then follow [Bundle C](bundle-c/README.md) for WireGuard
and NetBird. The WireGuard lab has a museum server, hub and three remote sites.
NetBird uses the team workspace and its Staff/Volunteer policies.

Bundle A is the original standalone network. It shares a subnet with the
integrated WireGuard lab, so run these setups separately.

## Check the results

[Bundle D's report](bundle-d/results/results.txt) explains the live checks and
measurements. [The comparison PDF](bundle-d/results/comparison-and-scaling.pdf)
includes the access results, response times and scaling analysis.

From the repository root:

```sh
python3 -B -m unittest discover -s bundle-d/tests
sh bundle-d/measure.sh SERVER_NETBIRD_IP
```

The measurement command needs both VPN labs running and Staff access.

## How the parts fit

C includes the same museum page as A so the integrated lab runs from its own
folder. Both contain the identical small HTML resource. B supplies the team
policies; C exercises them against a controlled local service. D records the tests.

Imported sources: A `65c8ade`, B `4f27c32`. The original source branches retain
contribution history. B's extended setup note contains exposed credentials;
its original is kept in local private materials. Use a fresh private API token
when running B's monitoring program.

Local course documents, past reports, the checklist and presentation plan are
organized under `project-materials/`. Original logs/screenshots are in
`bundle-d/private/`.
