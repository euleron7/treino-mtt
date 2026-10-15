"""Generate the PWA icons (felt-green tile with a white spade) into docs/icons/."""
import os

from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "icons")


def spade(draw, cx, cy, s, fill):
    """Upside-down parametric heart plus a flared stem, fitted in a box of size s centred on (cx, cy)."""
    import math
    pts = []
    for i in range(400):
        t = 2 * math.pi * i / 400
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s / 34, cy - 0.12 * s + y * s / 34))  # heart flipped: point up
    draw.polygon(pts, fill=fill)
    draw.polygon([(cx, cy + s * 0.02), (cx - s * 0.16, cy + s * 0.52), (cx + s * 0.16, cy + s * 0.52)], fill=fill)


def tile(size, maskable=False, radius_frac=0.22):
    scale = 4
    S = size * scale
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bg = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(bg)
    for y in range(S):
        t = y / S
        c = (int(26 + (12 - 26) * t), int(122 + (72 - 122) * t), int(80 + (48 - 80) * t), 255)
        gd.line([(0, y), (S, y)], fill=c)
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    if maskable:
        md.rectangle([0, 0, S, S], fill=255)
    else:
        md.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * radius_frac), fill=255)
    img.paste(bg, (0, 0), mask)
    fg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fg)
    k = 0.42 if maskable else 0.56
    spade(fd, S / 2, S / 2 - S * 0.03, S * k, (250, 252, 250, 255))
    shadow = fg.split()[3].filter(ImageFilter.GaussianBlur(S * 0.012))
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 90))
    img.paste(sh, (int(S * 0.006), int(S * 0.012)), shadow)
    img.alpha_composite(fg)
    return img.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    tile(192).save(os.path.join(OUT, "icon-192.png"))
    tile(512).save(os.path.join(OUT, "icon-512.png"))
    tile(512, maskable=True).save(os.path.join(OUT, "maskable-512.png"))
    tile(180, maskable=True).convert("RGB").save(os.path.join(OUT, "apple-touch-icon.png"))
    print("icons written to", OUT)
