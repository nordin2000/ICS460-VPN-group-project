#!/bin/sh
set -eu

# Check that this container can create a WireGuard interface.
ip link add wg-probe type wireguard
ip link delete wg-probe

# Only VPN traffic can pass through the hub to the museum.
if [ "$1" = hub ]; then
    iptables -P FORWARD DROP
    iptables -A FORWARD -i wg0 -j ACCEPT
    iptables -A FORWARD -o wg0 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
fi

# Make keys on the first start. Reuse them on later starts.
umask 077
mkdir -p /etc/wireguard
if [ ! -s /etc/wireguard/private.key ]; then
    wg genkey > /etc/wireguard/private.key
fi
wg pubkey < /etc/wireguard/private.key > /etc/wireguard/public.key

echo "$1 ready. VPN is off until connect.sh runs."
exec sleep infinity
