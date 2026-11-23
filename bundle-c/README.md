# Bundle C: museum VPN

This runs the museum page through WireGuard and NetBird on one laptop.
Rose supplied the museum page/server design (Bundle A, commit 65c8ade).
Kanag set up the team NetBird groups and policies (Bundle B).
Suraz built the VPN connection/removal scripts and local integration.

- `lab/`: WireGuard hub, museum server and north/east/west sites.
- `netbird/`: NetBird museum peer and client.
- [Bundle D](../bundle-d/README.md): tests, measurements and results.

## WireGuard

Start Docker Desktop. From `bundle-c/lab`:

```sh
docker compose up --build -d --remove-orphans
sh connect.sh
```

Each site has its own key and address. Test all three:

```sh
docker compose exec north curl --noproxy '*' --max-time 5 http://172.28.0.10/
docker compose exec east curl --noproxy '*' --max-time 5 http://172.28.0.10/
docker compose exec west curl --noproxy '*' --max-time 5 http://172.28.0.10/
```

All three should print the museum page. Remove east, then repeat the requests:

```sh
python3 remove.py east
```

East should time out. North and west should still work. Bring east back:

```sh
sh connect.sh east
```

Reconnecting may take a few seconds for a new handshake. To check saved removal,
remove east, reload the hub, and repeat the requests:

```sh
docker compose exec hub wg-quick down wg0
docker compose exec hub wg-quick up wg0
docker compose exec hub wg show
```

In our tests, north/west recovered about 15-16 seconds after reload; east stayed
removed. Repeating `python3 remove.py east` reports it is already removed.

Stop with `docker compose down`. Keys/configs stay in named volumes. Each startup
leaves the VPN off until `connect.sh` runs. For the before-VPN check, run a site
request before connecting and check that the hub can still load the page.

## NetBird

Use the team workspace. From `bundle-c/netbird`:

```sh
docker volume create ics460-netbird-check
docker compose up -d
docker compose exec server netbird up --disable-dns
docker compose exec client netbird up --disable-dns
```

The server volume reuses our original test enrollment when present. Keep the old
`ics460-netbird-check` container stopped while this stack runs.

Follow the login links and approve devices if prompted. Put the server in
Museum-Server and the client in Staff. Remove inherited Museum-Server membership
from the client. The existing team rules allow Staff all traffic to Museum-Server
and Volunteers TCP80; the default allow-all rule is disabled.

Find the server IP with `docker compose exec server netbird status`.
Replace SERVER_IP in these requests:

```sh
docker compose exec client wget -T 5 -qO- http://SERVER_IP/
docker compose exec client wget -T 5 -qO- http://SERVER_IP:8080/
```

Staff should reach both. Volunteers should reach only 80. A client with neither
role should reach neither. Check server health separately:

```sh
docker compose exec museum wget -T 5 -qO- http://127.0.0.1:8080/
```

Restore Staff after role testing. Stop with `docker compose down` from `netbird/`.
