#!/usr/bin/env bash
set -euo pipefail

# Fast, non-destructive deploy loop for the custom Matter add-on.
# Syncs source and rebuilds/restarts without uninstalling the add-on.

: "${HA_USER:?Set HA_USER}"
: "${HA_HOST:?Set HA_HOST}"
HA_SSH_PORT="${HA_SSH_PORT:-22}"

LOCAL_ADDON_DIR="/workspaces/homeassistant-addons/matter_server_gep"
REMOTE_ADDON_DIR="/addons/local/matter_server_gep"
SSH_TARGET="${HA_USER}@${HA_HOST}"

if [ ! -d "$LOCAL_ADDON_DIR" ]; then
  echo "Missing local add-on dir: $LOCAL_ADDON_DIR"
  exit 1
fi

echo "Syncing add-on source to HA host..."
rsync -avz --delete -e "ssh -p ${HA_SSH_PORT}" "$LOCAL_ADDON_DIR/" "${SSH_TARGET}:${REMOTE_ADDON_DIR}/"

echo "Running remote rebuild/restart (non-destructive)..."
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

ha addons logs local_matter_server_gep --tail 200
EOF

echo "Done."
