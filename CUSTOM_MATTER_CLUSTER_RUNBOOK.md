# Home Assistant Matter Custom Cluster Runbook (GEP)

This guide is a repeatable, from-scratch procedure to patch Home Assistant Core and a local Matter Server add-on so a custom vendor cluster is discovered and writable.

It assumes:

- HA Core source repo is available at `/workspaces/homeassistant-core`.
- You have a separate add-ons repo (for example on macOS host): `/Users/O28845/homeassistant-addons`.
- Your HA instance is HA OS with Supervisor (so `ha` CLI commands are available on host).

## 1) Target Design (What "Good" Looks Like)

- Exactly one Matter server binds port `5580`.
- HA Matter integration points to your local custom add-on slug: `local_matter_server_gep`.
- Custom cluster ID `0xFFF1FC00` is:
  - known by HA Core (entity discovery layer), and
  - registered in Matter Server runtime (server-side cluster registry).

## 2) Prerequisites

## 2.1 Devcontainer workspace setup

If your add-ons repo is on your host machine, mount it into the devcontainer.

1. Open `/workspaces/homeassistant-core/.devcontainer/devcontainer.json`.
2. Add a bind mount entry in `mounts`:

```json
"mounts": [
  "source=/Users/O28845/homeassistant-addons,target=/workspaces/homeassistant-addons,type=bind,consistency=cached"
]
```

3. Rebuild/reopen container.
4. Verify both repos exist:

```bash
ls -la /workspaces
```

Expected: both `homeassistant-core` and `homeassistant-addons`.

## 2.2 Prepare HA Core environment

From `/workspaces/homeassistant-core`:

```bash
script/setup
```

## 3) Patch Home Assistant Core

Use your feature branch in `homeassistant-core`:

```bash
cd /workspaces/homeassistant-core
git checkout -b add_custom_cluster
```

## 3.1 Add custom cluster descriptors and entities

Implement/verify these files:

- `homeassistant/components/matter/custom_clusters.py`
- `homeassistant/components/matter/number.py`
- `homeassistant/components/matter/sensor.py`

Required constant:

- `GEP_CUSTOM_CLUSTER_ID = 0xFFF1FC00`

Required behavior:

- Add entity descriptions for your custom attributes (for example target flow rate and target ratio).
- Ensure any unit fallbacks needed by your Python/runtime version are present.

Hook-safe implementation notes from this session:

- In core integration code, do not add `version` to `homeassistant/components/matter/manifest.json`; this fails `hassfest` for built-in integrations.
- If you need compatibility fallbacks for ratio/density units, prefer module-level constants instead of reassigning imported types. Example pattern:

```python
try:
  from homeassistant.const import UnitOfRatio
except ImportError:
  UNIT_OF_RATIO_PERCENTAGE = PERCENTAGE
  UNIT_OF_RATIO_PARTS_PER_MILLION = "ppm"
else:
  UNIT_OF_RATIO_PERCENTAGE = UnitOfRatio.PERCENTAGE
  UNIT_OF_RATIO_PARTS_PER_MILLION = UnitOfRatio.PARTS_PER_MILLION
```

- Use `\u03bc` (Greek mu) for micro-unit fallback strings (for example `"\u03bcg/m\u00b3"`) to satisfy pylint custom rules.
- For CHIP classes imported as untyped `Any`, targeted `# type: ignore[misc]` on subclass lines may be required to satisfy mypy.

## 3.2 Point integration to local custom add-on

Edit `homeassistant/components/matter/const.py` so:

```python
ADDON_SLUG = "local_matter_server_gep"
```

## 3.3 Ensure custom integration manifest has version

If using custom component override under `/config/custom_components/matter`, ensure its `manifest.json` contains:

```json
"version": "0.0.1"
```

Without this, HA blocks custom integration loading.

## 3.4 Optional hardening for empty entry cases

If you hit startup race/index errors around Matter entry access, harden `homeassistant/components/matter/helpers.py` so missing loaded entries fail gracefully (instead of `IndexError`).

