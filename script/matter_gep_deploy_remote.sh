#!/usr/bin/env bash
set -euo pipefail

# One-command deploy for both repositories:
# 1) Sync add-on source and rebuild/restart custom Matter add-on.
# 2) Sync core custom Matter integration into /config/custom_components/matter.
# 3) Inject manifest version key required for custom integrations.
# 4) Restart Home Assistant Core and tail logs.

: "${HA_USER:?Set HA_USER}"
: "${HA_HOST:?Set HA_HOST}"
HA_SSH_PORT="${HA_SSH_PORT:-22}"

CORE_REPO_DIR="${CORE_REPO_DIR:-/workspaces/homeassistant-core}"
ADDON_REPO_DIR="${ADDON_REPO_DIR:-/workspaces/homeassistant-addons}"

LOCAL_ADDON_DIR="${ADDON_REPO_DIR}/matter_server_gep"
REMOTE_ADDON_DIR="/addons/local/matter_server_gep"
LOCAL_CORE_MATTER_DIR="${CORE_REPO_DIR}/homeassistant/components/matter"
REMOTE_CORE_MATTER_DIR="/config/custom_components/matter"

SSH_TARGET="${HA_USER}@${HA_HOST}"

if [ ! -d "$LOCAL_ADDON_DIR" ]; then
  echo "Missing local add-on dir: $LOCAL_ADDON_DIR"
  exit 1
fi

if [ ! -d "$LOCAL_CORE_MATTER_DIR" ]; then
  echo "Missing local core matter dir: $LOCAL_CORE_MATTER_DIR"
  exit 1
fi

echo "[1/5] Syncing add-on source to HA host..."
rsync -avz --delete -e "ssh -p ${HA_SSH_PORT}" "$LOCAL_ADDON_DIR/" "${SSH_TARGET}:${REMOTE_ADDON_DIR}/"

echo "[2/5] Rebuilding/restarting custom Matter add-on..."
ssh -p "$HA_SSH_PORT" "$SSH_TARGET" <<'EOF'
set -euo pipefail

ha addons stop core_matter_server || true
if ha addons info local_matter_server_gep >/dev/null 2>&1; then
  ha addons rebuild local_matter_server_gep || true
  ha addons restart local_matter_server_gep || ha addons start local_matter_server_gep
else
  ha addons install local_matter_server_gep
  ha addons start local_matter_server_gep
fi
EOF

echo "[3/5] Syncing core custom integration to custom_components..."
rsync -avz --delete --exclude "__pycache__/" --exclude "*.pyc" -e "ssh -p ${HA_SSH_PORT}" "$LOCAL_CORE_MATTER_DIR/" "${SSH_TARGET}:${REMOTE_CORE_MATTER_DIR}/"

echo "[4/5] Injecting custom integration manifest version key..."
python - <<'PY' | ssh -p "$HA_SSH_PORT" "$SSH_TARGET" "cat > /config/custom_components/matter/manifest.json"
import json
from pathlib import Path

manifest = json.loads(
    Path("/workspaces/homeassistant-core/homeassistant/components/matter/manifest.json").read_text(encoding="utf-8")
)
manifest["version"] = "0.0.1"
print(json.dumps(manifest, indent=2, ensure_ascii=False))
PY

echo "[5/5] Restarting Home Assistant Core and tailing logs..."
ssh -p "$HA_SSH_PORT" "$SSH_TARGET" <<'EOF'
set -euo pipefail

ha core restart
ha core logs --tail 200
ha addons logs local_matter_server_gep --tail 120
EOF

echo "Deploy complete."
