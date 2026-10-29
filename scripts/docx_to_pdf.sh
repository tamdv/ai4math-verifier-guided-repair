#!/usr/bin/env bash
# Export a .docx in this repo to PDF next to it with Microsoft Word (macOS).
# Usage: ./scripts/docx_to_pdf.sh docs/OnTap_BaoVe_Nhom6.docx
# Close any Word dialog first: a modal dialog blocks AppleScript and the export hangs.
set -euo pipefail
SRC="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
F="$(basename "$SRC")"
P="${F%.docx}.pdf"
C="$HOME/Library/Containers/com.microsoft.Word/Data/Documents"
rm -f "$(dirname "$SRC")/${P:?}" "${C:?}/${P:?}" "${C:?}/${F:?}"
cp "$SRC" "${C:?}/${F:?}"  # open from Word's own container: no folder permission prompt
osascript <<OSA
with timeout of 300 seconds
tell application "Microsoft Word"
    repeat with x in (get documents)
        if name of x is "$F" then close x saving no
    end repeat
    open POSIX file "$C/$F"
    delay 1
    set d to document "$F"  -- by name: the user may have other documents in front
    save as d file name "$P" file format format PDF
    close d saving no
end tell
end timeout
OSA
for i in 1 2 3 4 5 6 7 8 9 10; do [ -f "${C:?}/${P:?}" ] && break; sleep 2; done
mv "${C:?}/${P:?}" "$(dirname "$SRC")/${P:?}"
rm -f "${C:?}/${F:?}"
pdfinfo "$(dirname "$SRC")/$P" | grep Pages