## 3.5 Verify no syntax/errors in changed files

```bash
python -m compileall homeassistant/components/matter
```

## 4) Patch Local Matter Add-on

Use your add-ons repo:

```bash
cd /workspaces/homeassistant-addons
git checkout -b add_custom_cluster
```

Use this repo directory:

`matter_server_gep/`

Important naming convention:

- Source repo directory/slug in `config.yaml`: `matter_server_gep`
- HA Supervisor add-on slug used in commands: `local_matter_server_gep`

## 4.1 Add-on metadata

`matter_server_gep/config.yaml`:

- Set slug to `matter_server_gep` and name to `Matter Server (GEP)`.
- Ensure startup/network permissions match Matter server needs.

`matter_server_gep/build.yaml`:

- Keep architecture/base config valid for your HA OS target.
- Current working base in this repo is `8.5.0` for both `aarch64` and `amd64`.

## 4.2 Add cluster patch payload file

Canonical source file in this repo:

- `matter_server_gep/gep_custom_cluster.py`

Current repo also contains mirrored copies at:

- `matter_server_gep/rootfs/opt/gep_custom_cluster.py`
- `matter_server_gep/rootfs/tmp/gep_custom_cluster.py`

If you edit the canonical file, sync mirrors before deploying:

```bash
cp /workspaces/homeassistant-addons/matter_server_gep/gep_custom_cluster.py /workspaces/homeassistant-addons/matter_server_gep/rootfs/opt/gep_custom_cluster.py
cp /workspaces/homeassistant-addons/matter_server_gep/gep_custom_cluster.py /workspaces/homeassistant-addons/matter_server_gep/rootfs/tmp/gep_custom_cluster.py
```

## 4.3 Patch Matter Server at container build time

In `matter_server_gep/Dockerfile`, keep a deterministic patch step that:

1. Locates the installed `matter_server` package path.
2. Writes/installs `gep_custom_cluster.py` into package space.
3. Patches server cluster registry so `ALL_CLUSTERS` and `ALL_ATTRIBUTES` include your custom cluster.

Important constraints:

- Do not rely on missing binaries (`python3` may not exist in some base images; use available interpreter).
- Keep patching idempotent (safe on rebuild/restart).
- Ensure Docker build context includes any `COPY` sources.

## 4.4 Sync add-on source to HA host local add-ons

From devcontainer:

```bash
rsync -avz --delete -e "ssh -p ${HA_SSH_PORT}" /workspaces/homeassistant-addons/matter_server_gep/ ${HA_USER}@${HA_HOST}:/addons/local/matter_server_gep/
```

## 4.5 Build and install local add-on

On HA host terminal:

```bash
ha addons rebuild local_matter_server_gep
ha addons install local_matter_server_gep
ha addons start local_matter_server_gep
```

If `rebuild` is unavailable on your version, use:

```bash
ha addons restart local_matter_server_gep
```

## 5) Enforce Single Matter Server Ownership (Critical)

Port conflict (`Errno 98` on `172.30.32.1:5580`) happens when multiple servers run.

On HA host:

```bash
ha addons stop core_matter_server || true
ha addons uninstall core_matter_server || true
ha addons stop matter-server || true
ha addons uninstall matter-server || true
```

Then ensure custom one is running:

```bash
ha addons start local_matter_server_gep
ha addons logs local_matter_server_gep --follow
```

## 6) Bind HA Integration to Custom Server

You must ensure the running Matter integration instance is the custom one that uses:

- `ADDON_SLUG = "local_matter_server_gep"`

If HA keeps recreating `core_matter_server`, remove the old Matter integration instance and add it again after your patched custom component is in place.

## 7) Deploy Core Patch to Running HA

If you are deploying via custom component override:

1. Copy patched `matter` integration folder to `/config/custom_components/matter`.
2. Restart HA Core.

From devcontainer, sync core integration code to HA host:

