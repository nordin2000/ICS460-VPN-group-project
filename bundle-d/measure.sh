#!/bin/sh
# Run from bundle-d: sh measure.sh SERVER_NETBIRD_IP
set -eu
cd "$(dirname "$0")"
server_ip=${1:?Usage: sh measure.sh SERVER_NETBIRD_IP}
mkdir -p private
output=$(mktemp -d "private/http-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")
image=curlimages/curl:8.12.1
docker image inspect "$image" >/dev/null 2>&1 || docker pull "$image"
printf 'setup,batch,trial,http_status,seconds,exit_code\n' > "$output/trials.csv"
docker version > "$output/docker-version.txt"
for setup in wireguard netbird; do
    if [ "$setup" = wireguard ]; then
        container=ics460c-north
        url=http://172.28.0.10/
    else
        container=ics460-netbird-client-1
        url=http://$server_ip/
    fi
    for batch in 1 2 3; do
        if [ "$setup" = netbird ]; then
            docker exec "$container" netbird status --detail > "$output/netbird-$batch-before.txt"
        fi
        docker run --rm --network "container:$container" --entrypoint sh "$image" -c '
            setup=$1
            batch=$2
            url=$3
            curl --version >&2
            curl -fsS --noproxy "*" --max-time 5 -o /dev/null "$url" || true
            for trial in 1 2 3 4 5 6 7 8 9 10; do
                curl -sS --noproxy "*" --max-time 5 -o /dev/null \
                    -w "$setup,$batch,$trial,%{http_code},%{time_total}," "$url"
                echo "$?"
            done
        ' sh "$setup" "$batch" "$url" >> "$output/trials.csv" 2>> "$output/curl-log.txt"
        if [ "$setup" = netbird ]; then
            docker exec "$container" netbird status --detail > "$output/netbird-$batch-after.txt"
        fi
    done
done
cat "$output/trials.csv"
echo "Saved in $output"
awk -F, 'NR > 1 && ($4 != 200 || $6 != 0) {failed=1} END {exit failed}' "$output/trials.csv"
