#!/bin/bash
# Example: Resume an interrupted production.
set -euo pipefail
if [ -z "${1:-}" ]; then
  echo "Usage: $0 <project-dir>"
  echo "Example: $0 out/20260918-120000-the-fermi-paradox"
  exit 1
fi
python3 run.py resume --project-dir "$1"
