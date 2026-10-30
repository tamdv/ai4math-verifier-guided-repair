#!/usr/bin/env bash
# Export a deck in slides/ to PDF with Microsoft PowerPoint (macOS), for visual checks.
# Usage: ./slides/to_pdf.sh [Slides_Nhom6_VerifierRepair.pptx]   (default: the full deck)
# PowerPoint is sandboxed: write into its container, then move the PDF here.
set -euo pipefail
cd "$(dirname "$0")"
F="${1:-Slides_Nhom6_VerifierRepair.pptx}"
P="${F%.pptx}.pdf"
C="$HOME/Library/Containers/com.microsoft.Powerpoint/Data"
rm -f "./${P:?}" "${C:?}/${P:?}"
osascript <<OSA
with timeout of 300 seconds
tell application "Microsoft PowerPoint"
    repeat with p in (get presentations)
        if name of p is "$F" then close p saving no
    end repeat
    open POSIX file "$PWD/$F"
    set thePres to presentation "$F"  -- by name: other decks may be open
    save thePres in "$P" as save as PDF
    close thePres saving no
end tell
end timeout
OSA
for i in 1 2 3 4 5 6 7 8 9 10; do [ -f "${C:?}/${P:?}" ] && break; sleep 1; done
mv "${C:?}/${P:?}" "./${P:?}"
pdfinfo "$P" | grep Pages
