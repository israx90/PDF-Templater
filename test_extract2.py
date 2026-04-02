import json
from engines.web_engine import WebConverter
import sys

def progress(percent, msg):
    print(f"[{percent}%] {msg}")

converter = WebConverter()
try:
    style_config = '{"h1Size":26,"h1Color":"#000000","h2Size":17,"h2Color":"#ef4444","fontPrompt":"Helvetica","fontSize":11,"lineSpacing":1.5,"linkColor":"#ef4444","textAlignment":"justify","headerType":"title","headerText":"","pageNumFormat":"page_n_of_m","marginTop":50,"marginBottom":50,"marginLeft":50,"marginRight":50,"caratula_enabled":false,"contratapa_enabled":false}'
    pdf_buffer, title = converter.convert_to_pdf("https://qwilr.com/blog/business-proposal-examples/", style_config=style_config, progress_callback=progress)
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")
