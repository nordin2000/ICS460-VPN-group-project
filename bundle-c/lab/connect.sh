#!/bin/sh
# Connect all three sites, or one: sh connect.sh north
set -eu
if [ "$#" -eq 0 ]; then
    set -- north east west
fi
for site in "$@"; do
    case "$site" in
        north|east|west) ;;
        *) echo "Choose north, east, or west." >&2; exit 1 ;;
    esac
done

hub_key=$(docker compose exec -T hub cat /etc/wireguard/public.key)
for site in "$@"; do
    case "$site" in
        north) address=10.100.0.2 ;;
        east) address=10.100.0.3 ;;
        west) address=10.100.0.4 ;;
    esac
    key=$(docker compose exec -T "$site" cat /etc/wireguard/public.key)

    # Keep existing peers; add this site to saved and live hub settings.
    docker compose exec -T -e PEER_KEY="$key" -e SITE_IP="$address" hub sh -s <<'HUB'
set -eu
umask 077
if [ ! -s /etc/wireguard/wg0.conf ]; then
    cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
PrivateKey = $(cat /etc/wireguard/private.key)
Address = 10.100.0.1/24
ListenPort = 51820
PostUp = iptables -t nat -A POSTROUTING -s 10.100.0.0/24 -d 172.28.0.10/32 -j MASQUERADE
PostDown = iptables -t nat -D POSTROUTING -s 10.100.0.0/24 -d 172.28.0.10/32 -j MASQUERADE
EOF
fi
if ! grep -Fq "PublicKey = $PEER_KEY" /etc/wireguard/wg0.conf; then
    cat >> /etc/wireguard/wg0.conf <<EOF

[Peer]
PublicKey = $PEER_KEY
AllowedIPs = $SITE_IP/32
EOF
fi
if ! ip link show wg0 >/dev/null 2>&1; then
    wg-quick up wg0
fi
wg set wg0 peer "$PEER_KEY" allowed-ips "$SITE_IP/32"
HUB

    docker compose exec -T -e HUB_KEY="$hub_key" -e SITE_IP="$address" "$site" sh -s <<'CLIENT'
set -eu
if ip link show wg0 >/dev/null 2>&1; then
    echo "Site tunnel already running."
    exit 0
fi
umask 077
cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
PrivateKey = $(cat /etc/wireguard/private.key)
Address = $SITE_IP/32

[Peer]
PublicKey = $HUB_KEY
Endpoint = 172.29.0.2:51820
AllowedIPs = 172.28.0.10/32
EOF
wg-quick up wg0
CLIENT
    echo "$site connected. Test the museum webpage next."
done
