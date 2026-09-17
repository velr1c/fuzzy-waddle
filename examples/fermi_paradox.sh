#!/bin/bash
# Example: Produce a 2-minute Fermi Paradox explainer.
set -euo pipefail
python3 run.py produce --topic "The Fermi Paradox" --minutes 2 \
  --confirm-commercial-rights --confirm-not-mass-produced
