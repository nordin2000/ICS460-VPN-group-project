FROM alpine:3.23
RUN apk add --no-cache wireguard-tools iproute2 iptables curl python3
COPY node-start.sh /usr/local/bin/node-start
RUN chmod +x /usr/local/bin/node-start
