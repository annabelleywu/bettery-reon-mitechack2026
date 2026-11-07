#!/usr/bin/env bash
# Download the Zhou et al. (2026) source data (MIT licence) into data/paper/.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/paper
if [ ! -d data/paper/repo ]; then
  git clone --depth 1 https://github.com/Rico-dicp/Ev-battery-cell-to-cell-inconsistency.git data/paper/repo
fi
echo "Source data: data/paper/repo/Source Data of Figures in Manuscript"
