"""
make_forward_beat.py — the beat that shows the thing no public board can do.

The demo covers the loop anyone can picture: a gig is posted, you are told, you
reply. Forwarding is the half nobody else has, and it is invisible in every cut
we have. A newsletter goes to an inbox, not a board — so a crawler cannot see
it, and neither can a competitor. The person who receives it can forward it,
and then it is on their board and on nobody else's.

COPY IS LIFTED FROM THE SITE, NOT WRITTEN HERE. nabbly.co already carries this
exact example — Study Hall's "Opportunities of the Week" split into three gigs.
Reusing it verbatim keeps the video and the front page telling one story, and
it is copy that has already been through a founder pass.

THE ADDRESS IS THE REAL SHAPE. inbox.py derives it as `gigs+<10 hex>@nabbly.co`,
a hash of the account's email so it is stable without storing another secret
and does not leak who it belongs to. The tag shown here is inbox.py's own
docstring example, not a live one: putting a working address on a video means
publishing an inbox anyone can post into.

Run:  .venv/bin/python tools/make_forward_beat.py [WxH]
Out:  brand/posts/demo/forward-beat.png   (stills; animation comes after review)
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import make_post as mp                                    # noqa: E402

OUT = ROOT / "brand" / "posts" / "demo"
W, H = 1920, 1080

SENDER_INITIALS = "SH"
SENDER = "Study Hall"
SUBJECT = "Opportunities of the Week"
BODY = ("A few things crossed our desk this week that are a fit for you. "
        "Wired's looking for a freelance science reporter, $1/word, pitches "
        "due Friday. Also heard from a production house after a documentary "
        "editor for a 6-week remote contract, and a nonprofit is hunting for "
        "someone to handle a full brand refresh…")

# inbox.py's docstring example. Deliberately not a live address.
ADDRESS = "gigs+3f9a2b1c04@nabbly.co"

SPLIT = [
    ("Freelance science reporter — Wired", "$1/word · pitch by Friday"),
    ("Documentary editor — 6-week contract", "Remote · Video"),
    ("Brand designer for a nonprofit rebrand", "Project rate · Design"),
]


def wrap(d, text, font, width):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if d.textlength(trial, font=font) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def render():
    img = Image.new("RGB", (W, H), mp.BG)
    d = ImageDraw.Draw(img)

    f_lbl = mp.font(21, "Semibold")
    f_name = mp.font(32, "Semibold")
    f_sub = mp.font(27, "Regular", mp.ARIAL)
    f_body = mp.font(23, "Regular", mp.ARIAL)
    f_addr = mp.font(25, "Semibold")
    f_title = mp.font(29, "Semibold")
    f_meta = mp.font(22, "Regular", mp.ARIAL)

    # ---- left: the newsletter, as it lands in a mailbox ---------------------
    LX, LW = 190, 720
    card = Image.new("RGBA", ((LW) * 2, 470 * 2), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle(
        [0, 0, LW * 2 - 1, 470 * 2 - 1], radius=26 * 2,
        fill=(21, 24, 29, 255), outline=(47, 52, 61, 255), width=2 * 2)
    card = card.resize((LW, 470), Image.LANCZOS)
    img.paste(card, (LX, 300), card)

    cd = ImageDraw.Draw(img)
    av = 60
    cd.ellipse([LX + 36, 336, LX + 36 + av, 336 + av], fill=(44, 49, 58))
    cd.text((LX + 36 + av / 2, 336 + av / 2), SENDER_INITIALS,
            font=mp.font(24, "Semibold"), fill=mp.GREY, anchor="mm")
    cd.text((LX + 118, 344), SENDER, font=f_name, fill=mp.BODY)
    cd.text((LX + 118, 382), SUBJECT, font=f_sub, fill=mp.GREY)

    y = 448
    for line in wrap(cd, BODY, f_body, LW - 76)[:5]:
        cd.text((LX + 38, y), line, font=f_body, fill=mp.DIM)
        y += 33

    cd.line([(LX + 38, 640), (LX + LW - 38, 640)], fill=(47, 52, 61), width=1)
    cd.text((LX + 38, 664), "FORWARDED TO", font=mp.font(19, "Semibold"),
            fill=mp.DIM)
    cd.text((LX + 38, 696), ADDRESS, font=f_addr, fill=mp.HOT)

    # ---- the hinge ----------------------------------------------------------
    cd.text((LX + LW + 60, 520), "→", font=mp.font(46, "Regular", mp.ARIAL),
            fill=(90, 96, 106))

    # ---- right: what it became ---------------------------------------------
    RX = LX + LW + 150
    cd.text((RX, 300), "NABBLY SPLITS IT INTO", font=f_lbl, fill=mp.DIM)

    y = 356
    for i, (title, meta) in enumerate(SPLIT):
        row = Image.new("RGBA", (700 * 2, 116 * 2), (0, 0, 0, 0))
        ImageDraw.Draw(row).rounded_rectangle(
            [0, 0, 700 * 2 - 1, 116 * 2 - 1], radius=18 * 2,
            fill=(21, 24, 29, 255), outline=(47, 52, 61, 255), width=2 * 2)
        row = row.resize((700, 116), Image.LANCZOS)
        img.paste(row, (RX, y), row)
        rd = ImageDraw.Draw(img)
        rd.text((RX + 30, y + 30), title, font=f_title, fill=mp.BODY)
        rd.text((RX + 30, y + 70), meta, font=f_meta, fill=mp.GREY)
        y += 140

    # ---- the claim ----------------------------------------------------------
    d = ImageDraw.Draw(img)
    d.text((LX, 170), "The gigs no public board carries.",
           font=mp.font(52, "Semibold"), fill=mp.BODY)
    d.text((LX, 232), "Forward the newsletter once. Every gig inside it lands "
                      "on your board, and nobody else's.",
           font=mp.font(26, "Regular", mp.ARIAL), fill=mp.GREY)

    out = OUT / "forward-beat.png"
    img.save(out, "PNG", optimize=True)
    print(f"wrote {out}  {W}x{H}")


if __name__ == "__main__":
    size = next((a for a in sys.argv[1:] if "x" in a
                 and all(p.isdigit() for p in a.split("x", 1))), None)
    if size:
        W, H = (int(v) for v in size.split("x"))
    render()
