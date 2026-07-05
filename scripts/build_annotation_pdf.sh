#!/usr/bin/env bash
set -euo pipefail

# Compile the Russian annotation (ANNOTATION_RU.md) to a PDF that follows the
# IU formatting rules (Times New Roman 14, 1.5 spacing, 1.25 cm first-line
# indent, justified, A4 with 25/20/20/20 mm margins). No title page — the body
# starts directly at "Содержание". Mirrors scripts/build_thesis_pdf.sh, incl.
# the Times New Roman -> Tinos fallback for machines without the MS font.

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
cd "$repo_root"

# $1 -> content PDF (Содержание starts at page 2, title page is page 1);
# $2 -> final submission PDF, with the official IU title page prepended.
output="${1:-ANNOTATION_RU.pdf}"
final_output="${2:-Ilias_Dzhabbarov_BS_Annotation.pdf}"
title_page="BS_Annotation_title_page_2026.pdf"
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

pandoc ANNOTATION_RU.md \
  --pdf-engine=xelatex \
  --metadata "mainfont=$build_font" \
  --output "$output"

# Prepend the official IU title page (page 1) to the content (Содержание from
# page 2) to produce the final submission PDF.
"$script_dir/prepend_title_page.sh" \
  "$title_page" "$output" "-" "$final_output"
