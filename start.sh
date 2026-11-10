#!/usr/bin/env bash
# One-command local setup. No privileged installation and no model-weight downloads.
set -euo pipefail
ROOT="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
printf '\nExpenseGuard AI — Starting...\n\n'
fail() { printf '\n[ERROR] %s\n' "$*" >&2; exit 1; }
trap 'printf "\n[ERROR] Startup failed at line %s. Fix the error above and rerun ./start.sh.\n" "$LINENO" >&2' ERR

# Ignore inherited virtualenvs. Require a tested version rather than an arbitrary newer interpreter.
PYTHON=''
if [[ -n "${EXPENSEGUARD_PYTHON:-}" ]]; then
    candidates=("$EXPENSEGUARD_PYTHON")
else
    candidates=(python3.12 python3.11 python3)
fi
for candidate in "${candidates[@]}"; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c \
        'import sys; raise SystemExit(0 if sys.version_info[:2] in [(3,11),(3,12)] else 1)' 2>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
[[ -n "$PYTHON" ]] || fail 'Install Python 3.11 or 3.12, or set EXPENSEGUARD_PYTHON to its executable.'
if [[ ! -d .venv ]]; then
    "$PYTHON" -m venv .venv || fail 'Could not create .venv. Linux may need the python3-venv package.'
fi
VENV_PY="$ROOT/.venv/bin/python"
[[ -x "$VENV_PY" ]] || fail 'Existing .venv is incomplete. Rename it, then rerun ./start.sh.'
"$VENV_PY" -c 'import sys; assert sys.version_info[:2] in [(3,11),(3,12)]' || \
    fail 'Existing .venv uses an unsupported Python. Rename it and rerun.'
printf '[OK] Python environment ready\n'
# Lock setup using an atomic directory, supported by macOS and Linux without flock.
LOCK="$ROOT/.venv/.expenseguard-setup.lock"
mkdir "$LOCK" 2>/dev/null || fail 'Another startup is configuring .venv. If interrupted, remove .venv/.expenseguard-setup.lock and retry.'
cleanup() { rmdir "$LOCK" 2>/dev/null || true; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
STAMP="$ROOT/.venv/.expenseguard-dependencies.sha256"
DIGEST="$("$VENV_PY" -c 'import hashlib,platform,sys; from pathlib import Path; print(hashlib.sha256(Path("requirements.txt").read_bytes()+sys.version.encode()+platform.machine().encode()).hexdigest())')"
if [[ ! -f "$STAMP" ]] || [[ "$(cat "$STAMP")" != "$DIGEST" ]] || \
   ! "$VENV_PY" scripts/check_environment.py --dependencies-only >/dev/null 2>&1; then
    "$VENV_PY" -m pip --version >/dev/null 2>&1 || "$VENV_PY" -m ensurepip --upgrade
    "$VENV_PY" -m pip install -r requirements.txt
    "$VENV_PY" scripts/check_environment.py --dependencies-only
    printf '%s\n' "$DIGEST" > "$STAMP"
    printf '[OK] Dependencies installed\n'
else
    printf '[OK] Dependencies already installed — skipping installation\n'
fi
if [[ ! -f .env ]]; then
    (umask 077; cp .env.example .env)
fi
mkdir -p data .local/logs .local/cache
if [[ ! -f data/synthetic_expenses.csv ]]; then
    "$VENV_PY" scripts/generate_data.py --rows 1200 --seed 42
fi
printf '[OK] Demo dataset available\n'
"$VENV_PY" scripts/check_environment.py
printf '[OK] Application configuration ready\n'
cleanup
trap - EXIT
printf '\nStarting ExpenseGuard AI...\n\n'
exec "$VENV_PY" -m streamlit run app/main.py --server.address 127.0.0.1 "$@"
