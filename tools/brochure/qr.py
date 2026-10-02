"""Make the brochure's QR codes (pip install segno).

    python3 qr.py

qr-brochure.png / .svg open the brochure page; qr-demo.png (printed on the back cover) opens the live demo.
"""
from pathlib import Path

import segno

OUT = Path(__file__).resolve().parents[2] / "brochure"
BROCHURE = "https://pizzatechies.github.io/ojo/brochure/"
DEMO = "https://pizzatechies.github.io/ojo/demo/"

OUT.mkdir(exist_ok=True)
qr = segno.make(BROCHURE, error="m")
qr.save(OUT / "qr-brochure.png", scale=20, border=4, dark="#0B0E12", light="#FFFFFF")
qr.save(OUT / "qr-brochure.svg", scale=10, border=4, dark="#0B0E12", light="#FFFFFF", title="OJO Sentinel brochure")
segno.make(DEMO, error="m").save(OUT / "qr-demo.png", scale=16, border=2, dark="#0B0E12", light="#FFFFFF")
print("wrote", ", ".join(p.name for p in sorted(OUT.glob("qr-*"))))
