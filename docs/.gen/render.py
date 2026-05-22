from pathlib import Path
from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
HTML = HERE / "demo.html"
OUT = HERE.parent / "demo.png"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1200, "height": 675}, device_scale_factor=2)
    page.goto(HTML.resolve().as_uri())
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(OUT), full_page=False, omit_background=False)
    browser.close()
print(f"wrote {OUT}")
