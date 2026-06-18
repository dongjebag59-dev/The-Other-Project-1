#!/bin/bash
# Duck DNS 도메인 IP 갱신 스크립트 (cron 에서 5분마다 호출)
# 토큰/서브도메인은 argv 노출 피하려고 파일에서 읽음.

set -euo pipefail

DUCKDNS_DIR="${DUCKDNS_DIR:-$HOME/duckdns}"
TOKEN=$(cat "${DUCKDNS_DIR}/token")
SUBDOMAIN=$(cat "${DUCKDNS_DIR}/subdomain")
LOG="${DUCKDNS_DIR}/duck.log"

response=$(curl -sS -K - <<EOF
url = "https://www.duckdns.org/update?domains=${SUBDOMAIN}&token=${TOKEN}&ip=&verbose=true"
EOF
)

echo "[$(date -Iseconds)] ${response}" >> "${LOG}"

case "${response}" in
	OK*) exit 0 ;;
	*)   exit 1 ;;
esac
