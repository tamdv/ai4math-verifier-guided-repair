#!/usr/bin/env bash
# Update the TOC fields and export reports/report.docx to reports/report.pdf with Microsoft Word (macOS).
# Word is sandboxed: it writes into its container, then the PDF is moved here.
set -euo pipefail
cd "$(dirname "$0")"
F="report.docx"
P="report.pdf"
C="$HOME/Library/Containers/com.microsoft.Word/Data/Documents"
rm -f "./${P:?}" "${C:?}/${P:?}"
osascript <<OSA
with timeout of 300 seconds
tell application "Microsoft Word"
    repeat with x in (get documents)
        if name of x is "$F" then close x saving no
    end repeat
    open POSIX file "$PWD/$F"
    set d to active document
    repeat with t in (get tables of contents of d)
        update t
    end repeat
    save as d file name "$P" file format format PDF
    close d saving no
end tell
end timeout
OSA
for i in 1 2 3 4 5 6 7 8 9 10; do [ -f "${C:?}/${P:?}" ] && break; sleep 2; done
mv "${C:?}/${P:?}" "./${P:?}"
pdfinfo "$P" | grep Pages
