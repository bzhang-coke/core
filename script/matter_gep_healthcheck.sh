#!/usr/bin/env bash
set -u

# Health check for custom Matter setup using local_matter_server_gep.
# Runs read-only checks and prints PASS/FAIL with details.

today="$(date +%Y-%m-%d)"
fail_count=0

pass() {
  echo "PASS: $1"
}

warn() {
  echo "WARN: $1"
}

fail() {
  echo "FAIL: $1"
  fail_count=$((fail_count + 1))
}

echo "Matter GEP healthcheck (${today})"
echo "--------------------------------"

if ! command -v ha >/dev/null 2>&1; then
  echo "FAIL: Home Assistant CLI (ha) is not available in PATH"
  exit 2
fi

# Check add-on presence and exclusivity.
apps_list="$(ha apps list 2>&1 || true)"
if echo "$apps_list" | grep -qi "local_matter_server_gep"; then
  pass "local_matter_server_gep is present in app list"
else
  fail "local_matter_server_gep is missing from app list"
fi

if echo "$apps_list" | grep -qi "core_matter_server"; then
  fail "core_matter_server is present; expected single-server topology"
else
  pass "core_matter_server is not present"
fi

# Confirm custom integration files still exist.
if [ -f /config/custom_components/matter/manifest.json ]; then
  pass "custom integration manifest exists"
else
  fail "custom integration manifest is missing"
fi

if [ -f /config/custom_components/matter/const.py ]; then
  pass "custom integration const.py exists"
else
  fail "custom integration const.py is missing"
fi

# Validate critical file content.
if grep -q '"version"' /config/custom_components/matter/manifest.json 2>/dev/null; then
  pass "custom manifest contains version key"
else
  fail "custom manifest missing version key"
fi

if grep -q 'ADDON_SLUG = "local_matter_server_gep"' /config/custom_components/matter/const.py 2>/dev/null; then
  pass "ADDON_SLUG points to local_matter_server_gep"
else
  fail "ADDON_SLUG is not set to local_matter_server_gep"
fi

# Collect logs once and focus checks on the most recent runtime window.
core_logs="$(ha core logs -n 500 2>&1 || true)"
addon_logs="$(ha apps logs local_matter_server_gep -n 500 2>&1 || true)"

# Keep only lines since the latest Core startup marker.
core_recent="$(printf "%s\n" "$core_logs" | awk '
  /services-up: info: copying legacy longrun home-assistant/ {start=NR}
  {line[NR]=$0}
  END {
    if (start == 0) start = 1
    for (i = start; i <= NR; i++) print line[i]
  }
')"

# Keep only lines from the latest successful initialization marker.
# If no successful init marker exists, fall back to latest startup marker.
addon_start_line="$(
  printf "%s\n" "$addon_logs" \
    | grep -nF "Matter Server successfully initialized." \
    | tail -n 1 \
    | cut -d: -f1
)"

if [ -z "$addon_start_line" ]; then
  addon_start_line="$(
    printf "%s\n" "$addon_logs" \
      | grep -nF "INFO: Starting Matter Server" \
      | tail -n 1 \
      | cut -d: -f1
  )"
fi

if [ -z "$addon_start_line" ]; then
  addon_start_line=1
fi

addon_recent="$(printf "%s\n" "$addon_logs" | sed -n "${addon_start_line},\$p")"

# Look for known bad patterns in recent Core logs.
core_bad="$(printf "%s\n" "$core_recent" | grep -Ei "(number\.set_value|4294048768|issubclass\(\) arg 1 must be a class|custom_components\.matter.*(ERROR|Traceback)|blocked from loading|missing version key|UnknownHandler|IndexError: list index out of range)" || true)"
if [ -n "$core_bad" ]; then
  fail "found problematic patterns in recent core logs (since last startup)"
  echo "$core_bad"
else
  pass "no known bad patterns in recent core logs"
fi

# Look for known bad patterns in recent add-on logs.
addon_bad="$(printf "%s\n" "$addon_recent" | grep -Ei "(Traceback|Task exception was never retrieved|Errno 98|address already in use|error while attempting to bind|Failed to start|Failed to set)" || true)"
if [ -n "$addon_bad" ]; then
  fail "found problematic patterns in recent add-on logs (since last startup)"
  echo "$addon_bad"
else
  pass "no known bad patterns in recent add-on logs"
fi

# Positive signal: initialized and node subscription is active.
addon_good="$(printf "%s\n" "$addon_recent" | grep -Ei "(Matter Server successfully initialized|Subscription succeeded|Commissioning of Node ID .* completed)" | tail -n 1 || true)"
if [ -n "$addon_good" ]; then
  pass "positive runtime signal observed: ${addon_good}"
else
  warn "no positive runtime signal found in recent add-on log window"
fi

echo "--------------------------------"
if [ "$fail_count" -eq 0 ]; then
  echo "RESULT: PASS"
  exit 0
fi

echo "RESULT: FAIL (${fail_count} issue(s))"
exit 1
