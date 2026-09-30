"""Draw the OJO Sentinel launcher icon (gold eye on night background) at every density."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

SIZES = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
out = Path(sys.argv[1])
for density, px in SIZES.items():
    s = px * 4  # draw large, then downsample for smooth edges
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=s * 0.22, fill=(11, 13, 16, 255))
    r = s * 0.30
    d.ellipse([s / 2 - r, s / 2 - r, s / 2 + r, s / 2 + r], fill=(212, 160, 23, 255))
    p = s * 0.115
    d.ellipse([s / 2 - p, s / 2 - p, s / 2 + p, s / 2 + p], fill=(11, 13, 16, 255))
    folder = out / f"mipmap-{density}"
    folder.mkdir(parents=True, exist_ok=True)
    im.resize((px, px), Image.LANCZOS).save(folder / "ic_launcher.png")
