"""
make_icons.py — render the Nabbly mark to PNG with a real transparent background.

Why this exists: assets/icon.svg is the vector master, but Streamlit's
page_icon wants a raster file, and the macOS Quick Look trick we used before
(`qlmanage`) bakes a solid WHITE background into the PNG. That's what made the
browser tab show a white box behind the icon.

cairosvg would be the obvious tool but it needs a native cairo library that
isn't on this machine, so we redraw the same geometry with Pillow, which is
pure-wheel and always available. Coordinates below are the 48x48 viewBox from
icon.svg multiplied by SCALE, so the two stay in sync — if you change the SVG,
change these numbers to match.

Run:  python make_icons.py
"""
from PIL import Image, ImageDraw, ImageFilter

SIZE = 512
SCALE = SIZE / 48          # icon.svg uses a 48x48 viewBox
OUT = "assets/favicon.png"

AMBER_LIGHT = (247, 181, 105)
AMBER_MID = (232, 147, 58)
AMBER_DEEP = (203, 111, 22)
SHADOW = (124, 66, 6)


def s(v):
    """viewBox units -> pixels."""
    return v * SCALE


def diagonal_amber(size):
    """The badge gradient: light top-left, deep bottom-right."""
    g = Image.new("RGB", (size, size))
    px = g.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size - 2)
            if t <= 0.52:
                k = t / 0.52
                a, b = AMBER_LIGHT, AMBER_MID
            else:
                k = (t - 0.52) / 0.48
                a, b = AMBER_MID, AMBER_DEEP
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))
    return g


def round_line(draw, pts, width, fill):
    """Polyline with round caps and joins (Pillow has no stroke-linecap)."""
    draw.line(pts, fill=fill, width=width, joint="curve")
    r = width / 2
    for x, y in pts:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def build():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # --- badge: gradient clipped to a rounded square -----------------------
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [s(4), s(4), s(44), s(44)], radius=s(11), fill=255)
    img.paste(diagonal_amber(SIZE), (0, 0), mask)

    # --- sheen across the top ---------------------------------------------
    gloss = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gp = gloss.load()
    for y in range(int(s(44))):
        t = y / (SIZE * 0.55)
        a = int(max(0.0, 0.30 * (1 - t)) * 255)
        if a:
            for x in range(SIZE):
                gp[x, y] = (255, 255, 255, a)
    img = Image.alpha_composite(img, Image.composite(
        gloss, Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0)), mask))

    d = ImageDraw.Draw(img)

    # --- inner light edge --------------------------------------------------
    d.rounded_rectangle([s(4.7), s(4.7), s(43.3), s(43.3)], radius=s(10.4),
                        outline=(255, 255, 255, 66), width=max(1, int(s(1.1))))

    # --- ping ring around the blip ----------------------------------------
    cx, cy, rr = s(34.2), s(11.4), s(4.7)
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr],
              outline=(255, 255, 255, 92), width=max(1, int(s(1.4))))

    # --- the mark, with a soft shadow so it lifts off the badge ------------
    stem = [(s(13.5), s(33.5)), (s(13.5), s(17))]
    check = [(s(13.5), s(17)), (s(23), s(30.5)), (s(32), s(14))]
    blip_r = s(2.5)

    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    round_line(sd, stem, int(s(3.5)), SHADOW + (107,))
    round_line(sd, check, int(s(4.5)), SHADOW + (107,))
    sd.ellipse([cx - blip_r, cy - blip_r, cx + blip_r, cy + blip_r], fill=SHADOW + (107,))
    shadow = shadow.filter(ImageFilter.GaussianBlur(s(1.15)))
    shadow = Image.composite(shadow.transform(
        shadow.size, Image.AFFINE, (1, 0, 0, 0, 1, -s(1.2))),
        Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0)), mask)
    img = Image.alpha_composite(img, shadow)

    d = ImageDraw.Draw(img)
    round_line(d, stem, int(s(3.5)), (255, 255, 255, 128))   # stem steps back
    round_line(d, check, int(s(4.5)), (255, 255, 255, 255))  # check leads
    d.ellipse([cx - blip_r, cy - blip_r, cx + blip_r, cy + blip_r],
              fill=(255, 255, 255, 255))

    img.save(OUT)
    corners = [img.getpixel(p)[3] for p in ((1, 1), (SIZE - 2, 1), (1, SIZE - 2))]
    print(f"wrote {OUT} at {SIZE}px — corner alpha {corners} (0 = transparent)")


if __name__ == "__main__":
    build()
