#!/bin/bash
# Build script to create PDF_templater.html from parts
cd "$(dirname "$0")/web_parts"
cat part1_head.html part2_sidebar.html part3_workspace.html part4_right_sidebar.html part5_modal.html part6_css.html part7_js.html > "../PDF_templater.html"
echo "✅ PDF_templater.html built successfully!"
