import json
from engines.web_engine import WebConverter

def progress(percent, msg):
    print(f"[{percent}%] {msg}")

converter = WebConverter()
try:
    pdf_buffer, title = converter.convert_to_pdf("https://qwilr.com/blog/business-proposal-examples/", progress_callback=progress)
    with open("outputs/test_result.pdf", "wb") as f:
        f.write(pdf_buffer.getvalue())
    print(f"Successfully saved test_result.pdf. Title: {title}")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")