```bash
export HA_USER=root
export HA_HOST=<your-ha-host-or-ip>
export HA_SSH_PORT=22222

LOCAL_MATTER_DIR=/workspaces/homeassistant-core/homeassistant/components/matter/
rsync -avz --delete --exclude "__pycache__/" --exclude "*.pyc" -e "ssh -p ${HA_SSH_PORT}" "$LOCAL_MATTER_DIR" "${HA_USER}@${HA_HOST}:/config/custom_components/matter/"

# REQUIRED for custom integration loading:
# inject a version key into the deployed custom-components manifest only.
# Do NOT add version to the core source manifest in this repository.
python - <<'PY' | ssh -p "${HA_SSH_PORT}" "${HA_USER}@${HA_HOST}" "cat > /config/custom_components/matter/manifest.json"
import json
from pathlib import Path

manifest = json.loads(
  Path("/workspaces/homeassistant-core/homeassistant/components/matter/manifest.json").read_text(encoding="utf-8")
)
manifest["version"] = "0.0.1"
print(json.dumps(manifest, indent=2, ensure_ascii=False))
PY
```

Optional verification on HA host:

```bash
ssh -p "${HA_SSH_PORT}" "${HA_USER}@${HA_HOST}" "ls -la /config/custom_components/matter && grep -n 'ADDON_SLUG' /config/custom_components/matter/const.py"
```

HA host commands:

```bash
ha core restart
ha core logs --follow
```

Check for custom integration load success and no manifest/version error.

## 8) Validate End-to-End Function

## 8.1 Server startup validation

Watch add-on logs and confirm:

- no bind error on `5580`
- no import/runtime patch failure
- Matter server starts successfully

## 8.2 Device commissioning

Commission/recommission one test device from Matter integration UI.

## 8.3 Custom attribute write test

Trigger write via HA entity/service and confirm:

- Matter server logs show write path processed
- device serial logs show `WriteRequest` followed by `WriteResponse` status `0x00`

## 8.4 Run healthcheck script

From repo root:

```bash
cd /workspaces/homeassistant-core
bash script/matter_gep_healthcheck.sh
```

Expected: overall `PASS` when topology and recent logs are healthy.

## 9) Troubleshooting Matrix

## 9.1 `Errno 98` / address already in use (5580)

Cause: two Matter servers running.

Fix:

- stop/uninstall `core_matter_server` and any rogue `matter-server`
- run only `local_matter_server_gep`

## 9.2 `python3: command not found` in add-on container

Cause: base image lacks `python3` binary path.

Fix:

- use available interpreter in Dockerfile patch step
- verify with build-time `which` checks

## 9.3 `COPY ... not found` during Docker build

Cause: file not in Docker build context.

Fix:

- place source file under add-on directory
- verify `.dockerignore` does not exclude it

## 9.4 custom component blocked by manifest

Cause: missing `version` in custom integration `manifest.json`.

Fix:

- add a semantic version string (for example `0.0.1`)

## 9.5 Entities unavailable after seemingly successful startup

Cause candidates:

- HA bound to wrong add-on slug
- old Matter integration instance still linked to core add-on
- server-side cluster not registered even if HA descriptors exist

Fix:

- verify `ADDON_SLUG`
- recreate integration if needed
- confirm runtime registry patch in Matter Server

## 10) Recommended Validation Commands

From HA host:

```bash
ha addons list
ha addons logs local_matter_server_gep --tail 200
ha supervisor logs --tail 200
ha core logs --tail 200
```

From devcontainer (`homeassistant-core`):

```bash
git status
grep -RIn "local_matter_server_gep\|0xFFF1FC00\|4294048768" homeassistant/components/matter script || true
```

## 11) Repeatable Clean-Restart Procedure

Use this sequence whenever behavior gets inconsistent:

1. Stop all Matter server add-ons.
2. Start only `local_matter_server_gep`.
3. Restart HA Core.
4. Verify logs for bind/import errors.
5. Run healthcheck script.
6. Recommission one test device and run one write test.

## 12) Commit Checklist

Core repo (`/workspaces/homeassistant-core`):

