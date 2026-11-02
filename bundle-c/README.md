# Bundle C

This is our local WireGuard test setup. It runs three Docker containers: a museum test webpage, a VPN hub, and a remote client.

Open Docker Desktop, then run these from the bundle-c folder:

```sh
cd lab
docker compose up --build -d
sh connect.sh
```

Try opening the museum page from the client:

```sh
docker compose exec client curl --max-time 5 http://172.30.0.10:8080/
```

It should print the webpage. To remove the client's access:

```sh
python3 remove.py
```

Run the same curl command again. It should time out. The museum server is still running, but the client can no longer reach it.

We tested that access fails before the VPN connects, works after connecting, and stops after removal. We also reloaded the hub's WireGuard settings and confirmed the client stayed blocked. Running removal again correctly says it is already removed. These checks passed on November 2. The 19 original helper tests also pass.

To stop the lab:

```sh
docker compose down
```

Docker keeps the keys in local volumes. Restart the containers before repeating the full test. If connect.sh stops halfway, check the error before trying again.

The files in scripts/ are the older dry-run starters. config.example is only sample input for those scripts; the lab does not use it. The working lab uses connect.sh and remove.py inside lab/. NetBird, the shared museum network, performance tests, and tests with more sites are still next steps.
