#!/usr/bin/env bash
# Start local subtensor (Docker), register SignOra subnet, run bootstrap.
set -euo pipefail

SUBTENSOR_ROOT="${SUBTENSOR_ROOT:-$(cd "$(dirname "$0")/../../subtensor-1" 2>/dev/null && pwd || echo "")}"
SIGNORA_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENDPOINT="${SUBTENSOR_ENDPOINT:-ws://127.0.0.1:9944}"

if [[ -z "$SUBTENSOR_ROOT" || ! -d "$SUBTENSOR_ROOT" ]]; then
  echo "Set SUBTENSOR_ROOT to your subtensor clone (e.g. ../subtensor-1)"
  exit 1
fi

echo "=== 1. Start local subtensor (Docker) ==="
cd "$SUBTENSOR_ROOT"
docker compose -f docker-compose.localnet.yml up alice -d
echo "Waiting for RPC on :9944..."
for i in $(seq 1 60); do
  if curl -s -H "Content-Type: application/json" \
    -d '{"id":1,"jsonrpc":"2.0","method":"system_health","params":[]}' \
    http://127.0.0.1:9944 >/dev/null 2>&1; then
    echo "Node ready."
    break
  fi
  sleep 2
  if [[ $i -eq 60 ]]; then
    echo "Timeout waiting for subtensor RPC"
    exit 1
  fi
done

cd "$SIGNORA_ROOT"
PY="${SIGNORA_ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY=python3
fi

echo "=== 2. Register SignOra subnet ==="
"$PY" scripts/register_local_subnet.py --endpoint "$ENDPOINT" || true

echo "=== 3. WLASL YouTube clips (small batch) ==="
"$PY" -m pip install -q yt-dlp 2>/dev/null || pip install -q yt-dlp
"$PY" scripts/prepare_wlasl_dataset.py \
  --with-youtube \
  --max-samples 5 \
  --pose-backend ensemble \
  --output data/training/wlasl_video_pairs.json || echo "YouTube download partial/failed — OK for devnet"

echo "=== 4. Train translator + challenge smoke ==="
"$PY" scripts/devnet_bootstrap.py --skip-dwpose --epochs 10

echo "=== 5. Challenge server (background) ==="
export SIGNORA_CHALLENGE_SECRET="${SIGNORA_CHALLENGE_SECRET:-devnet-secret}"
pkill -f "run_challenge_server.py" 2>/dev/null || true
nohup "$PY" scripts/run_challenge_server.py --port 8787 > /tmp/signora-challenge.log 2>&1 &
echo "Challenge server → http://127.0.0.1:8787/health (log: /tmp/signora-challenge.log)"

NETUID=$(cat data/local_netuid.txt 2>/dev/null || echo "?")
echo ""
echo "=== Done ==="
echo "Netuid: $NETUID"
echo "See docs/ASL_AND_POSE.md for WLASL/YouTube-ASL (ASL) vs DWPose (pose tracking)"