```bash
git add homeassistant/components/matter script/matter_gep_healthcheck.sh CUSTOM_MATTER_CLUSTER_RUNBOOK.md
git commit -m "Add runbook and custom Matter cluster gep wiring"
```

Add-ons repo (`/workspaces/homeassistant-addons`):

```bash
git add matter_server_gep
git commit -m "Patch local Matter add-on for GEP custom cluster"
```

Pre-commit workflow notes:

- Use `prek run --all-files` from an activated environment.
- Avoid `uv run prek run --all-files` for this repo on host machines; it may create a fresh env that does not include `prek`.
- If all-files mypy fails on known `.py` + `.pyi` duplicate-module paths unrelated to your changes, prefer normal staged commit hooks and/or run targeted mypy on changed files.

Host toolchain notes (macOS):

- Keep Xcode/clang current when running host `script/setup` with Python 3.14.
- If host native builds keep failing, commit and run checks from devcontainer.

---

## 13) Appendix A: Session-Proven Embedded Dockerfile (No COPY Context Dependency)

Use this on the HA host to generate a Dockerfile that embeds your live `/config/gep_custom_cluster.py` directly. This avoids the build-context `2B` and `COPY ... not found` failure mode.

```bash
set -euo pipefail

APP_DIR=/addons/local/matter_server_gep
CLUSTER_FILE=/config/gep_custom_cluster.py

if [ ! -f "$CLUSTER_FILE" ]; then
  echo "Missing $CLUSTER_FILE"
  exit 1
fi

CLUSTER_B64="$(base64 -w0 "$CLUSTER_FILE")"

cat > "$APP_DIR/Dockerfile" <<EOF
ARG BUILD_FROM
FROM \${BUILD_FROM}

RUN python3 - <<'PY'
from pathlib import Path
import base64
import matter_server.server as ms

cluster_src = base64.b64decode("${CLUSTER_B64}").decode("utf-8")

server_dir = Path(ms.__file__).parent
cluster_file = server_dir / "gep_custom_cluster.py"
cluster_file.write_text(cluster_src, encoding="utf-8")

init_file = server_dir / "__init__.py"
text = init_file.read_text(encoding="utf-8")
inject = "from . import gep_custom_cluster\\n"

if inject not in text:
  marker = "from .server import MatterServer\\n"
  if marker in text:
    text = text.replace(marker, marker + inject)
  else:
    text += "\\n" + inject
  init_file.write_text(text, encoding="utf-8")

print(f"Patched Matter Server package at: {server_dir}")
print(f"Wrote custom cluster module: {cluster_file}")
PY
EOF

# Optional safety: do not exclude needed files accidentally
: > "$APP_DIR/.dockerignore"

# Force fresh build by bumping version
sed -i 's/^version:.*/version: 9.0.10/' "$APP_DIR/config.yaml"

ha addons stop local_matter_server_gep || true
ha addons uninstall local_matter_server_gep || true
ha supervisor restart
ha addons install local_matter_server_gep
ha addons stop core_matter_server || true
ha addons start local_matter_server_gep
ha addons logs local_matter_server_gep --tail 250
```

## 14) Appendix B: Reference gep_custom_cluster.py (Server Registration)

This is the reference cluster module used during the session to register cluster `0xFFF1FC00` and attributes into CHIP global registries.

