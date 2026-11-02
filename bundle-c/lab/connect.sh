#!/bin/sh
# Set up the hub and client. Run from the lab folder.
set -eu

# Only public keys leave their containers.
hub_key=$(docker compose exec -T hub cat /etc/wireguard/public.key)
client_key=$(docker compose exec -T client cat /etc/wireguard/public.key)

# Hub settings: listen for the client and forward its traffic.
docker compose exec -T -e PEER_KEY="$client_key" hub sh -s <<'HUB'
set -eu
if ip link show wg0 >/dev/null 2>&1; then
    echo "Hub tunnel is already up. Stop it before reconfiguring." >&2
    exit 1
fi
umask 077
cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
PrivateKey = $(cat /etc/wireguard/private.key)
Address = 10.100.0.1/24
ListenPort = 51820
PostUp = iptables -t nat -A POSTROUTING -s 10.100.0.0/24 -d 172.30.0.10/32 -j MASQUERADE
PostDown = iptables -t nat -D POSTROUTING -s 10.100.0.0/24 -d 172.30.0.10/32 -j MASQUERADE

[Peer]
# local-client
PublicKey = $PEER_KEY
AllowedIPs = 10.100.0.2/32
EOF
wg-quick up wg0
HUB

# Client settings: send museum traffic through the hub.
docker compose exec -T -e PEER_KEY="$hub_key" client sh -s <<'CLIENT'
set -eu
if ip link show wg0 >/dev/null 2>&1; then
    echo "Client tunnel is already up. Stop it before reconfiguring." >&2
    exit 1
fi
umask 077
cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
PrivateKey = $(cat /etc/wireguard/private.key)
Address = 10.100.0.2/32

[Peer]
PublicKey = $PEER_KEY
Endpoint = 172.29.0.2:51820
AllowedIPs = 172.30.0.10/32
EOF
wg-quick up wg0
CLIENT

echo "VPN started. Try the museum webpage from the client."
