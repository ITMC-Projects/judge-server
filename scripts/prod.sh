#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
P="$ROOT/production"
TASK=${1:-prod}
trap 'echo "Judge production action failed at line $LINENO ($TASK)." >&2' ERR
dc() { docker compose -p itmc-oj-judge --env-file "$P/judge.env" -f "$P/compose.yml" "$@"; }
init() {
  command -v openssl >/dev/null
  command -v python3 >/dev/null
  mkdir -p "$P/config"
  [[ -e "$P/judge.env" ]] || cp "$P/judge.env.example" "$P/judge.env"
  [[ -e "$P/config/judge.yml" ]] || cp "$P/config/judge.yml.example" "$P/config/judge.yml"
  chmod 600 "$P/judge.env"
  # The judge process drops privileges; this config contains no credentials.
  chmod 644 "$P/config/judge.yml"
  JUDGE_INIT_SECRET=$(openssl rand -hex 32) python3 "$P/validate.py" --init "$P"
  echo 'Created missing configuration. Edit production/judge.env and production/config/judge.yml.'
  echo 'Register the judge name and generated key in OJ Admin > Judges, then run make prod.'
}
validate() {
  command -v docker >/dev/null
  command -v python3 >/dev/null
  python3 "$P/validate.py" "$P"
  dc config --quiet
}
start() {
  python3 "$P/validate.py" --network "$P"
  # First run builds automatically. Later starts reuse the image, like prod-up.
  if ! docker image inspect itmc-oj-prod/judge:local >/dev/null 2>&1; then dc build judge; fi
  # Check permissions as the real judge UID, not root. No chmod of shared OJ data.
  dc run --rm --no-deps --entrypoint /usr/bin/setpriv judge \
    --reuid judge --regid judge --clear-groups /bin/sh -c \
    'test -r /problems && test -x /problems && test -r /judge/.docker/judge.yml' || {
      echo 'Judge cannot read problems/config. See PRODUCTION.md for ACL setup.' >&2; exit 1;
    }
  dc up -d --no-build --force-recreate --wait --wait-timeout 120 judge
  dc ps
  echo 'Judge process started. Check make prod-logs and OJ judge status for authenticated connection.'
}
if [[ "$TASK" == prod-init ]]; then init; exit; fi
case "$TASK" in
  prod-down) dc down;;
  prod-logs) dc logs --follow --tail 100 judge;;
  prod-ps) dc ps;;
  prod|prod-restart) validate; start;;
  prod-build) validate; dc build judge;;
  prod-check) validate;;
  *) echo "Unknown action: $TASK" >&2; exit 1;;
esac
