#!/usr/bin/env bash
set -euo pipefail

TARGET="${FLEET_ROOT:-/app/fleet-automation}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -d "$TARGET" ]]; then
  printf 'missing fleet runtime: %s\n' "$TARGET" >&2
  exit 1
fi

# Harbor's solution container does not guarantee that pip's console scripts
# land on the inherited PATH. Install the reference controller first, then
# resolve ansible-core's actual script directory from installed package metadata.
python -m pip install --disable-pip-version-check --no-cache-dir 'ansible==12.0.0' >/dev/null
PYTHON_SCRIPTS="$(python - <<'PY'
from importlib.metadata import distribution
from pathlib import Path

dist = distribution("ansible-core")
for entry in dist.files or ():
    if Path(str(entry)).name == "ansible-config":
        candidate = Path(dist.locate_file(entry)).resolve()
        if candidate.is_file():
            print(candidate.parent)
            break
else:
    raise SystemExit("ansible-config console script not found after installation")
PY
)"
export PATH="$PYTHON_SCRIPTS:$PATH"
command -v ansible-config >/dev/null

WORK="$(mktemp -d)"
cleanup() {
  if [[ -L "$TARGET/environment" ]]; then
    rm -f "$TARGET/environment"
  fi
  if [[ -L "$TARGET/ansible.cfg" ]]; then
    rm -f "$TARGET/ansible.cfg"
  fi
  if [[ -L "$TARGET/.runtime-vault-pass" ]]; then
    rm -f "$TARGET/.runtime-vault-pass"
  fi
  rm -rf "$WORK"
}
trap cleanup EXIT

mkdir -p "$WORK/solution"
ln -s "$TARGET" "$WORK/environment"
cp "$HERE/repair.sh" "$WORK/solution/repair.sh"
chmod 0755 "$WORK/solution/repair.sh"

# The historical reference repair was authored against the repository task
# layout where the runtime lives under environment/. Recreate that layout
# transiently while applying all mutations to the real runtime artifact.
if [[ ! -e "$TARGET/environment" ]]; then
  ln -s . "$TARGET/environment"
fi
ln -s "$WORK/ansible.cfg" "$TARGET/ansible.cfg"
ln -s "$WORK/.runtime-vault-pass" "$TARGET/.runtime-vault-pass"

"$WORK/solution/repair.sh"

# Persist a runtime-native configuration after the transient repository-layout
# compatibility layer is removed.
cfg_tmp="$WORK/ansible.runtime.cfg"
cp -L "$TARGET/ansible.cfg" "$cfg_tmp"
sed -i \
  -e 's#roles_path = ./environment/roles#roles_path = ./roles#' \
  -e 's#inventory = ./environment/inventory/hosts.yml#inventory = ./inventory/hosts.yml#' \
  -e 's#vault_password_file = ./.runtime-vault-pass#vault_password_file = /app/fleet-automation/.runtime-vault-pass#' \
  "$cfg_tmp"
pass_tmp="$WORK/runtime-vault-pass"
cp -L "$TARGET/.runtime-vault-pass" "$pass_tmp"
rm -f "$TARGET/ansible.cfg" "$TARGET/.runtime-vault-pass" "$TARGET/environment"
install -m 0644 "$cfg_tmp" "$TARGET/ansible.cfg"
install -m 0600 "$pass_tmp" "$TARGET/.runtime-vault-pass"

cd "$TARGET"
export ANSIBLE_CONFIG="$TARGET/ansible.cfg"
./bin/fleet-ansible playbooks/site.yml --syntax-check
printf 'reference_solution=PASS target=%s\n' "$TARGET"