```python
"""Register GEP custom cluster so server-side write_attribute can resolve it."""

from dataclasses import dataclass
import typing

from chip.clusters.ClusterObjects import (
    ALL_ATTRIBUTES,
    ALL_CLUSTERS,
    Cluster,
    ClusterAttributeDescriptor,
    ClusterObjectDescriptor,
    ClusterObjectFieldDescriptor,
)
from chip.tlv import float32, uint

GEP_CUSTOM_CLUSTER_ID = 0xFFF1FC00  # 4294048768


@dataclass
class GepCustomCluster(Cluster):
    """GEP custom cluster for water valve devices."""

    id = GEP_CUSTOM_CLUSTER_ID

    descriptor = ClusterObjectDescriptor(
        Fields=[
            ClusterObjectFieldDescriptor(
                Label="target_flow_rate",
                Tag=0x0000,
                Type=typing.Optional[float32],
            ),
            ClusterObjectFieldDescriptor(
                Label="current_flow_rate",
                Tag=0x0001,
                Type=typing.Optional[float32],
            ),
            ClusterObjectFieldDescriptor(
                Label="target_ratio",
                Tag=0x0002,
                Type=typing.Optional[float32],
            ),
            ClusterObjectFieldDescriptor(
                Label="current_ratio",
                Tag=0x0003,
                Type=typing.Optional[float32],
            ),
            ClusterObjectFieldDescriptor(
                Label="lever_press_count",
                Tag=0x0004,
                Type=typing.Optional[uint],
            ),
            ClusterObjectFieldDescriptor(
                Label="feature_map",
                Tag=0xFFFC,
                Type=uint,
            ),
            ClusterObjectFieldDescriptor(
                Label="cluster_revision",
                Tag=0xFFFD,
                Type=uint,
            ),
        ]
    )

    class Attributes:
        @dataclass
        class TargetFlowRate(ClusterAttributeDescriptor):
            cluster_id = GEP_CUSTOM_CLUSTER_ID
            attribute_id = 0x0000
            attribute_type = ClusterObjectFieldDescriptor(Type=typing.Optional[float32])
            value: typing.Optional[float32] = None

        @dataclass
        class CurrentFlowRate(ClusterAttributeDescriptor):
            cluster_id = GEP_CUSTOM_CLUSTER_ID
            attribute_id = 0x0001
            attribute_type = ClusterObjectFieldDescriptor(Type=typing.Optional[float32])
            value: typing.Optional[float32] = None

        @dataclass
        class TargetRatio(ClusterAttributeDescriptor):
            cluster_id = GEP_CUSTOM_CLUSTER_ID
            attribute_id = 0x0002
            attribute_type = ClusterObjectFieldDescriptor(Type=typing.Optional[float32])
            value: typing.Optional[float32] = None

        @dataclass
        class CurrentRatio(ClusterAttributeDescriptor):
            cluster_id = GEP_CUSTOM_CLUSTER_ID
            attribute_id = 0x0003
            attribute_type = ClusterObjectFieldDescriptor(Type=typing.Optional[float32])
            value: typing.Optional[float32] = None

        @dataclass
        class LeverPressCount(ClusterAttributeDescriptor):
            cluster_id = GEP_CUSTOM_CLUSTER_ID
            attribute_id = 0x0004
            attribute_type = ClusterObjectFieldDescriptor(Type=typing.Optional[uint])
            value: typing.Optional[uint] = None

        @dataclass
        class FeatureMap(ClusterAttributeDescriptor):
            cluster_id = GEP_CUSTOM_CLUSTER_ID
            attribute_id = 0xFFFC
            attribute_type = ClusterObjectFieldDescriptor(Type=uint)
            value: uint = 0

        @dataclass
        class ClusterRevision(ClusterAttributeDescriptor):
            cluster_id = GEP_CUSTOM_CLUSTER_ID
            attribute_id = 0xFFFD
            attribute_type = ClusterObjectFieldDescriptor(Type=uint)
            value: uint = 1


def register_gep_custom_cluster() -> None:
  """Ensure cluster and attributes are present in global CHIP registries."""
  ALL_CLUSTERS[GEP_CUSTOM_CLUSTER_ID] = GepCustomCluster
  attrs = ALL_ATTRIBUTES.setdefault(GEP_CUSTOM_CLUSTER_ID, {})
  attrs[GepCustomCluster.Attributes.TargetFlowRate.attribute_id] = (
    GepCustomCluster.Attributes.TargetFlowRate
  )
  attrs[GepCustomCluster.Attributes.CurrentFlowRate.attribute_id] = (
    GepCustomCluster.Attributes.CurrentFlowRate
  )
  attrs[GepCustomCluster.Attributes.TargetRatio.attribute_id] = (
    GepCustomCluster.Attributes.TargetRatio
  )
  attrs[GepCustomCluster.Attributes.CurrentRatio.attribute_id] = (
    GepCustomCluster.Attributes.CurrentRatio
  )
  attrs[GepCustomCluster.Attributes.LeverPressCount.attribute_id] = (
    GepCustomCluster.Attributes.LeverPressCount
  )
  attrs[GepCustomCluster.Attributes.FeatureMap.attribute_id] = (
    GepCustomCluster.Attributes.FeatureMap
  )
  attrs[GepCustomCluster.Attributes.ClusterRevision.attribute_id] = (
    GepCustomCluster.Attributes.ClusterRevision
  )


# Register at import time so write_attribute can resolve descriptors immediately.
register_gep_custom_cluster()
```

