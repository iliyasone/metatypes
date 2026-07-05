#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
cd "$repo_root"

# $1 -> content PDF, kept for general-purpose reading/rendering. It still
#       carries pandoc's own generated title page as page 1 (the plain
#       `pandoc THESIS.md -o THESIS.pdf --pdf-engine=xelatex` one-liner in
#       AGENTS.md produces the same file).
# $2 -> final submission PDF: the official IU title page replaces that
#       generated first page.
output="${1:-THESIS.pdf}"
final_output="${2:-Ilias_Dzhabbarov_BS_Thesis.pdf}"
title_page="BS_Thesis_title_page_2026.pdf"
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

# Replace pandoc's generated title page (page 1) with the official IU title
# page: prepend the title page, then include the content from page 2 onward.
"$script_dir/prepend_title_page.sh" \
  "$title_page" "$output" "2-" "$final_output"
