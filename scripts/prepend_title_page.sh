#!/usr/bin/env bash
set -euo pipefail

# Assemble a final submission PDF by prepending the official IU title-page PDF
# to a pandoc-built content PDF, using LaTeX pdfpages (part of
# texlive-latex-extra, already required to build the documents). No poppler /
# qpdf / ghostscript needed.
#
# Usage:
#   prepend_title_page.sh <title.pdf> <content.pdf> <content_page_range> <output.pdf>
#
#   content_page_range  pdfpages page spec for the content PDF:
#                         "-"   keep every page (annotation)
#                         "2-"  drop the content's own first page (thesis, whose
#                               pandoc-generated title page is replaced here)

if [[ $# -ne 4 ]]; then
  echo "usage: $0 <title.pdf> <content.pdf> <content_page_range> <output.pdf>" >&2
  exit 2
fi

title_pdf="$1"
content_pdf="$2"
page_range="$3"
output="$4"

for f in "$title_pdf" "$content_pdf"; do
  if [[ ! -f "$f" ]]; then
    echo "error: input PDF not found: $f" >&2
    exit 1
  fi
done

if ! command -v xelatex >/dev/null 2>&1; then
  echo "error: xelatex not found (install texlive-xetex)." >&2
  exit 1
fi
if ! kpsewhich pdfpages.sty >/dev/null 2>&1; then
  echo "error: LaTeX package 'pdfpages' not found (install texlive-latex-extra)." >&2
  exit 1
fi

# Absolute paths so the merge compiles from a scratch directory.
abspath() { echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; }
title_abs="$(abspath "$title_pdf")"
content_abs="$(abspath "$content_pdf")"
output_abs="$(abspath "$output")"

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

# fitpaper=true keeps each source page at its own (A4) size — no scaling.
# \pagestyle{empty} plus pdfpages' default per-page \thispagestyle{empty}
# mean the wrapper overlays NO page numbers of its own, so only the content's
# baked-in numbering shows (and the title page stays unnumbered).
cat > "$workdir/merge.tex" <<TEX
\documentclass[a4paper]{article}
\usepackage{pdfpages}
\pagestyle{empty}
\begin{document}
\includepdf[pages=-,fitpaper=true]{$title_abs}
\includepdf[pages=$page_range,fitpaper=true]{$content_abs}
\end{document}
TEX

if ! xelatex -interaction=nonstopmode -halt-on-error \
      -output-directory "$workdir" "$workdir/merge.tex" >"$workdir/merge.log" 2>&1; then
  echo "error: xelatex failed to assemble '$output'. Log:" >&2
  tail -n 20 "$workdir/merge.log" >&2
  exit 1
fi

mv "$workdir/merge.pdf" "$output_abs"
echo "wrote $output"
