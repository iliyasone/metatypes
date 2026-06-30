#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

output="${1:-THESIS.pdf}"
requested_font="${THESIS_MAINFONT:-Times New Roman}"
build_font="$requested_font"

if command -v fc-match >/dev/null 2>&1; then
  matched_font="$(fc-match -f '%{family[0]}\n' "$requested_font" | head -n 1)"
  if [[ "$matched_font" != "$requested_font" ]]; then
    if [[ "${THESIS_STRICT_FONT:-0}" == "1" ]]; then
      echo "error: '$requested_font' is not installed; fontconfig resolved it to '$matched_font'." >&2
      exit 1
    fi

    build_font="${THESIS_FALLBACK_FONT:-Tinos}"
    echo "warning: '$requested_font' is not installed; building with '$build_font' for local inspection." >&2
  fi
fi

pandoc THESIS.md \
  --pdf-engine=xelatex \
  --metadata "mainfont=$build_font" \
  --output "$output"