## 15) Appendix C: Quick Verify Commands

After add-on starts, run:

```bash
ha addons logs local_matter_server_gep --tail 200
ha core logs --tail 200
```

Then perform one custom `number.set_value` action in UI and run:

```bash
ha addons logs local_matter_server_gep --tail 350 | grep -i -E 'write|set|4294048768|fff1fc00|error|traceback|keyerror|issubclass' -C 12
ha core logs --tail 220 | grep -i -E 'matter|set_value|4294048768|fff1fc00|error|traceback' -C 10
```

## 16) One-Command Add-on Deploy Wrapper

An executable helper script is available in this repo:

- `script/matter_gep_addon_sync_build.sh`
- `script/matter_gep_addon_sync_restart.sh`

What it does:

1. Rsyncs local source from `/workspaces/homeassistant-addons/matter_server_gep/` to HA host `/addons/local/matter_server_gep/`.
2. Restarts Supervisor.
3. Stops official `core_matter_server`.
4. Reinstalls and starts `local_matter_server_gep`.
5. Prints last 200 lines of custom add-on logs.

Required environment variables:

- `HA_USER`
- `HA_HOST`
- Optional: `HA_SSH_PORT` (defaults to `22`)

Usage from devcontainer:

```bash
cd /workspaces/homeassistant-core
export HA_USER=root
export HA_HOST=<your-ha-host-or-ip>
export HA_SSH_PORT=22

./script/matter_gep_addon_sync_build.sh
```

If you prefer preserving the existing custom add-on container without uninstall/install, edit the script and remove the `ha addons uninstall local_matter_server_gep` line.

Fast non-destructive inner loop:

```bash
cd /workspaces/homeassistant-core
export HA_USER=root
export HA_HOST=<your-ha-host-or-ip>
export HA_SSH_PORT=22

./script/matter_gep_addon_sync_restart.sh
```

`matter_gep_addon_sync_restart.sh` behavior:

1. Rsyncs `matter_server_gep` source to HA host.
2. Stops `core_matter_server` if present.
3. Rebuilds and restarts `local_matter_server_gep` if already installed.
4. Installs and starts `local_matter_server_gep` if not installed.
5. Tails add-on logs.

## 17) Git Remote and Push Workflow (Core + Add-ons)

Recommended remote layout in both repositories:

- `origin` -> your fork (push target)
- `upstream` -> Home Assistant upstream repo (pull/rebase target)

Core repo (`/workspaces/homeassistant-core`):

```bash
git remote rename origin upstream
git remote add origin https://github.com/<your-user>/core.git
git remote -v
git push -u origin add_custom_cluster
```

Add-ons repo (`/workspaces/homeassistant-addons`):

```bash
git remote rename origin upstream
git remote add origin https://github.com/<your-user>/addons.git
git remote -v
git push -u origin add_custom_cluster
```

If push from SourceTree returns `403` but terminal `git push` succeeds:

- SourceTree is using stale/wrong credentials.
- Re-auth SourceTree GitHub account and clear stale `github.com` keychain entries.
- As fallback, push from terminal and continue PR flow.

PR targets:

- Core: `<your-user>/core:add_custom_cluster` -> `home-assistant/core:dev`
- Add-ons: `<your-user>/addons:add_custom_cluster` -> `home-assistant/addons:master`